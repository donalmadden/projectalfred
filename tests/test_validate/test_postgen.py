"""Slice-8 post-generation validator tests.

Coverage:

- One isolated negative test per check (1–6), each crafting a minimal
  draft that fails exactly one check and asserting the structured
  ``check`` id and a fixture-derived error message.
- ``ValueError`` guards on the orchestrator's two non-default sequence
  parameters (``required_hard_rule_phrases`` and ``required_task_markers``)
  so neither Check-5 nor Check-6 can silently no-op.
- A known-good regression: ``docs/canonical/ALFRED_HANDOVER_12.md``
  passes ``validate_postgen`` against a notional brief constructed
  in-test.
- An orchestrator non-short-circuit assertion: a draft that fails every
  check yields one error per check id in a single pass.
- A shape lock for ``format_postgen_errors`` (one ``- [<check>] <msg>``
  line per error).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from alfred.validate import (  # noqa: E402
    PostgenError,
    PostgenResult,
    format_postgen_errors,
    validate_postgen,
)
from alfred.validate.postgen import (  # noqa: E402
    check_git_history_integrity,
    check_hard_rules_presence,
    check_metadata_identity,
    check_reference_doc_hygiene,
    check_required_sections,
    check_task_closure,
)

# ---------------------------------------------------------------------------
# Minimal passing draft — every negative test mutates exactly one thing.
# ---------------------------------------------------------------------------


_GIT_LINE = "abc1234  fixture commit for postgen test"


def _minimal_passing_draft(
    *,
    handover_id: str = "ALFRED_HANDOVER_777",
    previous_handover: str = "ALFRED_HANDOVER_776",
    date: str = "2026-05-07",
    git_line: str = _GIT_LINE,
) -> str:
    """Return a deterministic draft that passes all six checks against
    the matching expectations.

    Anchors used: ``Slice 8`` in HARD RULES, and three task markers
    (``MODULE_A``, ``MODULE_B``, ``MODULE_C``) one per task body. The
    draft is intentionally short — every line carries a checked
    invariant.
    """
    return (
        "# Fixture handover\n\n"
        "## CONTEXT — READ THIS FIRST\n\n"
        f"**id:** {handover_id}\n"
        f"**date:** {date}\n"
        f"**previous_handover:** {previous_handover}\n\n"
        "**Reference Documents:**\n"
        "- `docs/x.md` — fixture reference.\n\n"
        "## WHAT EXISTS TODAY\n\n"
        "### Git History\n\n"
        f"```\n{git_line}\n```\n\n"
        "## HARD RULES\n\n"
        "1. Slice 8 only: fixture invariant.\n\n"
        "## WHAT THIS PHASE PRODUCES\n\n- fixture deliverable.\n\n"
        "## TASK OVERVIEW\n\n"
        "| # | Task | Deliverable | Checkpoint decides |\n"
        "|---|---|---|---|\n"
        "| 1 | t1 covers MODULE_A | d | CHECKPOINT-1 |\n"
        "| 2 | t2 covers MODULE_B | d | CHECKPOINT-2 |\n"
        "| 3 | t3 covers MODULE_C | d | CHECKPOINT-3 |\n\n"
        "## TASK 1 — t1\n\nbody mentions MODULE_A here.\n\n"
        "## TASK 2 — t2\n\nbody mentions MODULE_B here.\n\n"
        "## TASK 3 — t3\n\nbody mentions MODULE_C here.\n\n"
        "## WHAT NOT TO DO\n\n1. nope.\n\n"
        "## POST-MORTEM\n\nbody.\n\n"
        f"**next_handover_id:** ALFRED_HANDOVER_778\n"
    )


def _passing_inputs(handover_id: str = "ALFRED_HANDOVER_777") -> dict:
    """Default keyword inputs that match the minimal passing draft."""
    return dict(
        expected_id=handover_id,
        expected_previous="ALFRED_HANDOVER_776",
        expected_date="2026-05-07",
        expected_git_history_lines=[_GIT_LINE],
        required_hard_rule_phrases=["Slice 8"],
        required_task_markers=[["MODULE_A"], ["MODULE_B"], ["MODULE_C"]],
    )


def test_minimal_passing_draft_is_actually_passing() -> None:
    """Self-check the fixture: the minimal-passing draft really does pass.

    If this test fails, every negative test below is potentially
    misleading because the failure they observe might come from drift
    in the fixture, not the mutation under test.
    """
    result = validate_postgen(_minimal_passing_draft(), **_passing_inputs())
    assert result.ok is True, format_postgen_errors(result.errors)
    assert result.errors == ()


# ---------------------------------------------------------------------------
# Isolated negative tests — one per check.
# ---------------------------------------------------------------------------


def test_check_1_flags_id_mismatch() -> None:
    """Check 1 names both the declared id and the expected id."""
    bad = _minimal_passing_draft(handover_id="ALFRED_HANDOVER_999")

    errors = check_metadata_identity(
        bad,
        expected_id="ALFRED_HANDOVER_777",
        expected_date="2026-05-07",
        expected_previous="ALFRED_HANDOVER_776",
    )

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "1_metadata_identity"
    assert "ALFRED_HANDOVER_999" in error.message
    assert "ALFRED_HANDOVER_777" in error.message


def test_check_1_flags_missing_previous_line() -> None:
    """Check 1 catches a silently dropped ``previous_handover`` line."""
    base = _minimal_passing_draft()
    bad = re.sub(r"(?m)^\*\*previous_handover:\*\*.*\n", "", base)

    errors = check_metadata_identity(
        bad,
        expected_id="ALFRED_HANDOVER_777",
        expected_date="2026-05-07",
        expected_previous="ALFRED_HANDOVER_776",
    )

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "1_metadata_identity"
    assert "previous_handover" in error.message
    # The other two metadata lines must NOT be flagged.
    assert "id mismatch" not in error.message
    assert "date mismatch" not in error.message


def test_check_2_flags_missing_required_heading() -> None:
    """Dropping ``## HARD RULES`` triggers Check 2 with a precise message."""
    base = _minimal_passing_draft()
    bad = re.sub(
        r"(?ms)^## HARD RULES\s*$.*?(?=^## )", "", base, count=1
    )

    errors = check_required_sections(bad)

    check_ids = {e.check for e in errors}
    messages = "\n".join(e.message for e in errors)
    assert "2_required_sections" in check_ids
    assert "## HARD RULES" in messages
    # Other required headings remain present and must NOT be flagged.
    assert "## CONTEXT — READ THIS FIRST" not in messages
    assert "## TASK OVERVIEW" not in messages


