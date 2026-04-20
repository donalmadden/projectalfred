"""Tests for ``scripts/validate_alfred_planning_facts.py``.

Each test constructs a minimal markdown fixture and asserts the validator's
error list. The validator is scoped to current-state sections only, so
future-tense sections can contain proposals without false positives.
"""
from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from validate_alfred_planning_facts import validate  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal markdown fixtures
# ---------------------------------------------------------------------------


def _wrap_current_state(body: str, *, context_extra: str = "") -> str:
    """Place ``body`` under ``## WHAT EXISTS TODAY`` with a minimal context header."""
    parts = [
        "## CONTEXT — READ THIS FIRST",
        "**id:** ALFRED_HANDOVER_6_DRAFT",
        "**date:** 2026-04-20",
        "**previous_handover:** ALFRED_HANDOVER_5",
    ]
    if context_extra:
        parts.append(context_extra)
    parts.extend(["", "## WHAT EXISTS TODAY", body, ""])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Path existence checks (R2: invented module paths)
# ---------------------------------------------------------------------------


def test_flags_nonexistent_subpackage_reference() -> None:
    md = _wrap_current_state("The codebase includes `src/alfred/state/` module.")
    errors = validate(md)
    assert any("src/alfred/state" in e for e in errors)


def test_accepts_real_existing_path() -> None:
    md = _wrap_current_state("FastAPI lives in `src/alfred/api.py`.")
    errors = validate(md)
    assert not any("src/alfred/api.py" in e for e in errors)


def test_does_not_flag_negated_path_claim() -> None:
    md = _wrap_current_state(
        "`src/alfred/api/main.py` does not exist — the app is a single file."
    )
    errors = validate(md)
    # The negated mention must not be flagged as a hallucination...
    negated_path_errs = [e for e in errors if "src/alfred/api/main.py" in e and "does not exist in the repo" in e]
    assert not negated_path_errs


def test_does_not_flag_future_tense_section() -> None:
    md = dedent(
        """\
        ## CONTEXT — READ THIS FIRST
        **id:** X
        ## WHAT THIS PHASE PRODUCES
        Will add `src/alfred/state/` for state persistence.
        """
    )
    errors = validate(md)
    assert not any("src/alfred/state" in e for e in errors)


# ---------------------------------------------------------------------------
# API topology checks (R3: wrong FastAPI path; R4: wrong endpoint count)
# ---------------------------------------------------------------------------


def test_flags_directory_style_api_reference() -> None:
    md = _wrap_current_state("The FastAPI app lives in `src/alfred/api/main.py`.")
    errors = validate(md)
    assert any("src/alfred/api.py" in e for e in errors)


def test_flags_wrong_endpoint_count() -> None:
    md = _wrap_current_state("The API exposes 5 endpoints.")
    errors = validate(md)
    assert any("5 endpoints" in e for e in errors)


def test_flags_wrong_endpoint_count_as_word() -> None:
    md = _wrap_current_state("The API exposes five endpoints.")
    errors = validate(md)
    assert any("5 endpoints" in e for e in errors)


# ---------------------------------------------------------------------------
# Agent roster checks (R5: wrong agent names)
# ---------------------------------------------------------------------------


def test_flags_planner_executor_reviewer_enumeration() -> None:
    md = _wrap_current_state(
        "The system uses planner, executor, reviewer, and summariser agents."
    )
    errors = validate(md)
    assert any("planner, executor, reviewer" in e for e in errors)


def test_flags_backticked_executor_module() -> None:
    md = _wrap_current_state("See `src/alfred/agents/executor.py` for details.")
    errors = validate(md)
    assert any("executor" in e for e in errors)


def test_does_not_flag_bare_role_word_executor() -> None:
    # "executor" as a methodology role word (from property 3) must not be flagged.
    md = _wrap_current_state(
        "The executor never makes strategic decisions — this is methodology property 3."
    )
    errors = validate(md)
    # Only the enumeration/backtick patterns should flag; a bare role-word use
    # in prose is legitimate.
    assert not any(
        "executor" in e and "agent" in e.lower() for e in errors
    )


# ---------------------------------------------------------------------------
# Type checker check (R6: mypy claim)
# ---------------------------------------------------------------------------


def test_flags_mypy_in_current_state() -> None:
    md = _wrap_current_state("Type checking is handled by mypy.")
    errors = validate(md)
    assert any("mypy" in e and "pyright" in e for e in errors)


def test_does_not_flag_negated_mypy_mention() -> None:
    md = _wrap_current_state("Note: mypy is not used; the repo uses pyright.")
    errors = validate(md)
    assert not any("Phase 6 explicitly forbids" in e for e in errors)


# ---------------------------------------------------------------------------
# Top-level package checks (R7)
# ---------------------------------------------------------------------------


