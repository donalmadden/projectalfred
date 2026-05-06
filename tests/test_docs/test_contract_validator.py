"""Tests for deterministic doc-class contract validation."""
from __future__ import annotations

from pathlib import Path

from alfred.docs.contract_validator import split_markdown_by_contract, validate_doc_against_contract
from alfred.docs.contracts import get_doc_class_contract

ROOT = Path(__file__).resolve().parents[2]


def _error_messages(markdown: str) -> list[str]:
    contract = get_doc_class_contract("canonical_handover", repo_root=ROOT)
    findings = validate_doc_against_contract(markdown, contract)
    return [finding.format() for finding in findings if finding.severity == "error"]


def test_validate_doc_against_contract_accepts_canonical_handover_15() -> None:
    contract = get_doc_class_contract("canonical_handover", repo_root=ROOT)
    markdown = (ROOT / "docs" / "canonical" / "ALFRED_HANDOVER_15.md").read_text(
        encoding="utf-8"
    )

    findings = validate_doc_against_contract(markdown, contract)

    assert [finding for finding in findings if finding.severity == "error"] == []


def test_validate_doc_against_contract_reports_missing_hard_rules() -> None:
    markdown = (
        "# Demo\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "Context.\n\n"
        "## WHAT EXISTS TODAY\n"
        "Current state.\n\n"
        "## WHAT THIS PHASE PRODUCES\n"
        "- Deliverable.\n\n"
        "## TASK OVERVIEW\n"
        "| # | Task | Deliverable |\n"
        "|---|---|---|\n"
        "| 1 | Keep | thing |\n\n"
        "## WHAT NOT TO DO\n"
        "- Skip the rules.\n"
    )

    errors = _error_messages(markdown)

    assert errors == [
        "Missing required level-2 heading for section `hard_rules`. Accepted headings: "
        "`HARD RULES`."
    ]


def test_validate_doc_against_contract_reports_renamed_heading() -> None:
    markdown = (
        "# Demo\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "Context.\n\n"
        "## WHAT EXISTS TODAY\n"
        "Current state.\n\n"
        "## HARD-RULES\n"
        "- typo.\n\n"
        "## WHAT THIS PHASE PRODUCES\n"
        "- Deliverable.\n\n"
        "## TASK OVERVIEW\n"
        "| # | Task | Deliverable |\n"
        "|---|---|---|\n"
        "| 1 | Keep | thing |\n\n"
        "## WHAT NOT TO DO\n"
        "- Skip the rules.\n"
    )

    errors = _error_messages(markdown)

    assert errors == [
        "Missing required level-2 heading for section `hard_rules`. Accepted headings: "
        "`HARD RULES`."
    ]


def test_validate_doc_against_contract_accepts_canonical_corpus_through_15() -> None:
    contract = get_doc_class_contract("canonical_handover", repo_root=ROOT)

    for index in range(1, 16):
        markdown = (ROOT / "docs" / "canonical" / f"ALFRED_HANDOVER_{index}.md").read_text(
            encoding="utf-8"
        )
        findings = validate_doc_against_contract(markdown, contract)
        errors = [finding.format() for finding in findings if finding.severity == "error"]
        assert errors == [], f"ALFRED_HANDOVER_{index} failed contract validation: {errors}"


def test_split_markdown_by_contract_uses_semantic_section_keys() -> None:
    contract = get_doc_class_contract("canonical_handover", repo_root=ROOT)
    markdown = (ROOT / "docs" / "canonical" / "ALFRED_HANDOVER_12.md").read_text(
        encoding="utf-8"
    )

    sections = split_markdown_by_contract(markdown, contract)

    assert sections["context"].startswith("**schema_version:** 1.0")
    assert "operator demo script" in sections["deliverables"]
    assert "task_overview" in sections