def test_check_3_flags_altered_git_history_line() -> None:
    """Altering a tracked commit line surfaces it as missing byte-for-byte."""
    bad = _minimal_passing_draft(git_line="dead beef  altered commit")

    errors = check_git_history_integrity(
        bad,
        expected_lines=[_GIT_LINE],
    )

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "3_git_history_integrity"
    assert _GIT_LINE in error.message
    # The actual fenced content must not be reported as a "found" line —
    # only the expected line is referenced in the error.
    assert "dead beef" not in error.message


def test_check_4_flags_empty_reference_documents_block() -> None:
    """An empty Reference Documents block is a closure failure."""
    base = _minimal_passing_draft()
    bad = base.replace(
        "**Reference Documents:**\n- `docs/x.md` — fixture reference.\n",
        "**Reference Documents:**\n",
    )

    errors = check_reference_doc_hygiene(bad)

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "4_reference_doc_hygiene"
    assert "empty" in error.message.lower()


def test_check_4_flags_unresolved_future_tag() -> None:
    """A ``[future-doc:]`` tag inside Reference Documents blocks promotion."""
    base = _minimal_passing_draft()
    bad = base.replace(
        "- `docs/x.md` — fixture reference.\n",
        "- [future-doc: docs/y.md] — pending closure.\n",
    )

    errors = check_reference_doc_hygiene(bad)

    assert any(
        e.check == "4_reference_doc_hygiene"
        and "future-doc" in e.message
        and "docs/y.md" in e.message
        for e in errors
    )


