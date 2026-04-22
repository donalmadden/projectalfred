"""Tests for ``scripts/check_manifest.py``."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_manifest as cm  # noqa: E402


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_manifest(repo_root: Path, entries: list[str]) -> Path:
    manifest = repo_root / "docs" / "DOCS_MANIFEST.yaml"
    documents = "\n".join(
        "\n".join(
            (
                "  - current_path: " + entry,
                "    kind: test_doc",
                "    lifecycle_status: canonical",
                "    indexed: true",
                "    citable: true",
                "    authoritative: true",
                "    notes: test entry",
            )
        )
        for entry in entries
    )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(f"manifest_version: 1\ndocuments:\n{documents}\n", encoding="utf-8")
    return manifest


def test_manifest_check_passes_when_manifest_and_docs_match(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path
    _write(repo_root / "docs" / "canonical" / "ALFRED_HANDOVER_1.md", "# ok\n")
    _write(repo_root / "docs" / "archive" / "history.md", "# archive\n")
    manifest = _write_manifest(
        repo_root,
        [
            "docs/canonical/ALFRED_HANDOVER_1.md",
            "docs/archive/history.md",
        ],
    )

    exit_code = cm.main(
        [
            "--docs-root",
            str(repo_root / "docs"),
            "--manifest",
            str(manifest),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No drift detected" in captured.out


def test_manifest_check_fails_when_manifest_declares_missing_path(
    tmp_path: Path,
    capsys,
) -> None:
    repo_root = tmp_path
    _write(repo_root / "docs" / "canonical" / "ALFRED_HANDOVER_1.md", "# ok\n")
    manifest = _write_manifest(
        repo_root,
        [
            "docs/canonical/ALFRED_HANDOVER_1.md",
            "docs/protocol/OPERATOR_RUNBOOK.md",
        ],
    )

    exit_code = cm.main(
        [
            "--docs-root",
            str(repo_root / "docs"),
            "--manifest",
            str(manifest),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Declared in manifest but missing on disk" in captured.out
    assert "docs/protocol/OPERATOR_RUNBOOK.md" in captured.out


def test_manifest_check_fails_when_markdown_file_is_missing_from_manifest(
    tmp_path: Path,
    capsys,
) -> None:
    repo_root = tmp_path
    _write(repo_root / "docs" / "canonical" / "ALFRED_HANDOVER_1.md", "# ok\n")
    _write(repo_root / "docs" / "protocol" / "architecture.md", "# extra\n")
    manifest = _write_manifest(repo_root, ["docs/canonical/ALFRED_HANDOVER_1.md"])

    exit_code = cm.main(
        [
            "--docs-root",
            str(repo_root / "docs"),
            "--manifest",
            str(manifest),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Markdown files on disk but absent from manifest" in captured.out
    assert "docs/protocol/architecture.md" in captured.out


def test_manifest_check_ignores_scratch_markdown_files(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path
    _write(repo_root / "docs" / "canonical" / "ALFRED_HANDOVER_1.md", "# ok\n")
    _write(repo_root / "docs" / "scratch" / "notes.md", "# local scratch\n")
    manifest = _write_manifest(repo_root, ["docs/canonical/ALFRED_HANDOVER_1.md"])

    exit_code = cm.main(
        [
            "--docs-root",
            str(repo_root / "docs"),
            "--manifest",
            str(manifest),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No drift detected" in captured.out
