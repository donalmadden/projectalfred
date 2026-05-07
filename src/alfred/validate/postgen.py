"""Deterministic post-generation validation for the canonical handover generator.

Runs the fixed Slice-8 set of six checks **after** the planner returns a
draft and **before** the generator promotes it to the canonical output
path. Failure blocks promotion and the caller is expected to write a
``FAILED_CANDIDATE`` artifact (the wiring lives in the generator script;
this module never writes files and never prints).

Per protocol every check is deterministic code only — no LLM-as-judge
anywhere. Semantic judgment is reserved for the human approval gate.

The six checks are:

- 1: metadata identity / chronology closure (id, date, previous_handover
  appear in the ``## CONTEXT — READ THIS FIRST`` block)
- 2: required section contract (``##`` headings from the canonical
  scaffold, plus ``### Git History`` under ``## WHAT EXISTS TODAY``)
- 3: git history integrity (every expected commit line is present
  byte-for-byte inside the ``### Git History`` fenced block)
- 4: reference-doc hygiene closure (``Reference Documents`` list is
  non-empty and contains no unresolved ``[future-doc:]`` /
  ``[future-path:]`` tags)
- 5: hard-rules presence (every required invariant phrase appears in the
  ``## HARD RULES`` section)
- 6: task closure against the brief seed (``## TASK OVERVIEW`` row count
  matches and each ``## TASK N —`` heading exists)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

CheckId = Literal[
    "1_metadata_identity",
    "2_required_sections",
    "3_git_history_integrity",
    "4_reference_doc_hygiene",
    "5_hard_rules_presence",
    "6_task_closure",
]

CHECK_IDS: tuple[CheckId, ...] = (
    "1_metadata_identity",
    "2_required_sections",
    "3_git_history_integrity",
    "4_reference_doc_hygiene",
    "5_hard_rules_presence",
    "6_task_closure",
)

# Required ``##`` headings on a canonical Alfred handover. Mirrors the
# scaffold at ``configs/alfred_handover_template.md``. The matching is
# strict (exact text after the ``## ``) so that header drift is caught at
# promotion time rather than silently parsed.
REQUIRED_H2_HEADINGS: tuple[str, ...] = (
    "CONTEXT — READ THIS FIRST",
    "WHAT EXISTS TODAY",
    "HARD RULES",
    "WHAT THIS PHASE PRODUCES",
    "TASK OVERVIEW",
    "WHAT NOT TO DO",
    "POST-MORTEM",
)

# ``### Git History`` must live under ``## WHAT EXISTS TODAY``. Pairs of
# (h3 text, required parent h2 text).
REQUIRED_H3_UNDER: tuple[tuple[str, str], ...] = (
    ("Git History", "WHAT EXISTS TODAY"),
)


@dataclass(frozen=True)
class PostgenError:
    """A single deterministic post-generation failure.

    ``check`` identifies which of the six checks failed (stable, testable
    identifier). ``message`` names the offending value/section so the
    operator can act without consulting the validator source.
    """

    check: CheckId
    message: str


@dataclass(frozen=True)
class PostgenResult:
    """Result of a post-generation validation pass.

    ``ok`` is true iff there are zero errors. The generator wiring uses
    ``ok`` to gate promotion; on failure it persists ``errors`` (rendered
    via :func:`format_errors`) into the ``FAILED_CANDIDATE`` artifact.
    """

    ok: bool
    errors: tuple[PostgenError, ...]


# Slice 6 explicit-continuity contract: the planner must emit
# ``**id:** <ID>`` and ``**previous_handover:** <ID>`` lines verbatim,
# so postgen is a deterministic parse, not a semantic inference.
_ID_RE = re.compile(r"(?m)^\*\*id:\*\*\s*(?P<id>\S+)\s*$")
_DATE_RE = re.compile(r"(?m)^\*\*date:\*\*\s*(?P<date>\S+)\s*$")
_PREVIOUS_RE = re.compile(
    r"(?m)^\*\*previous_handover:\*\*\s*(?P<id>\S+)\s*$"
)

# Future-doc / future-path tags must not appear in a candidate that is
# being promoted: open future references mean the document still has
# unresolved closure work and is not safe to ratify.
_FUTURE_TAG_RE = re.compile(r"\[future-(?:doc|path):\s*[^\]]*\]")

# Task overview row in the table block, e.g.:
#   "| 1 | Title | Deliverable | CHECKPOINT-1 |"
_TASK_ROW_RE = re.compile(r"(?m)^\|\s*(?P<n>\d+)\s*\|")

# Task section heading, e.g. "## TASK 1 — Title"
_TASK_HEADING_RE = re.compile(
    r"(?m)^##\s+TASK\s+(?P<n>\d+)\s*[—\-:]"
)


def _parse_headings(markdown: str) -> list[tuple[int, str, int]]:
    """Return ``[(level, text, line_no), ...]`` for ATX headings.

    Fenced code blocks are skipped so example handovers / commit tables
    inside fences cannot satisfy the contract by accident.
    """
    headings: list[tuple[int, str, int]] = []
    in_fence = False
    for line_no, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).rstrip("#").strip()
            headings.append((level, text, line_no))
    return headings


def _section_text(markdown: str, h2_title: str) -> str | None:
    """Return the slice of markdown under ``## <h2_title>``.

    The slice runs from the heading's next line to (but not including)
    the next ``##`` heading, or end-of-file. Returns ``None`` if the
    heading is not present.
    """
    pattern = re.compile(
        r"(?ms)^##\s+" + re.escape(h2_title) + r"\s*$(?P<body>.*?)(?=^##\s|\Z)"
    )
    match = pattern.search(markdown)
    if match is None:
        return None
    return match.group("body")


def _git_history_block(markdown: str) -> str | None:
    """Return the contents of the first fenced block under ``### Git History``.

    Looks only inside the ``## WHAT EXISTS TODAY`` section so an example
    code fence elsewhere in the document does not satisfy the contract.
    Returns ``None`` if the section or fence is absent.
    """
    section = _section_text(markdown, "WHAT EXISTS TODAY")
    if section is None:
        return None
    history_re = re.compile(
        r"(?ms)^###\s+Git History\s*$(?P<body>.*?)(?=^###\s|^##\s|\Z)"
    )
    match = history_re.search(section)
    if match is None:
        return None
    body = match.group("body")
    fence_re = re.compile(r"(?ms)^```[^\n]*\n(?P<inner>.*?)^```")
    fence_match = fence_re.search(body)
    if fence_match is None:
        return None
    return fence_match.group("inner")


def _reference_documents_block(markdown: str) -> str | None:
    """Return the bullet-list slice that follows ``**Reference Documents:**``.

    Slice ends at the first blank line followed by a non-bullet line, or
    at the next ``---`` rule, or at end-of-section.
    """
    section = _section_text(markdown, "CONTEXT — READ THIS FIRST")
    if section is None:
        return None
    marker_re = re.compile(r"(?m)^\*\*Reference Documents:\*\*\s*$")
    marker = marker_re.search(section)
    if marker is None:
        return None
    after = section[marker.end():]
    # Capture the contiguous block of bullet lines (and any continuation
    # lines indented under them) up to the next blank-paragraph boundary.
    lines: list[str] = []
    seen_bullet = False
    for raw in after.splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            seen_bullet = True
            lines.append(raw)
            continue
        if seen_bullet and stripped == "":
            # Blank line ends the bullet block.
            break
        if seen_bullet:
            # Allow indented continuation; otherwise stop.
            if raw.startswith(" "):
                lines.append(raw)
                continue
            break
    return "\n".join(lines) if lines else ""


def check_metadata_identity(
    markdown: str,
    *,
    expected_id: str,
    expected_date: str,
    expected_previous: str,
) -> list[PostgenError]:
    """Check 1 — id, date, previous_handover all match expectations.

    The three lines must appear inside ``## CONTEXT — READ THIS FIRST``.
    A missing line and a mismatched value are both blocking; the
    operator response differs (planner template drift vs. wrong inputs)
    so the messages distinguish them.
    """
    errors: list[PostgenError] = []
    section = _section_text(markdown, "CONTEXT — READ THIS FIRST")
    if section is None:
        errors.append(
            PostgenError(
                check="1_metadata_identity",
                message=(
                    "missing required section '## CONTEXT — READ THIS FIRST'; "
                    "cannot validate metadata identity"
                ),
            )
        )
        return errors

    for label, regex, expected in (
        ("id", _ID_RE, expected_id),
        ("date", _DATE_RE, expected_date),
        ("previous_handover", _PREVIOUS_RE, expected_previous),
    ):
        match = regex.search(section)
        if match is None:
            errors.append(
                PostgenError(
                    check="1_metadata_identity",
                    message=(
                        f"missing `**{label}:** <value>` line in "
                        "'## CONTEXT — READ THIS FIRST'"
                    ),
                )
            )
            continue
        actual = match.group(match.lastindex or 1)
        if actual != expected:
            errors.append(
                PostgenError(
                    check="1_metadata_identity",
                    message=(
                        f"{label} mismatch: draft declares {actual!r}, "
                        f"expected {expected!r}"
                    ),
                )
            )
    return errors


def check_required_sections(markdown: str) -> list[PostgenError]:
    """Check 2 — every required ``##`` heading is present and ``### Git
    History`` lives under ``## WHAT EXISTS TODAY``.
    """
    errors: list[PostgenError] = []
    headings = _parse_headings(markdown)
    h2_texts = {text for level, text, _ in headings if level == 2}
    for required in REQUIRED_H2_HEADINGS:
        if required not in h2_texts:
            errors.append(
                PostgenError(
                    check="2_required_sections",
                    message=f"missing required heading '## {required}'",
                )
            )

    # Build (h3, parent_h2) pairs to validate placement.
    h3_pairs: list[tuple[str, str | None]] = []
    current_h2: str | None = None
    for level, text, _ in headings:
        if level == 2:
            current_h2 = text
        elif level == 3:
            h3_pairs.append((text, current_h2))
    for required_h3, required_parent in REQUIRED_H3_UNDER:
        matches = [pair for pair in h3_pairs if pair[0] == required_h3]
        if not matches:
            errors.append(
                PostgenError(
                    check="2_required_sections",
                    message=(
                        f"missing required heading '### {required_h3}' "
                        f"(must appear under '## {required_parent}')"
                    ),
                )
            )
            continue
        if not any(parent == required_parent for _, parent in matches):
            found = [parent or "(document root)" for _, parent in matches]
            errors.append(
                PostgenError(
                    check="2_required_sections",
                    message=(
                        f"'### {required_h3}' present but not under "
                        f"'## {required_parent}' (found under: "
                        f"{', '.join(found)})"
                    ),
                )
            )
    return errors


def check_git_history_integrity(
    markdown: str,
    *,
    expected_lines: Sequence[str],
) -> list[PostgenError]:
    """Check 3 — every expected commit line appears verbatim inside the
    ``### Git History`` fenced block.

    Order is not enforced (the planner is free to render newest-first or
    oldest-first), but each expected line must match byte-for-byte. If
    no expected lines are supplied this check is a no-op — the caller is
    responsible for passing the active phase's git history.
    """
    if not expected_lines:
        return []
    block = _git_history_block(markdown)
    if block is None:
        return [
            PostgenError(
                check="3_git_history_integrity",
                message=(
                    "missing fenced '### Git History' block under "
                    "'## WHAT EXISTS TODAY'"
                ),
            )
        ]
    actual_lines = set(block.splitlines())
    errors: list[PostgenError] = []
    for expected in expected_lines:
        if expected not in actual_lines:
            errors.append(
                PostgenError(
                    check="3_git_history_integrity",
                    message=(
                        "expected commit line missing from "
                        f"'### Git History' block: {expected!r}"
                    ),
                )
            )
    return errors


def check_reference_doc_hygiene(markdown: str) -> list[PostgenError]:
    """Check 4 — Reference Documents list is non-empty and free of
    unresolved ``[future-doc:]`` / ``[future-path:]`` tags.
    """
    errors: list[PostgenError] = []
    block = _reference_documents_block(markdown)
    if block is None:
        return [
            PostgenError(
                check="4_reference_doc_hygiene",
                message=(
                    "missing '**Reference Documents:**' marker in "
                    "'## CONTEXT — READ THIS FIRST'"
                ),
            )
        ]
    bullet_lines = [
        line for line in block.splitlines() if line.strip().startswith("- ")
    ]
    if not bullet_lines:
        errors.append(
            PostgenError(
                check="4_reference_doc_hygiene",
                message=(
                    "'**Reference Documents:**' list is empty; canonical "
                    "promotion requires at least one reference"
                ),
            )
        )
    future_hits = _FUTURE_TAG_RE.findall(block)
    for hit in future_hits:
        errors.append(
            PostgenError(
                check="4_reference_doc_hygiene",
                message=(
                    "unresolved future tag in 'Reference Documents' "
                    f"block: {hit!r}; future references must be closed "
                    "before promotion"
                ),
            )
        )
    return errors


def check_hard_rules_presence(
    markdown: str,
    *,
    required_phrases: Sequence[str],
) -> list[PostgenError]:
    """Check 5 — every required invariant phrase appears in
    ``## HARD RULES``.

    The caller passes the safety-critical phrases for the active slice
    (e.g. for Slice 8: a no-LLM-judge marker, a FAILED_CANDIDATE marker,
    and a slice-scope-limit marker). If no phrases are supplied this
    check is a no-op — the caller is responsible for declaring which
    invariants must be present.
    """
    if not required_phrases:
        return []
    section = _section_text(markdown, "HARD RULES")
    if section is None:
        return [
            PostgenError(
                check="5_hard_rules_presence",
                message=(
                    "missing required section '## HARD RULES'; cannot "
                    "validate slice invariants"
                ),
            )
        ]
    errors: list[PostgenError] = []
    for phrase in required_phrases:
        if phrase not in section:
            errors.append(
                PostgenError(
                    check="5_hard_rules_presence",
                    message=(
                        "'## HARD RULES' missing required invariant "
                        f"phrase: {phrase!r}"
                    ),
                )
            )
    return errors


def check_task_closure(
    markdown: str,
    *,
    expected_task_count: int,
) -> list[PostgenError]:
    """Check 6 — Task overview and per-task sections are consistent.

    Verifies (a) ``## TASK OVERVIEW`` has at least ``expected_task_count``
    numbered rows and (b) a ``## TASK N —`` section exists for each
    1..expected_task_count. Title text is not asserted (titles drift
    legitimately between drafts); structural closure is.
    """
    errors: list[PostgenError] = []
    overview = _section_text(markdown, "TASK OVERVIEW")
    if overview is None:
        errors.append(
            PostgenError(
                check="6_task_closure",
                message="missing required section '## TASK OVERVIEW'",
            )
        )
    else:
        row_numbers = {int(m.group("n")) for m in _TASK_ROW_RE.finditer(overview)}
        for n in range(1, expected_task_count + 1):
            if n not in row_numbers:
                errors.append(
                    PostgenError(
                        check="6_task_closure",
                        message=(
                            f"'## TASK OVERVIEW' table missing row for "
                            f"task {n}"
                        ),
                    )
                )

    task_heading_numbers = {
        int(m.group("n")) for m in _TASK_HEADING_RE.finditer(markdown)
    }
    for n in range(1, expected_task_count + 1):
        if n not in task_heading_numbers:
            errors.append(
                PostgenError(
                    check="6_task_closure",
                    message=f"missing required section '## TASK {n} — <Title>'",
                )
            )
    return errors


def validate_postgen(
    draft_markdown: str,
    *,
    expected_id: str,
    expected_previous: str,
    expected_date: str,
    expected_git_history_lines: Sequence[str],
    required_hard_rule_phrases: Sequence[str] = (),
    expected_task_count: int = 3,
) -> PostgenResult:
    """Run all six post-generation checks and return a structured result.

    Checks run independently; the function does not short-circuit so the
    operator sees every blocking issue in a single ``FAILED_CANDIDATE``
    artifact. ``ok`` is true iff every check passed.
    """
    errors: list[PostgenError] = []
    errors.extend(
        check_metadata_identity(
            draft_markdown,
            expected_id=expected_id,
            expected_date=expected_date,
            expected_previous=expected_previous,
        )
    )
    errors.extend(check_required_sections(draft_markdown))
    errors.extend(
        check_git_history_integrity(
            draft_markdown,
            expected_lines=expected_git_history_lines,
        )
    )
    errors.extend(check_reference_doc_hygiene(draft_markdown))
    errors.extend(
        check_hard_rules_presence(
            draft_markdown,
            required_phrases=required_hard_rule_phrases,
        )
    )
    errors.extend(
        check_task_closure(
            draft_markdown,
            expected_task_count=expected_task_count,
        )
    )
    return PostgenResult(ok=not errors, errors=tuple(errors))


def format_errors(errors: Iterable[PostgenError]) -> str:
    """Render a deterministic, multi-line error block for operator output.

    Format is ``- [<check_id>] <message>`` per line. The generator script
    is free to wrap or prefix this; postgen itself never prints.
    """
    return "\n".join(f"- [{error.check}] {error.message}" for error in errors)
