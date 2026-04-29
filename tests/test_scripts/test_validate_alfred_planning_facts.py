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

from validate_alfred_planning_facts import (  # noqa: E402
    ClaimCategory,
    validate,
    validate_current_state_facts,
    validate_future_task_realism,
)

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


def _build_partial_state_repo(tmp_path: Path) -> Path:
    (tmp_path / "src" / "alfred" / "agents").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "tools").mkdir(parents=True)
    (tmp_path / "src" / "alfred").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "api.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        '@app.get("/dashboard")\n'
        "def dashboard(): ...\n",
        encoding="utf-8",
    )
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'alfred'\n"
        "[project.scripts]\nalfred = 'alfred.cli:main'\n"
        "[tool.pyright]\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "ALFRED_HANDOVER_6.md").write_text(
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_6\n"
        "**date:** 2026-04-20\n"
        "**author:** Planner\n\n"
        "## WHAT THIS PHASE PRODUCES\n"
        "- `.github/workflows/release.yml`\n"
        "- `src/alfred/schemas/health.py`\n"
        "- `docs/operations.md`\n"
        "- `GET /healthz`\n"
        "- `GET /readyz`\n",
        encoding="utf-8",
    )
    return tmp_path


_TYPE_CHECKER_TOOL_CONFIGS = {
    "basedpyright": "[tool.basedpyright]\n",
    "mypy": "[tool.mypy]\nstrict = true\n",
    "pyright": "[tool.pyright]\n",
}
_TYPE_CHECKER_CASES = (
    ("pyright", "mypy"),
    ("basedpyright", "pyright"),
)


