"""Tests for reference-doc validation helpers."""
from __future__ import annotations

from pathlib import Path

from alfred.tools.reference_doc_validator import (
    extract_reference_doc_metadata,
    validate_reference_doc_cross_links,
    validate_reference_doc_freshness,
    validate_reference_doc_structure,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_valid_reference_doc_passes(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "ALFRED_HANDOVER_6.md"
    _write(
        doc,
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_6\n"
        "**date:** 2026-04-20\n"
        "**author:** Planner\n\n"
        "## WHAT EXISTS TODAY\nReal state.\n\n"
        "## TASK OVERVIEW\nPlan.\n",
    )

    assert validate_reference_doc_structure("docs/ALFRED_HANDOVER_6.md", tmp_path) == []


def test_missing_reference_doc_fails(tmp_path: Path) -> None:
    issues = validate_reference_doc_structure("docs/ALFRED_HANDOVER_9.md", tmp_path)
    assert issues
    assert issues[0].issue_type == "not_found"


def test_reference_doc_without_expected_metadata_fails(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "ALFRED_HANDOVER_6.md"
    _write(
        doc,
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## WHAT EXISTS TODAY\nReal state.\n",
    )

    issues = validate_reference_doc_structure("docs/ALFRED_HANDOVER_6.md", tmp_path)
    issue_types = {issue.issue_type for issue in issues}
    assert "missing_metadata" in issue_types


def test_stale_reference_doc_warns_not_errors(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "ALFRED_HANDOVER_4.md"
    _write(
        doc,
        "# Alfred's Handover Document #4 — Phase 5\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_4\n"
        "**date:** 2025-01-01\n"
        "**author:** Planner\n\n"
        "## WHAT EXISTS TODAY\nReal state.\n\n"
        "## TASK OVERVIEW\nPlan.\n",
    )

    issues = validate_reference_doc_freshness(
        "docs/ALFRED_HANDOVER_4.md",
        reference_date="2026-04-21",
        repo_root=tmp_path,
    )
    assert issues
    assert issues[0].severity == "warning"
    assert issues[0].issue_type == "stale_reference"


def test_cross_link_to_nonexistent_doc_fails(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "ALFRED_HANDOVER_6.md"
    _write(
        doc,
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_6\n"
        "**date:** 2026-04-20\n"
        "**author:** Planner\n\n"
        "See `docs/ALFRED_HANDOVER_5.md`.\n",
    )

    issues = validate_reference_doc_cross_links(
        "docs/ALFRED_HANDOVER_6.md",
        {"docs/ALFRED_HANDOVER_6.md"},
        tmp_path,
    )
    assert issues
    assert issues[0].issue_type == "cross_link_missing"


def test_optional_deferred_cross_link_to_future_doc_passes(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "protocol" / "architecture.md"
    _write(
        doc,
        "# Architecture\n\n"
        "- Optional `docs/CURRENT_STATE.md` is deferred and may add a "
        "\"what exists\" anchor later.\n",
    )

    issues = validate_reference_doc_cross_links(
        "docs/protocol/architecture.md",
        {"docs/protocol/architecture.md"},
        tmp_path,
    )

    assert issues == []


def test_extract_reference_doc_metadata_reads_expected_fields(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "ALFRED_HANDOVER_6.md"
    _write(
        doc,
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_6\n"
        "**date:** 2026-04-20\n"
        "**author:** Planner\n",
    )
    metadata = extract_reference_doc_metadata("docs/ALFRED_HANDOVER_6.md", tmp_path)
    assert metadata.exists is True
    assert metadata.expected_handover_id == "ALFRED_HANDOVER_6"
    assert metadata.declared_id == "ALFRED_HANDOVER_6"
    assert metadata.date == "2026-04-20"


def test_reference_doc_must_be_citable_under_manifest(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs" / "DOCS_MANIFEST.yaml",
        "manifest_version: 1\n"
        "documents:\n"
        "  - current_path: docs/ALFRED_HANDOVER_6_old.md\n"
        "    proposed_path: docs/archive/ALFRED_HANDOVER_6_old.md\n"
        "    indexed: false\n"
        "    citable: false\n"
        "    authoritative: false\n"
        "    lifecycle_status: archive\n",
    )
    _write(
        tmp_path / "docs" / "ALFRED_HANDOVER_6_old.md",
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_6_old\n"
        "**date:** 2026-04-20\n"
        "**author:** Planner\n\n"
        "## WHAT EXISTS TODAY\nReal state.\n\n"
        "## TASK OVERVIEW\nPlan.\n",
    )

    issues = validate_reference_doc_structure("docs/ALFRED_HANDOVER_6_old.md", tmp_path)

    assert issues
    assert issues[0].issue_type == "not_citable"


def test_cross_link_old_doc_path_is_normalised_via_manifest(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs" / "DOCS_MANIFEST.yaml",
        "manifest_version: 1\n"
        "documents:\n"
        "  - current_path: docs/canonical/ALFRED_HANDOVER_5.md\n"
        "    indexed: true\n"
        "    citable: true\n"
        "    authoritative: true\n"
        "    lifecycle_status: canonical\n"
        "  - current_path: docs/protocol/architecture.md\n"
        "    indexed: true\n"
        "    citable: true\n"
        "    authoritative: true\n"
        "    lifecycle_status: protocol\n",
    )
    _write(
        tmp_path / "docs" / "protocol" / "architecture.md",
        "# Architecture\n\nSee `docs/ALFRED_HANDOVER_5.md`.\n",
    )
    _write(
        tmp_path / "docs" / "canonical" / "ALFRED_HANDOVER_5.md",
        "# Alfred's Handover Document #5 — Phase 6\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_5\n"
        "**date:** 2026-04-20\n"
        "**author:** Planner\n\n"
        "## WHAT EXISTS TODAY\nReal state.\n\n"
        "## TASK OVERVIEW\nPlan.\n",
    )

    issues = validate_reference_doc_cross_links(
        "docs/protocol/architecture.md",
        {
            "docs/protocol/architecture.md",
            "docs/canonical/ALFRED_HANDOVER_5.md",
        },
        tmp_path,
    )

    assert issues == []
