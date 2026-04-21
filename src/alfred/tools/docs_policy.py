"""Helpers for the docs lifecycle policy defined in ``docs/DOCS_POLICY.md``.

The human-readable policy lives in markdown, while the machine-readable
contract lives in ``docs/DOCS_MANIFEST.yaml``. This module reads the manifest
and exposes small helpers for retrieval and reference-doc validation flows.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_RELATIVE_PATH = Path("docs") / "DOCS_MANIFEST.yaml"


@dataclass(frozen=True)
class DocsPolicyEntry:
    current_path: str
    proposed_path: str
    indexed: bool
    citable: bool
    authoritative: bool
    lifecycle_status: str
    kind: str = ""
    notes: str = ""

    def candidate_paths(self) -> tuple[str, ...]:
        paths = [self.current_path]
        if self.proposed_path and self.proposed_path != self.current_path:
            paths.append(self.proposed_path)
        return tuple(paths)


def _normalise_relative_path(path: str | Path, repo_root: Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.relative_to(repo_root).as_posix()
        except ValueError:
            return candidate.as_posix()
    return candidate.as_posix()


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _manifest_path(repo_root: Path) -> Path:
    return repo_root / _MANIFEST_RELATIVE_PATH


def has_docs_manifest(
    repo_root: str | Path | None = None,
    *,
    start_path: str | Path | None = None,
) -> bool:
    """Return whether a docs manifest exists for the resolved repo root."""
    root = Path(repo_root) if repo_root is not None else infer_repo_root(start_path)
    return root is not None and _manifest_path(root).is_file()


def infer_repo_root(start_path: str | Path | None = None) -> Optional[Path]:
    """Find the nearest repo root containing ``docs/DOCS_MANIFEST.yaml``."""
    if start_path is None:
        candidates = (_REPO_ROOT, *_REPO_ROOT.parents)
    else:
        start = Path(start_path)
        anchor = start if start.is_dir() else start.parent
        candidates = (anchor, *anchor.parents)
    for candidate in candidates:
        if _manifest_path(candidate).is_file():
            return candidate
    return None


def load_docs_policy_entries(
    repo_root: str | Path | None = None,
    *,
    start_path: str | Path | None = None,
) -> list[DocsPolicyEntry]:
    """Return manifest entries, or ``[]`` when no docs manifest is available."""
    root = Path(repo_root) if repo_root is not None else infer_repo_root(start_path)
    if root is None:
        return []

    manifest_path = _manifest_path(root)
    if not manifest_path.is_file():
        return []

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    raw_docs = data.get("documents") or []
    entries: list[DocsPolicyEntry] = []
    for raw in raw_docs:
        if not isinstance(raw, dict):
            continue
        current_path = str(raw.get("current_path") or "").strip()
        if not current_path:
            continue
        entries.append(
            DocsPolicyEntry(
                current_path=current_path,
                proposed_path=str(raw.get("proposed_path") or current_path).strip(),
                indexed=bool(raw.get("indexed", False)),
                citable=bool(raw.get("citable", False)),
                authoritative=bool(raw.get("authoritative", False)),
                lifecycle_status=str(raw.get("lifecycle_status") or "").strip(),
                kind=str(raw.get("kind") or "").strip(),
                notes=str(raw.get("notes") or "").strip(),
            )
        )
    return entries


def resolve_policy_entry(
    doc_path: str | Path,
    repo_root: str | Path | None = None,
) -> Optional[DocsPolicyEntry]:
    """Return the manifest entry matching ``doc_path`` if one exists."""
    root = Path(repo_root) if repo_root is not None else infer_repo_root(doc_path)
    if root is None:
        return None

    relative = _normalise_relative_path(doc_path, root)
    for entry in load_docs_policy_entries(root):
        if relative in entry.candidate_paths():
            return entry
    return None


def iter_policy_paths(
    repo_root: str | Path | None = None,
    *,
    start_path: str | Path | None = None,
    indexed: Optional[bool] = None,
    citable: Optional[bool] = None,
    authoritative: Optional[bool] = None,
    markdown_only: bool = False,
) -> list[Path]:
    """Return existing doc paths filtered by docs policy flags.

    When the manifest is absent, callers should fall back to their legacy
    behavior; this helper returns ``[]`` in that case.
    """
    root = Path(repo_root) if repo_root is not None else infer_repo_root(start_path)
    if root is None:
        return []

    entries = load_docs_policy_entries(root)
    if not entries:
        return []

    scope: Optional[Path] = None
    if start_path is not None:
        scope = Path(start_path)
        if not scope.is_absolute():
            scope = root / scope

    selected: list[Path] = []
    seen: set[str] = set()
    for entry in entries:
        if indexed is not None and entry.indexed != indexed:
            continue
        if citable is not None and entry.citable != citable:
            continue
        if authoritative is not None and entry.authoritative != authoritative:
            continue

        resolved: Optional[Path] = None
        for relative in entry.candidate_paths():
            candidate = root / relative
            if candidate.exists():
                resolved = candidate
                break
        if resolved is None:
            continue
        if markdown_only and resolved.suffix.lower() != ".md":
            continue
        if scope is not None and not _path_is_within(resolved, scope):
            continue

        rel = resolved.relative_to(root).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        selected.append(resolved)
    return sorted(selected)


def read_citable_docs(repo_root: str | Path | None = None) -> list[str]:
    """Return citable markdown docs relative to the repo root."""
    root = Path(repo_root) if repo_root is not None else infer_repo_root()
    if root is None:
        return []

    if has_docs_manifest(root):
        policy_paths = iter_policy_paths(root, citable=True, markdown_only=True)
        return [path.relative_to(root).as_posix() for path in policy_paths]

    docs_root = root / "docs"
    if not docs_root.is_dir():
        return []
    return sorted(path.relative_to(root).as_posix() for path in docs_root.rglob("*.md"))


def read_docs_inventory(repo_root: str | Path | None = None) -> list[str]:
    """Return all manifest-managed markdown docs relative to the repo root."""
    root = Path(repo_root) if repo_root is not None else infer_repo_root()
    if root is None:
        return []

    if has_docs_manifest(root):
        return [
            path.relative_to(root).as_posix()
            for path in iter_policy_paths(root, markdown_only=True)
        ]

    docs_root = root / "docs"
    if not docs_root.is_dir():
        return []
    return sorted(path.relative_to(root).as_posix() for path in docs_root.rglob("*.md"))


def is_citable_doc(doc_path: str | Path, repo_root: str | Path | None = None) -> bool:
    """Return whether ``doc_path`` is citable under the docs policy."""
    entry = resolve_policy_entry(doc_path, repo_root)
    if entry is not None:
        return entry.citable
    root = Path(repo_root) if repo_root is not None else infer_repo_root(doc_path)
    if root is None:
        return False
    relative = _normalise_relative_path(doc_path, root)
    return relative in read_citable_docs(root)