def test_check_5_flags_missing_anchor_phrase() -> None:
    """Check 5 names the missing invariant phrase verbatim."""
    base = _minimal_passing_draft()
    bad = base.replace("Slice 8 only: fixture invariant.", "no anchors here.")

    errors = check_hard_rules_presence(
        bad, required_phrases=["Slice 8", "FAILED_CANDIDATE"]
    )

    check_ids = {e.check for e in errors}
    assert check_ids == {"5_hard_rules_presence"}
    messages = "\n".join(e.message for e in errors)
    assert "'Slice 8'" in messages
    assert "'FAILED_CANDIDATE'" in messages


def test_check_6_flags_task_with_no_brief_marker_in_row_or_section() -> None:
    """A task that drops its topic anchor is caught as brief drift."""
    base = _minimal_passing_draft()
    # Wipe every mention of MODULE_C from the table row and the task
    # body so neither survives as an anchor.
    bad = base.replace(
        "| 3 | t3 covers MODULE_C | d | CHECKPOINT-3 |",
        "| 3 | t3 covers something else | d | CHECKPOINT-3 |",
    ).replace(
        "## TASK 3 — t3\n\nbody mentions MODULE_C here.",
        "## TASK 3 — t3\n\nbody mentions only something else.",
    )

    errors = check_task_closure(
        bad,
        required_task_markers=[["MODULE_A"], ["MODULE_B"], ["MODULE_C"]],
    )

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "6_task_closure"
    assert "task 3" in error.message
    assert "MODULE_C" in error.message
    # Tasks 1 and 2 still map; their markers must NOT appear in the error.
    assert "MODULE_A" not in error.message
    assert "MODULE_B" not in error.message


def test_check_6_flags_missing_task_section() -> None:
    """A missing ``## TASK N —`` heading is reported even if the row exists."""
    base = _minimal_passing_draft()
    bad = re.sub(
        r"(?ms)^## TASK 2 — t2\s*$.*?(?=^## )", "", base, count=1
    )

    errors = check_task_closure(
        bad,
        required_task_markers=[["MODULE_A"], ["MODULE_B"], ["MODULE_C"]],
    )

    messages = [e.message for e in errors]
    assert any(
        e.check == "6_task_closure"
        and "## TASK 2" in e.message
        and "<Title>" in e.message
        for e in errors
    ), messages


# ---------------------------------------------------------------------------
# ValueError guards on the orchestrator surface — fixed-six-checks contract.
# ---------------------------------------------------------------------------


def test_validate_postgen_rejects_empty_hard_rule_phrases() -> None:
    """Check 5 must never silently no-op."""
    inputs = _passing_inputs()
    inputs["required_hard_rule_phrases"] = []

    with pytest.raises(ValueError) as excinfo:
        validate_postgen(_minimal_passing_draft(), **inputs)

    assert "required_hard_rule_phrases" in str(excinfo.value)
    assert "Check 5" in str(excinfo.value)


def test_validate_postgen_rejects_empty_task_markers() -> None:
    """Check 6 must never silently skip task-to-brief mapping."""
    inputs = _passing_inputs()
    inputs["required_task_markers"] = []

    with pytest.raises(ValueError) as excinfo:
        validate_postgen(_minimal_passing_draft(), **inputs)

    assert "required_task_markers" in str(excinfo.value)
    assert "Check 6" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Known-good regression — a real prior canonical handover passes postgen.
# ---------------------------------------------------------------------------