def _build_type_checker_repo(tmp_path: Path, configured_tool: str) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'alfred'\n\n" + _TYPE_CHECKER_TOOL_CONFIGS[configured_tool],
        encoding="utf-8",
    )
    return tmp_path


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
# Type checker checks (R6: unexpected type-checker claim)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_flags_unconfigured_type_checker_in_current_state(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_current_state(f"Type checking is handled by {unexpected_tool}.")
    findings = validate_current_state_facts(md, repo_root=repo_root)
    tooling = [f for f in findings if f.category == ClaimCategory.CURRENT_TOOLING]
    assert tooling
    assert tooling[0].finding_object.claimed_tool == unexpected_tool
    assert tooling[0].finding_object.allowed_tool == configured_tool


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_does_not_flag_negated_unconfigured_type_checker_mention(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_current_state(
        f"Note: {unexpected_tool} is not used; the repo uses {configured_tool}."
    )
    findings = validate_current_state_facts(md, repo_root=repo_root)
    tooling = [f for f in findings if f.category == ClaimCategory.CURRENT_TOOLING]
    assert not tooling


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_does_not_flag_unconfigured_type_checker_described_as_hard_violation(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_current_state(
        f"Type checking uses `{configured_tool}`. Introducing `{unexpected_tool}` is a hard violation."
    )
    findings = validate_current_state_facts(md, repo_root=repo_root)
    tooling = [f for f in findings if f.category == ClaimCategory.CURRENT_TOOLING]
    assert not tooling


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_does_not_flag_unconfigured_type_checker_described_as_forbidden(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_current_state(
        f"The `{unexpected_tool}` tool is forbidden by hard rule; the repo uses `{configured_tool}`."
    )
    findings = validate_current_state_facts(md, repo_root=repo_root)
    tooling = [f for f in findings if f.category == ClaimCategory.CURRENT_TOOLING]
    assert not tooling


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_does_not_flag_markdown_formatted_negated_unconfigured_type_checker(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_current_state(
        f"Type checker: `{configured_tool}` (`{unexpected_tool}` is **not** in use and must not be referenced)."
    )
    findings = validate_current_state_facts(md, repo_root=repo_root)
    tooling = [f for f in findings if f.category == ClaimCategory.CURRENT_TOOLING]
    assert not tooling


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_does_not_flag_shorthand_negated_unconfigured_type_checker(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_current_state(
        f"Alfred canonical tooling: `{configured_tool}` for type checking; no `{unexpected_tool}`."
    )
    findings = validate_current_state_facts(md, repo_root=repo_root)
    tooling = [f for f in findings if f.category == ClaimCategory.CURRENT_TOOLING]
    assert not tooling


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
        Type checking is via basedpyright.
        The `src/alfred/rag/` and `src/alfred/state/` packages handle retrieval and persistence.
        """
    )
    errors = validate(broken, expected_date="2026-04-20")
    # R1 (date), R2 (state), R3 (api/main.py), R4 (5 endpoints), R5 (roster),
    # R6 (unexpected type checker), R7 (rag/state).
    assert len(errors) >= 6


@pytest.mark.parametrize(
    "clean_body",
    [
        "FastAPI lives in `src/alfred/api.py`.",
        "See `src/alfred/agents/planner.py` for planner logic.",
        "`docs/protocol/architecture.md` describes the overall layout.",
    ],
)
def test_correct_current_state_claims_pass(clean_body: str) -> None:
    md = _wrap_current_state(clean_body)
    errors = validate(md)
    # Metadata fields are present but no expected_* args given, so no
    # path/roster/tooling error should fire on a clean body.
    assert not any(
        any(key in e for key in ("does not exist", "type-checking toolchain", "executor"))
        for e in errors
    )


# ---------------------------------------------------------------------------
# A6 regression tests for known blind spots
# ---------------------------------------------------------------------------


def test_imperative_must_not_break_does_not_suppress_path_finding() -> None:
    # "must not break `src/alfred/state/`" — the path doesn't exist, so it
    # should still be flagged. The imperative negation must not suppress the finding.
    md = _wrap_current_state(
        "Care must not break `src/alfred/state/` during the migration."
    )
    findings = validate_current_state_facts(md)
    path_findings = [f for f in findings if "src/alfred/state" in f.evidence]
    assert path_findings, "Expected a finding for non-existent `src/alfred/state/`"
    assert path_findings[0].category == ClaimCategory.CURRENT_PATH


def test_existence_denial_suppresses_path_finding() -> None:
    # "`src/alfred/state/` does not exist" — negated, must not flag.
    md = _wrap_current_state(
        "`src/alfred/state/` does not exist yet; it will be added in Phase 4."
    )
    findings = validate_current_state_facts(md)
    path_findings = [f for f in findings if "src/alfred/state" in f.evidence]
    assert not path_findings, "Negated path claim must not produce a finding"


def test_complex_prose_with_embedded_clauses_is_still_negated() -> None:
    md = _wrap_current_state(
        "Although `src/alfred/state/`, which older drafts sometimes mention, "
        "does not exist today, `src/alfred/api.py` does."
    )
    findings = validate_current_state_facts(md)
    path_findings = [f for f in findings if "src/alfred/state" in f.evidence]
    assert not path_findings


def test_negation_with_unusual_punctuation_is_respected() -> None:
    md = _wrap_current_state("`src/alfred/state/` does not exist; do not refer to it as real.")
    findings = validate_current_state_facts(md)
    path_findings = [f for f in findings if "src/alfred/state" in f.evidence]
    assert not path_findings


def test_bad_reference_doc_path_flagged() -> None:
    # A docs path that doesn't exist in the inventory must be flagged as REFERENCE_DOC.
    md = _wrap_current_state(
        "See `docs/handovers/ALFRED_HANDOVER_5.md` for the previous session context."
    )
    findings = validate_current_state_facts(md)
    ref_findings = [f for f in findings if f.category == ClaimCategory.REFERENCE_DOC]
    assert ref_findings, "Expected REFERENCE_DOC finding for non-existent doc path"
    assert "docs/handovers/ALFRED_HANDOVER_5.md" in ref_findings[0].evidence


def test_good_reference_doc_path_passes() -> None:
    md = _wrap_current_state("See `docs/protocol/architecture.md` for architecture details.")
    findings = validate_current_state_facts(md)
    ref_findings = [f for f in findings if f.category == ClaimCategory.REFERENCE_DOC]
    assert not ref_findings, "Known-good architecture doc must not be flagged"


def test_explicit_future_doc_tag_skips_reference_doc_check() -> None:
    md = _wrap_current_state(
        "The external demo workspace starts with "
        "`docs/CHARTER.md` [future-doc: demo workspace path]."
    )
    findings = validate_current_state_facts(md)
    ref_findings = [f for f in findings if f.category == ClaimCategory.REFERENCE_DOC]
    assert not ref_findings, "Explicit future-doc tag must suppress inventory lookup"


def test_explicit_future_path_tag_skips_current_path_check() -> None:
    md = _wrap_current_state(
        "The external demo workspace begins with "
        "`docs/handovers/` [future-path: demo workspace directory]."
    )
    findings = validate_current_state_facts(md)
    path_findings = [f for f in findings if f.category == ClaimCategory.CURRENT_PATH]
    assert not path_findings, "Explicit future-path tag must suppress path existence lookup"


def test_reference_doc_missing_metadata_flagged(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "ALFRED_HANDOVER_6.md").write_text(
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## WHAT EXISTS TODAY\nReal state.\n",
        encoding="utf-8",
    )
    md = _wrap_current_state("See `docs/ALFRED_HANDOVER_6.md` for the current protocol.")
    findings = validate_current_state_facts(md, repo_root=tmp_path)
    ref_findings = [f for f in findings if f.category == ClaimCategory.REFERENCE_DOC]
    assert ref_findings
    assert any(
        getattr(f.finding_object, "issue_type", "") == "missing_metadata"
        for f in ref_findings
    )


def test_reference_doc_stale_warns_not_errors(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "ALFRED_HANDOVER_4.md").write_text(
        "# Alfred's Handover Document #4 — Phase 5\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_4\n"
        "**date:** 2025-01-01\n"
        "**author:** Planner\n\n"
        "## WHAT EXISTS TODAY\nReal state.\n\n"
        "## TASK OVERVIEW\nPlan.\n",
        encoding="utf-8",
    )
    md = dedent(
        """\
        ## CONTEXT — READ THIS FIRST
        **id:** ALFRED_HANDOVER_6_DRAFT
        **date:** 2026-04-21
        **previous_handover:** ALFRED_HANDOVER_5

        ## WHAT EXISTS TODAY
        See `docs/ALFRED_HANDOVER_4.md` for historical context.
        """
    )
    findings = validate_current_state_facts(md, repo_root=tmp_path)
    ref_findings = [f for f in findings if f.category == ClaimCategory.REFERENCE_DOC]
    assert ref_findings
    assert any(f.severity == "warning" for f in ref_findings)


def test_archived_reference_doc_is_not_citable_under_manifest(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "ALFRED_HANDOVER_6_old.md").write_text(
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_6_old\n"
        "**date:** 2026-04-20\n"
        "**author:** Planner\n\n"
        "## WHAT EXISTS TODAY\nReal state.\n\n"
        "## TASK OVERVIEW\nPlan.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "DOCS_MANIFEST.yaml").write_text(
        "manifest_version: 1\n"
        "documents:\n"
        "  - current_path: docs/ALFRED_HANDOVER_6_old.md\n"
        "    proposed_path: docs/archive/ALFRED_HANDOVER_6_old.md\n"
        "    indexed: false\n"
        "    citable: false\n"
        "    authoritative: false\n"
        "    lifecycle_status: archive\n",
        encoding="utf-8",
    )

    md = _wrap_current_state("See `docs/ALFRED_HANDOVER_6_old.md` for the previous snapshot.")
    findings = validate_current_state_facts(md, repo_root=tmp_path)
    ref_findings = [f for f in findings if f.category == ClaimCategory.REFERENCE_DOC]

    assert ref_findings
    assert "not citable under the docs lifecycle policy" in ref_findings[0].human_message


def test_cli_implemented_claim_flagged_when_cli_module_absent(tmp_path: Path) -> None:
    # Build a fake repo where pyproject.toml declares a CLI entry but cli.py is absent.
    (tmp_path / "src" / "alfred" / "agents").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "tools").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "api.py").write_text("", encoding="utf-8")
    pyproject = (
        "[project]\nname = 'alfred'\n"
        "[project.scripts]\nalfred = 'alfred.cli:main'\n"
        "[tool.pyright]\n"
    )
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    # cli.py is deliberately absent

    md = _wrap_current_state("The CLI is implemented and available via `alfred` command.")
    findings = validate_current_state_facts(md, repo_root=tmp_path)
    partial_findings = [f for f in findings if f.category == ClaimCategory.PARTIAL_STATE]
    assert partial_findings, "Expected PARTIAL_STATE finding for 'CLI is implemented' claim"


def test_cli_absence_claim_flagged_when_cli_declared(tmp_path: Path) -> None:
    # Same fake repo — CLI declared but not implemented — and draft says "no CLI".
    (tmp_path / "src" / "alfred" / "agents").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "tools").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "api.py").write_text("", encoding="utf-8")
    pyproject = (
        "[project]\nname = 'alfred'\n"
        "[project.scripts]\nalfred = 'alfred.cli:main'\n"
        "[tool.pyright]\n"
    )
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    md = _wrap_current_state("There is no CLI; no alfred CLI is available yet.")
    findings = validate_current_state_facts(md, repo_root=tmp_path)
    partial_findings = [f for f in findings if f.category == ClaimCategory.PARTIAL_STATE]
    assert partial_findings, "Expected PARTIAL_STATE finding for absence claim when CLI is declared"


def test_cli_declared_but_unimplemented_phrase_passes(tmp_path: Path) -> None:
    # The correct vocabulary "declared but unimplemented" must not produce a finding.
    (tmp_path / "src" / "alfred" / "agents").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "tools").mkdir(parents=True)
    (tmp_path / "src" / "alfred" / "api.py").write_text("", encoding="utf-8")
    pyproject = (
        "[project]\nname = 'alfred'\n"
        "[project.scripts]\nalfred = 'alfred.cli:main'\n"
        "[tool.pyright]\n"
    )
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    md = _wrap_current_state(
        "The CLI script entry is declared but unimplemented: "
        "`alfred.cli:main` appears in pyproject.toml but `src/alfred/cli.py` does not exist yet."
    )
    findings = validate_current_state_facts(md, repo_root=tmp_path)
    partial_findings = [f for f in findings if f.category == ClaimCategory.PARTIAL_STATE]
    assert not partial_findings, "Correct 'declared but unimplemented' vocabulary must not flag"


def test_workflow_planned_absence_claim_flagged(tmp_path: Path) -> None:
    repo_root = _build_partial_state_repo(tmp_path)
    md = _wrap_current_state("There is no planned release workflow yet.")
    findings = validate_current_state_facts(md, repo_root=repo_root)
    partial_findings = [f for f in findings if f.category == ClaimCategory.PARTIAL_STATE]
    assert partial_findings
    assert any(f.finding_object.state_type.value == "WORKFLOW" for f in partial_findings)


def test_schema_planned_absence_claim_flagged(tmp_path: Path) -> None:
    repo_root = _build_partial_state_repo(tmp_path)
    md = _wrap_current_state("The health schema is not planned yet.")
    findings = validate_current_state_facts(md, repo_root=repo_root)
    partial_findings = [f for f in findings if f.category == ClaimCategory.PARTIAL_STATE]
    assert partial_findings
    assert any(f.finding_object.state_type.value == "SCHEMA" for f in partial_findings)


def test_doc_planned_absence_claim_flagged(tmp_path: Path) -> None:
    repo_root = _build_partial_state_repo(tmp_path)
    md = _wrap_current_state("There is no planned operations runbook.")
    findings = validate_current_state_facts(md, repo_root=repo_root)
    partial_findings = [f for f in findings if f.category == ClaimCategory.PARTIAL_STATE]
    assert partial_findings
    assert any(f.finding_object.state_type.value == "DOC" for f in partial_findings)


def test_entry_point_planned_absence_claim_flagged(tmp_path: Path) -> None:
    repo_root = _build_partial_state_repo(tmp_path)
    md = _wrap_current_state("No /healthz endpoint is planned.")
    findings = validate_current_state_facts(md, repo_root=repo_root)
    partial_findings = [f for f in findings if f.category == ClaimCategory.PARTIAL_STATE]
    assert partial_findings
    assert any(f.finding_object.state_type.value == "ENTRY_POINT" for f in partial_findings)


def test_release_workflow_present_claim_not_flagged() -> None:
    # `.github/workflows/release.yml` now exists in this repo, so a current-state
    # claim that it exists should not be flagged as CURRENT_PATH.
    md = _wrap_current_state("CI includes `.github/workflows/release.yml`.")
    findings = validate_current_state_facts(md)
    path_findings = [
        f for f in findings
        if f.category == ClaimCategory.CURRENT_PATH and "release.yml" in f.evidence
    ]
    assert not path_findings, "Did not expect CURRENT_PATH finding for existing release.yml"


# ---------------------------------------------------------------------------
# B5 realism tests
# ---------------------------------------------------------------------------


def _wrap_future_tasks(body: str) -> str:
    """Place ``body`` under ``## TASK OVERVIEW`` with a minimal current-state header."""
    return "\n".join([
        "## CONTEXT — READ THIS FIRST",
        "**id:** ALFRED_HANDOVER_6_DRAFT",
        "**date:** 2026-04-20",
        "**previous_handover:** ALFRED_HANDOVER_5",
        "",
        "## WHAT EXISTS TODAY",
        "FastAPI lives in `src/alfred/api.py`.",
        "",
        "## TASK OVERVIEW",
        body,
        "",
    ])


def test_workflow_at_ci_path_flagged() -> None:
    md = _wrap_future_tasks(
        "### Task 1 — Add release workflow\n"
        "Create `ci/release.yml` that runs on every tag push.\n"
        "Tests: verify CI passes on a test tag."
    )
    findings = validate_future_task_realism(md)
    placement = [f for f in findings if f.category == ClaimCategory.PLACEMENT]
    assert placement, "Expected PLACEMENT finding for `ci/release.yml`"
    assert "ci/release.yml" in placement[0].evidence


def test_workflow_at_correct_path_passes() -> None:
    md = _wrap_future_tasks(
        "### Task 1 — Add release workflow\n"
        "Create `.github/workflows/release.yml` that runs on every tag push.\n"
        "Tests: verify CI passes on a test tag."
    )
    findings = validate_future_task_realism(md)
    placement = [f for f in findings if f.category == ClaimCategory.PLACEMENT]
    assert not placement, "Correct .github/workflows/ path must not produce a PLACEMENT finding"


def test_schema_as_single_file_flagged() -> None:
    md = _wrap_future_tasks(
        "### Task 2 — Add health schema\n"
        "Create `src/alfred/schemas.py` with a HealthCheck model.\n"
        "Tests: import the model in a unit test."
    )
    findings = validate_future_task_realism(md)
    placement = [f for f in findings if f.category == ClaimCategory.PLACEMENT]
    assert placement, "Expected PLACEMENT finding for `src/alfred/schemas.py`"
    assert "schemas.py" in placement[0].evidence


def test_schema_as_package_passes() -> None:
    md = _wrap_future_tasks(
        "### Task 2 — Add health schema\n"
        "Create `src/alfred/schemas/health.py` with a HealthCheck model.\n"
        "Tests: import the model in a unit test."
    )
    findings = validate_future_task_realism(md)
    placement = [f for f in findings if f.category == ClaimCategory.PLACEMENT]
    assert not placement, "Package-style schema path must not produce a PLACEMENT finding"


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_unconfigured_type_checker_in_future_task_flagged(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_future_tasks(
        "### Task 3 — Add type checking\n"
        f"Integrate {unexpected_tool} into the CI pipeline.\n"
        f"Tests: {unexpected_tool} passes on the src/ tree."
    )
    findings = validate_future_task_realism(md, repo_root=repo_root)
    hard_rule = [f for f in findings if f.category == ClaimCategory.HARD_RULE]
    assert hard_rule, "Expected HARD_RULE finding for an unexpected type checker in future task"
    assert f"`{unexpected_tool}`" in hard_rule[0].evidence


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_negated_unconfigured_type_checker_in_future_task_passes(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_future_tasks(
        "### Task 3 — Keep the type-checking policy consistent\n"
        f"Keep {configured_tool} as the only type checker; do not add {unexpected_tool} anywhere.\n"
        f"Tests: {configured_tool} exits 0 in CI."
    )
    findings = validate_future_task_realism(md, repo_root=repo_root)
    hard_rule = [f for f in findings if f.category == ClaimCategory.HARD_RULE]
    assert not hard_rule, "Prohibiting an unconfigured type checker must not produce a HARD_RULE finding"


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_type_checker_audit_cleanup_in_future_task_passes(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_future_tasks(
        "### Task 3 — Clean stale tooling references\n"
        f"Audit README content and remove stale references to {unexpected_tool} or `[tool.{unexpected_tool}]`.\n"
        f"Tests: `rg -n \"{unexpected_tool}\" README.md docs/ pyproject.toml` only reports approved prohibitions."
    )
    findings = validate_future_task_realism(md, repo_root=repo_root)
    hard_rule = [f for f in findings if f.category == ClaimCategory.HARD_RULE]
    assert not hard_rule, "Audit and removal work around an unconfigured type checker must be allowed"


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_bare_unconfigured_type_checker_mention_in_out_of_scope_bullet_passes(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_future_tasks(
        "### Task 3 — Define scope\n"
        "Out of scope:\n"
        f"- `{unexpected_tool}` or any type-checker other than `{configured_tool}`.\n"
        "Tests: scope section is reviewed."
    )
    findings = validate_future_task_realism(md, repo_root=repo_root)
    hard_rule = [f for f in findings if f.category == ClaimCategory.HARD_RULE]
    assert not hard_rule, "Bare out-of-scope type-checker mention must not trigger HARD_RULE"


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_unconfigured_type_checker_command_in_future_task_flagged(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_future_tasks(
        "### Task 3 — Add type checking\n"
        "Verification commands:\n"
        "```bash\n"
        f"{unexpected_tool} src/\n"
        "```\n"
    )
    findings = validate_future_task_realism(md, repo_root=repo_root)
    hard_rule = [f for f in findings if f.category == ClaimCategory.HARD_RULE]
    assert hard_rule, "Explicit type-checker command should count as introducing an absent tool"


@pytest.mark.parametrize(("configured_tool", "unexpected_tool"), _TYPE_CHECKER_CASES)
def test_configured_type_checker_in_future_task_passes(
    tmp_path: Path,
    configured_tool: str,
    unexpected_tool: str,
) -> None:
    repo_root = _build_type_checker_repo(tmp_path, configured_tool)
    md = _wrap_future_tasks(
        "### Task 3 — Add type checking\n"
        f"Ensure {configured_tool} passes on the src/ tree with strict mode.\n"
        f"Tests: {configured_tool} exits 0 in CI."
    )
    findings = validate_future_task_realism(md, repo_root=repo_root)
    hard_rule = [f for f in findings if f.category == ClaimCategory.HARD_RULE]
    assert not hard_rule, "Configured type-checker reference must not produce a HARD_RULE finding"


def test_docker_in_future_task_flagged() -> None:
    md = _wrap_future_tasks(
        "### Task 4 — Containerise\n"
        "Add a Dockerfile for the FastAPI service.\n"
        "Tests: docker build succeeds."
    )
    findings = validate_future_task_realism(md)
    hard_rule = [f for f in findings if f.category == ClaimCategory.HARD_RULE]
    assert hard_rule, "Expected HARD_RULE finding for Docker in future task"


def test_docker_in_future_task_allowed_for_phase7_handover() -> None:
    md = (
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        + _wrap_future_tasks(
            "### Task 4 — Containerise\n"
            "Add a Dockerfile for the FastAPI service.\n"
            "Tests: docker build succeeds."
        )
    )
    findings = validate_future_task_realism(md)
    hard_rule = [f for f in findings if f.category == ClaimCategory.HARD_RULE]
    assert not hard_rule, "Docker should be allowed in a Phase 7 handover"


def test_task_without_file_ref_gets_granularity_warning() -> None:
    md = _wrap_future_tasks(
        "### Task 5 — Do some work\n"
        "Refactor the internals to improve performance."
    )
    findings = validate_future_task_realism(md)
    granularity = [f for f in findings if f.category == ClaimCategory.TASK_GRANULARITY]
    assert granularity, "Expected TASK_GRANULARITY warning for task with no file path"
    assert granularity[0].severity == "warning"


def test_task_with_file_ref_and_test_mention_passes() -> None:
    md = _wrap_future_tasks(
        "### Task 5 — Add retry logic\n"
        "Extend `src/alfred/tools/llm.py` with exponential backoff.\n"
        "Tests: `pytest tests/test_tools/test_llm.py -q` passes."
    )
    findings = validate_future_task_realism(md)
    granularity = [f for f in findings if f.category == ClaimCategory.TASK_GRANULARITY]
    assert not granularity, "Task with file ref and test mention must not get TASK_GRANULARITY warning"


def test_realism_checks_do_not_fire_on_current_state_sections() -> None:
    # Current-state sections must be invisible to the realism validator.
    md = _wrap_future_tasks("")
    # Inject a schema single-file reference into WHAT EXISTS TODAY (already in _wrap_future_tasks)
    # but not in TASK OVERVIEW — so realism should not flag it.
    md_with_current_state_schema = md.replace(
        "FastAPI lives in `src/alfred/api.py`.",
        "FastAPI lives in `src/alfred/api.py`. Schema: `src/alfred/schemas.py`.",
    )
    findings = validate_future_task_realism(md_with_current_state_schema)
    placement = [f for f in findings if f.category == ClaimCategory.PLACEMENT]
    assert not placement, "Realism validator must not inspect current-state sections"
