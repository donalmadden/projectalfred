"""Tests for manifest-backed doc-class contracts."""
from __future__ import annotations

from pathlib import Path

import pytest

from alfred.docs.contracts import DocContractLoadError, get_doc_class_contract, load_doc_contracts

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_load_doc_contracts_reads_canonical_handover_contract() -> None:
    contracts = load_doc_contracts(repo_root=ROOT)

    assert list(contracts) == ["canonical_handover"]

    contract = contracts["canonical_handover"]
    assert contract.allow_unexpected_headings is True
    assert contract.ordered_keys == (
        "context",
        "current_state",
        "hard_rules",
        "deliverables",
        "task_overview",
        "non_goals",
        "retrospective",
    )
    assert contract.get_section("context").headings == ("CONTEXT — READ THIS FIRST",)
    assert contract.get_section("deliverables").headings == (
        "WHAT THIS PHASE PRODUCES",
        "WHAT THIS HANDOVER PRODUCES",
        "WHAT PHASE 2 PRODUCES",
    )


def test_get_doc_class_contract_missing_contract_mentions_manifest_path(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs" / "DOCS_MANIFEST.yaml",
        "manifest_version: 1\n"
        "doc_classes: {}\n"
        "documents: []\n",
    )

    with pytest.raises(DocContractLoadError) as exc:
        get_doc_class_contract("canonical_handover", repo_root=tmp_path)

    message = str(exc.value)
    assert "docs/DOCS_MANIFEST.yaml" in message
    assert "doc_classes.canonical_handover" in message


def test_load_doc_contracts_reports_precise_invalid_key_path(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs" / "DOCS_MANIFEST.yaml",
        "manifest_version: 1\n"
        "doc_classes:\n"
        "  canonical_handover:\n"
        "    description: Demo\n"
        "    allow_unexpected_headings: true\n"
        "    sections:\n"
        "      - key: context\n"
        "        headings: []\n"
        "        required: true\n"
        "        semantic_class: continuity\n"
        "        rendering_treatment: extractable\n"
        "documents: []\n",
    )

    with pytest.raises(DocContractLoadError) as exc:
        load_doc_contracts(repo_root=tmp_path)

    assert "doc_classes.canonical_handover.sections[0].headings" in str(exc.value)
