#!/usr/bin/env python3
"""Validate that the docs manifest matches the managed docs corpus.

This script compares ``documents[].current_path`` entries in
``docs/DOCS_MANIFEST.yaml`` against the on-disk ``docs/`` tree.

It reports two classes of drift:
  1. Paths declared in the manifest but missing on disk.
  2. Markdown files on disk that are absent from the manifest.

Scratch content is excluded from the on-disk markdown scan because the docs
policy treats ``docs/scratch/`` as disposable local output rather than part of
the governed corpus.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check docs manifest coverage against the docs filesystem.",
    )
    parser.add_argument(
        "--docs-root",
        default="docs",
        help="Docs root to scan (default: docs)",
    )
    parser.add_argument(
        "--manifest",
        default="docs/DOCS_MANIFEST.yaml",
        help="Manifest to validate (default: docs/DOCS_MANIFEST.yaml)",
    )
    return parser.parse_args(argv)


def _normalise_relative(path: str | Path) -> str:
    return Path(path).as_posix().rstrip("/")


def _is_under_scope(path: str, docs_root_name: str) -> bool:
    return path == docs_root_name or path.startswith(f"{docs_root_name}/")


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def _is_scratch_markdown(path: Path) -> bool:
    parts = path.parts
    return len(parts) >= 2 and parts[0] == "docs" and parts[1] == "scratch"


def load_manifest_paths(manifest_path: Path, docs_root_name: str) -> set[str]:
    data: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    raw_documents = data.get("documents") or []
    if not isinstance(raw_documents, list):
        raise ValueError("Manifest 'documents' must be a list.")

    declared: set[str] = set()
    for raw_entry in raw_documents:
        if not isinstance(raw_entry, dict):
            continue
        current_path = str(raw_entry.get("current_path") or "").strip()
        if not current_path:
            continue
        normalised = _normalise_relative(current_path)
        if _is_under_scope(normalised, docs_root_name):
            declared.add(normalised)
    return declared


def collect_markdown_docs(docs_root: Path) -> set[str]:
    repo_root = docs_root.parent
    discovered: set[str] = set()
    for path in docs_root.rglob("*.md"):
        relative = path.relative_to(repo_root)
        if _is_hidden(relative):
            continue
        if _is_scratch_markdown(relative):
            continue
        discovered.add(relative.as_posix())
    return discovered


def find_manifest_drift(
    docs_root: Path,
    manifest_path: Path,
) -> tuple[list[str], list[str]]:
    docs_root_name = docs_root.name
    declared_paths = load_manifest_paths(manifest_path, docs_root_name)

    missing_from_disk = sorted(
        declared
        for declared in declared_paths
        if not (docs_root.parent / declared).exists()
    )
    unmanaged_markdown = sorted(collect_markdown_docs(docs_root) - declared_paths)
    return missing_from_disk, unmanaged_markdown


def format_drift_report(
    *,
    missing_from_disk: list[str],
    unmanaged_markdown: list[str],
) -> str:
    lines = ["Manifest drift detected:"]
    if missing_from_disk:
        lines.append("")
        lines.append("Declared in manifest but missing on disk:")
        lines.extend(f"  - {path}" for path in missing_from_disk)
    if unmanaged_markdown:
        lines.append("")
        lines.append("Markdown files on disk but absent from manifest:")
        lines.extend(f"  - {path}" for path in unmanaged_markdown)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    docs_root = Path(args.docs_root)
    manifest_path = Path(args.manifest)

    if not docs_root.is_dir():
        print(f"ERROR: docs root not found: {docs_root}", file=sys.stderr)
        return 2
    if not manifest_path.is_file():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    try:
        missing_from_disk, unmanaged_markdown = find_manifest_drift(
            docs_root=docs_root,
            manifest_path=manifest_path,
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: unable to validate manifest: {exc}", file=sys.stderr)
        return 2

    if missing_from_disk or unmanaged_markdown:
        print(
            format_drift_report(
                missing_from_disk=missing_from_disk,
                unmanaged_markdown=unmanaged_markdown,
            )
        )
        return 1

    print("No drift detected between manifest and docs filesystem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
