"""Tests for docs lifecycle policy helpers."""
from __future__ import annotations

from pathlib import Path

from alfred.tools.docs_policy import (
    infer_repo_root,
    is_citable_doc,
    iter_policy_paths,
    read_citable_docs,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_manifest(repo_root: Path) -> None:
    _write(
        repo_root / "docs" / "DOCS_MANIFEST.yaml",
        "manifest_version: 1\n"
        "documents:\n"
        "  - current_path: docs/ALFRED_HANDOVER_5.md\n"
        "    proposed_path: docs/canonical/ALFRED_HANDOVER_5.md\n"
        "    indexed: true\n"
        "    citable: true\n"
        "    authoritative: true\n"
        "    lifecycle_status: canonical\n"
        "  - current_path: docs/architecture.md\n"
        "    proposed_path: docs/protocol/architecture.md\n"
        "    indexed: true\n"
        "    citable: true\n"
        "    authoritative: true\n"
        "    lifecycle_status: protocol\n"
        "  - current_path: docs/ALFRED_HANDOVER_6_old.md\n"
        "    proposed_path: docs/archive/ALFRED_HANDOVER_6_old.md\n"
        "    indexed: false\n"
        "    citable: false\n"
        "    authoritative: false\n"
        "    lifecycle_status: archive\n",
    )


def test_infer_repo_root_finds_manifest_from_docs_subtree(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    (tmp_path / "docs" / "canonical").mkdir(parents=True)

    repo_root = infer_repo_root(tmp_path / "docs" / "canonical")
    assert repo_root == tmp_path


def test_iter_policy_paths_prefers_existing_proposed_paths(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    _write(
        tmp_path / "docs" / "canonical" / "ALFRED_HANDOVER_5.md",
        "# Canonical\n\n## Context\nCurrent.\n",
    )
    _write(
        tmp_path / "docs" / "protocol" / "architecture.md",
        "# Architecture\n\n## Layout\nTruth.\n",
    )
    _write(
        tmp_path / "docs" / "archive" / "ALFRED_HANDOVER_6_old.md",
        "# Old\n\n## Archive\nOld.\n",
    )

    indexed = iter_policy_paths(
        repo_root=tmp_path,
        start_path=tmp_path / "docs",
        indexed=True,
        markdown_only=True,
    )

    assert [path.relative_to(tmp_path).as_posix() for path in indexed] == [
        "docs/canonical/ALFRED_HANDOVER_5.md",
        "docs/protocol/architecture.md",
    ]


def test_read_citable_docs_and_is_citable_doc_respect_manifest(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    _write(
        tmp_path / "docs" / "canonical" / "ALFRED_HANDOVER_5.md",
        "# Canonical\n\n## Context\nCurrent.\n",
    )
    _write(
        tmp_path / "docs" / "archive" / "ALFRED_HANDOVER_6_old.md",
        "# Old\n\n## Archive\nOld.\n",
    )

    assert read_citable_docs(tmp_path) == ["docs/canonical/ALFRED_HANDOVER_5.md"]
    assert is_citable_doc("docs/canonical/ALFRED_HANDOVER_5.md", tmp_path) is True
    assert is_citable_doc("docs/archive/ALFRED_HANDOVER_6_old.md", tmp_path) is False
