"""Deterministic pre-flight validation for the canonical handover generator.

Runs the fixed Slice-7 set of five checks before any LLM / planner call so
malformed scope, continuity, ledger, role, or reference-tag conditions
hard-fail with structured, human-readable errors:

- A: assembled scope-input paths exist on disk
- B: carry-forward phase ids exist in the ledger and are ratified
- C: previous canonical handover's ``next_handover_id`` matches the active
  planning row's ``handover_id``
- D: no path appears in more than one context role
- E: reference tags in the relevant markdown sources parse per the canonical
  ``[future-doc: <path>]`` / ``[future-path: <path>]`` grammar

No LLM judgment is invoked anywhere. Every check is pure code over inputs
the caller has already assembled, so each check is independently testable
in isolation. The orchestrator does not short-circuit, so an operator sees
every blocking issue in a single report.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from alfred.ledger.models import PhaseLedger
from alfred.refs.tags import scan_reference_tags

CheckId = Literal[
    "A_scope_paths_exist",
    "B_carry_forward_ratified",
    "C_continuity_next_handover_match",
    "D_no_role_collision",
    "E_reference_tags_parse",
]

CHECK_IDS: tuple[CheckId, ...] = (
    "A_scope_paths_exist",
    "B_carry_forward_ratified",
    "C_continuity_next_handover_match",
    "D_no_role_collision",
    "E_reference_tags_parse",
)


@dataclass(frozen=True)
class PreflightError:
    """A single deterministic preflight failure.

    ``check`` identifies which of the five checks failed (stable, testable
    identifier). ``message`` names the offending path/id/value so the
    operator can act without consulting the validator source.
    """

    check: CheckId
    message: str


# Canonical handover continuity line. The Slice 6 contract requires the
# previous handover to declare the next id verbatim as
# ``**next_handover_id:** <ID>`` so this preflight is a deterministic parse,
# not a semantic inference.
_NEXT_HANDOVER_RE = re.compile(
    r"\*\*next_handover_id:\*\*\s*(?P<id>[A-Za-z0-9_]+)"
)


def check_scope_paths_exist(
    paths: Iterable[Path],
) -> list[PreflightError]:
    """Check A — every assembled scope-role path exists on disk.

    The caller passes the resolved ``scope``-role inputs the generator
    will register. Synthetic in-memory markers (e.g. the pre-rendered
    scope packet placeholder) must be excluded by the caller, since
    they are not file-backed and would always fail this check.

    The caller must also build this list *before* any "missing file"
    filtering step — preflight surfaces missing scope docs rather than
    letting them silently disappear from the packet builder's input set.
    """
    errors: list[PreflightError] = []
    for path in paths:
        resolved = Path(path)
        if not resolved.is_file():
            errors.append(
                PreflightError(
                    check="A_scope_paths_exist",
                    message=(
                        "scope-role input path does not exist on disk: "
                        f"{resolved.as_posix()}"
                    ),
                )
            )
    return errors


def check_carry_forward_ratified(
    *,
    ledger: PhaseLedger,
    carry_forward_phase_ids: Iterable[int],
) -> list[PreflightError]:
    """Check B — every carry-forward phase id exists and is ``ratified``.

    Errors distinguish *missing* ids from ids whose phase exists but has
    the wrong status, because the operator response differs (fix the
    reference vs. ratify the upstream phase first).
    """
    errors: list[PreflightError] = []
    by_id = {phase.id: phase for phase in ledger.phases}
    for pid in carry_forward_phase_ids:
        phase = by_id.get(pid)
        if phase is None:
            errors.append(
                PreflightError(
                    check="B_carry_forward_ratified",
                    message=(
                        f"carry-forward phase id {pid} is not declared in "
                        "the phase ledger"
                    ),
                )
            )
            continue
        if phase.status != "ratified":
            errors.append(
                PreflightError(
                    check="B_carry_forward_ratified",
                    message=(
                        f"carry-forward phase id {pid} has status "
                        f"{phase.status!r}; expected 'ratified'"
                    ),
                )
            )
    return errors


def check_previous_next_handover_match(
    *,
    previous_handover_path: Path,
    expected_handover_id: str,
) -> list[PreflightError]:
    """Check C — previous handover's ``next_handover_id`` matches the active phase.

    Preserves the Slice 6 explicit-continuity contract: the previous
    canonical handover must declare the active phase's handover id via a
    ``**next_handover_id:** <ID>`` line. Missing line or mismatched id
    are both blocking — continuity is never inferred from phase ordering.
    """
    path = Path(previous_handover_path)
    if not path.is_file():
        return [
            PreflightError(
                check="C_continuity_next_handover_match",
                message=(
                    "previous canonical handover not found at "
                    f"{path.as_posix()}; cannot verify next_handover_id "
                    "continuity"
                ),
            )
        ]
    text = path.read_text(encoding="utf-8")
    match = _NEXT_HANDOVER_RE.search(text)
    if match is None:
        return [
            PreflightError(
                check="C_continuity_next_handover_match",
                message=(
                    f"previous canonical handover {path.as_posix()} does "
                    "not declare a `**next_handover_id:** <ID>` line; "
                    "explicit continuity is required"
                ),
            )
        ]
    declared = match.group("id")
    if declared != expected_handover_id:
        return [
            PreflightError(
                check="C_continuity_next_handover_match",
                message=(
                    "continuity mismatch: previous handover "
                    f"{path.as_posix()} declares "
                    f"next_handover_id={declared!r} but the active planning "
                    f"row's handover_id is {expected_handover_id!r}"
                ),
            )
        ]
    return []


def check_no_role_collision(
    role_assignments: Iterable[tuple[str, str]],
) -> list[PreflightError]:
    """Check D — no path appears in more than one context role.

    The caller passes ``(path, role)`` pairs from the same plan that
    will feed ``ContextBundle``. The bundle's dedup precedence
    (``scope`` > ``carry_forward`` > ``continuity``) silently drops
    lower-precedence duplicates; this preflight surfaces them instead so
    we never mask a misassignment.
    """
    errors: list[PreflightError] = []
    roles_by_path: dict[str, list[str]] = {}
    for path, role in role_assignments:
        roles_by_path.setdefault(path, []).append(role)
    for path, roles in roles_by_path.items():
        unique_roles = sorted(set(roles))
        if len(unique_roles) > 1:
            errors.append(
                PreflightError(
                    check="D_no_role_collision",
                    message=(
                        f"path {path!r} is assigned to multiple context "
                        f"roles: {unique_roles}; preflight requires a "
                        "single role per path"
                    ),
                )
            )
    return errors


def check_reference_tags_parse(
    sources: Iterable[Path],
) -> list[PreflightError]:
    """Check E — every reference tag in the given sources parses.

    Uses the canonical ``[future-doc: <path>]`` / ``[future-path: <path>]``
    grammar from :mod:`alfred.refs.tags`. Malformed near-misses surface
    with the parser's line/column metadata so the message is actionable
    without reading the validator source.
    """
    errors: list[PreflightError] = []
    for source in sources:
        path = Path(source)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        _tags, parse_errors = scan_reference_tags(text)
        for parse_error in parse_errors:
            errors.append(
                PreflightError(
                    check="E_reference_tags_parse",
                    message=(
                        f"malformed reference tag in {path.as_posix()} at "
                        f"line {parse_error.line}, col {parse_error.col}: "
                        f"{parse_error.snippet!r} ({parse_error.message})"
                    ),
                )
            )
    return errors


def run_preflight(
    *,
    ledger: PhaseLedger,
    scope_paths: Iterable[Path],
    carry_forward_phase_ids: Iterable[int],
    previous_handover_path: Path,
    expected_handover_id: str,
    role_assignments: Iterable[tuple[str, str]],
    reference_tag_sources: Iterable[Path],
) -> list[PreflightError]:
    """Run all five preflight checks and return every error found.

    Checks run independently; the function does not short-circuit so the
    operator sees every blocking issue in a single report. An empty list
    means preflight passed and the generator is safe to call the planner.
    """
    errors: list[PreflightError] = []
    errors.extend(check_scope_paths_exist(scope_paths))
    errors.extend(
        check_carry_forward_ratified(
            ledger=ledger,
            carry_forward_phase_ids=carry_forward_phase_ids,
        )
    )
    errors.extend(
        check_previous_next_handover_match(
            previous_handover_path=previous_handover_path,
            expected_handover_id=expected_handover_id,
        )
    )
    errors.extend(check_no_role_collision(role_assignments))
    errors.extend(check_reference_tags_parse(reference_tag_sources))
    return errors


def format_errors(errors: Iterable[PreflightError]) -> str:
    """Render a deterministic, multi-line error block for operator output.

    Format is ``- [<check_id>] <message>`` per line. The generator script
    is free to wrap or prefix this; preflight itself never prints.
    """
    return "\n".join(f"- [{error.check}] {error.message}" for error in errors)