def test_real_handover_12_passes_postgen_against_a_notional_brief() -> None:
    """``docs/canonical/ALFRED_HANDOVER_12.md`` passes against a notional
    brief reconstructed in-test.

    The brief reconstruction is intentionally deterministic and local:
    a small set of anchor substrings that the real handover is known to
    contain. This guards against regressions that would tighten postgen
    until known-good drafts can no longer be promoted.
    """
    handover_path = ROOT / "docs/canonical/ALFRED_HANDOVER_12.md"
    markdown = handover_path.read_text(encoding="utf-8")

    # Pull the actual fenced git-history block so the byte-for-byte
    # check (Check 3) is decoupled from current HEAD movement.
    fence_match = re.search(
        r"### Git History\s*\n+```\s*\n(.*?)\n```",
        markdown,
        re.DOTALL,
    )
    assert fence_match is not None, "fixture must contain a git-history fence"
    git_history_lines = fence_match.group(1).splitlines()
    assert len(git_history_lines) >= 5  # sanity-check the fence content

    # Notional brief anchors (handover 12 verifiably contains each):
    hard_rule_anchors = [
        "orchestrate",  # rule 1: "Do not bypass `orchestrate(...)`"
        "approval",     # rule 2: "without a visible approval gate"
        "GitHub",       # rule 3: "the GitHub Project as the source of truth"
    ]
    # Per-task brief markers (handover 12 has 4 tasks). Each list is
    # any-match: at least one substring must appear in the row+section
    # combined text.
    task_markers = [
        ["operator demo script", "demo script"],
        ["preflight"],
        ["evidence"],
        ["rehearsal"],
    ]

    result = validate_postgen(
        markdown,
        expected_id="ALFRED_HANDOVER_12",
        expected_previous="ALFRED_HANDOVER_11",
        expected_date="2026-04-30",
        expected_git_history_lines=git_history_lines,
        required_hard_rule_phrases=hard_rule_anchors,
        required_task_markers=task_markers,
    )

    assert result.ok is True, format_postgen_errors(result.errors)
    assert result.errors == ()


# ---------------------------------------------------------------------------
# Orchestrator: every check runs, no short-circuit.
# ---------------------------------------------------------------------------


def test_validate_postgen_collects_every_check_id_without_short_circuiting() -> None:
    """A draft that fails every check yields one error per check id.

    Locks the orchestrator's "report all blocking issues in one pass"
    contract so a regression that adds short-circuit logic is caught.
    """
    # Bad enough to fail all six: wrong id, missing CONTEXT means we
    # also lose the ``Reference Documents`` block (Check 4) and the
    # required-heading scan (Check 2); empty git history block fails
    # Check 3; HARD RULES section without the anchor fails Check 5;
    # task overview missing tasks fails Check 6.
    bad = (
        "# title\n\n"
        "## WHAT EXISTS TODAY\n\n"
        "### Git History\n\n"
        "```\nzzzzzzz  unrelated commit\n```\n\n"
        "## HARD RULES\n\n1. no anchors here.\n\n"
        "## TASK OVERVIEW\n\n(no rows here)\n\n"
        "## WHAT NOT TO DO\n\n1. n.\n"
    )

    result = validate_postgen(
        bad,
        expected_id="ALFRED_HANDOVER_777",
        expected_previous="ALFRED_HANDOVER_776",
        expected_date="2026-05-07",
        expected_git_history_lines=[_GIT_LINE],
        required_hard_rule_phrases=["Slice 8"],
        required_task_markers=[["MODULE_A"], ["MODULE_B"], ["MODULE_C"]],
    )

    assert result.ok is False
    seen = {e.check for e in result.errors}
    expected = {
        "1_metadata_identity",
        "2_required_sections",
        "3_git_history_integrity",
        "4_reference_doc_hygiene",
        "5_hard_rules_presence",
        "6_task_closure",
    }
    assert expected.issubset(seen), (
        f"Missing checks: {expected - seen}; full set: {seen}"
    )


# ---------------------------------------------------------------------------
# Result + format_errors shape locks.
# ---------------------------------------------------------------------------


def test_postgen_result_ok_tracks_zero_errors() -> None:
    """``ok`` is exactly ``not errors``."""
    happy = validate_postgen(_minimal_passing_draft(), **_passing_inputs())
    assert isinstance(happy, PostgenResult)
    assert happy.ok is True
    assert happy.errors == ()

    sad = validate_postgen(
        _minimal_passing_draft(handover_id="ALFRED_HANDOVER_999"),
        **_passing_inputs(),
    )
    assert sad.ok is False
    assert len(sad.errors) >= 1


def test_format_postgen_errors_renders_one_line_per_error() -> None:
    """Operator-facing surface: lock the line shape."""
    rendered = format_postgen_errors(
        [
            PostgenError(check="1_metadata_identity", message="id mismatch x"),
            PostgenError(check="6_task_closure", message="task 3 drift y"),
        ]
    )
    lines = rendered.splitlines()
    assert lines == [
        "- [1_metadata_identity] id mismatch x",
        "- [6_task_closure] task 3 drift y",
    ]