def test_flags_rag_subpackage_when_absent() -> None:
    md = _wrap_current_state("The `src/alfred/rag/` package handles retrieval.")
    errors = validate(md)
    assert any("src/alfred/rag" in e for e in errors)


# ---------------------------------------------------------------------------
# pyproject.toml checks (R8)
# ---------------------------------------------------------------------------


def test_flags_claim_pyproject_missing_when_present() -> None:
    md = _wrap_current_state("pyproject.toml does not exist yet; we need to create it.")
    errors = validate(md)
    assert any("pyproject.toml" in e and "[project]=True" in e for e in errors)


# ---------------------------------------------------------------------------
# Metadata checks (R1: wrong id/date/previous)
# ---------------------------------------------------------------------------


def test_flags_mismatched_id_against_filename(tmp_path: Path) -> None:
    md = dedent(
        """\
        ## CONTEXT — READ THIS FIRST
        **id:** ALFRED_HANDOVER_7
        **date:** 2026-04-20
        **previous_handover:** ALFRED_HANDOVER_5

        ## WHAT EXISTS TODAY
        Nothing notable.
        """
    )
    path = tmp_path / "ALFRED_HANDOVER_6_DRAFT.md"
    path.write_text(md, encoding="utf-8")
    errors = validate(md, source_path=path)
    assert any("ALFRED_HANDOVER_7" in e for e in errors)


def test_flags_wrong_expected_date() -> None:
    md = dedent(
        """\
        ## CONTEXT — READ THIS FIRST
        **id:** ALFRED_HANDOVER_6_DRAFT
        **date:** 2025-01-31
        **previous_handover:** ALFRED_HANDOVER_5

        ## WHAT EXISTS TODAY
        Nothing notable.
        """
    )
    errors = validate(md, expected_date="2026-04-20")
    assert any("2025-01-31" in e and "2026-04-20" in e for e in errors)


def test_flags_wrong_expected_previous() -> None:
    md = dedent(
        """\
        ## CONTEXT — READ THIS FIRST
        **id:** ALFRED_HANDOVER_6_DRAFT
        **date:** 2026-04-20
        **previous_handover:** ALFRED_HANDOVER_4

        ## WHAT EXISTS TODAY
        Nothing notable.
        """
    )
    errors = validate(md, expected_previous="ALFRED_HANDOVER_5")
    assert any("ALFRED_HANDOVER_4" in e and "ALFRED_HANDOVER_5" in e for e in errors)


def test_accepts_correct_metadata() -> None:
    md = dedent(
        """\
        ## CONTEXT — READ THIS FIRST
        **id:** ALFRED_HANDOVER_6_DRAFT
        **date:** 2026-04-20
        **previous_handover:** ALFRED_HANDOVER_5

        ## WHAT EXISTS TODAY
        FastAPI lives in `src/alfred/api.py`.
        """
    )
    errors = validate(
        md,
        expected_id="ALFRED_HANDOVER_6",
        expected_previous="ALFRED_HANDOVER_5",
        expected_date="2026-04-20",
    )
    # Must accept both the bare id and the `_DRAFT` suffix.
    assert not any("ALFRED_HANDOVER_6_DRAFT" in e for e in errors)


# ---------------------------------------------------------------------------
# End-to-end: the known-bad draft fails, a corrected one passes.
# ---------------------------------------------------------------------------


def test_broken_draft_fixture_fails() -> None:
    broken = dedent(
        """\
        ## CONTEXT — READ THIS FIRST
        **id:** ALFRED_HANDOVER_7
        **date:** 2025-01-31
        **previous_handover:** ALFRED_HANDOVER_6

        ## WHAT EXISTS TODAY
        FastAPI lives in `src/alfred/api/main.py` with 5 endpoints.
        Agents include planner, executor, reviewer, and summariser.
        Type checking is via mypy.
        The `src/alfred/rag/` and `src/alfred/state/` packages handle retrieval and persistence.
        """
    )
    errors = validate(broken, expected_date="2026-04-20")
    # R1 (date), R2 (state), R3 (api/main.py), R4 (5 endpoints), R5 (roster),
    # R6 (mypy), R7 (rag/state).
    assert len(errors) >= 6


@pytest.mark.parametrize(
    "clean_body",
    [
        "FastAPI lives in `src/alfred/api.py`.",
        "See `src/alfred/agents/planner.py` for planner logic.",
        "`docs/architecture.md` describes the overall layout.",
    ],
)
def test_correct_current_state_claims_pass(clean_body: str) -> None:
    md = _wrap_current_state(clean_body)
    errors = validate(md)
    # Metadata fields are present but no expected_* args given, so no
    # path/roster/tooling error should fire on a clean body.
    assert not any(
        any(key in e for key in ("does not exist", "mypy", "executor"))
        for e in errors
    )
