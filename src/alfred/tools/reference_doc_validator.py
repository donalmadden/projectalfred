"""Reference-document structure and cross-link validation helpers."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from alfred.tools.docs_policy import is_citable_doc, load_docs_policy_entries, resolve_policy_entry

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOC_LINK_RE = re.compile(r"`(?P<path>docs/[A-Za-z0-9_./\-]+\.md)`")
_SENTENCE_SEP_RE = re.compile(r"\n\n|(?<=\w)\. |```")
_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_ID_RE = re.compile(r"\*\*id:\*\*\s*(?P<value>[A-Za-z0-9_\-]+)")
_DATE_RE = re.compile(r"\*\*date:\*\*\s*(?P<value>[0-9]{4}-[0-9]{2}-[0-9]{2})")
_AUTHOR_RE = re.compile(r"\*\*author:\*\*\s*(?P<value>.+)")
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_HANDOVER_NAME_RE = re.compile(r"ALFRED_HANDOVER_(\d+)(?:_[A-Z0-9_]+)?\.md$")
_STALE_REFERENCE_DAYS = 90
_EXPLICIT_FUTURE_PATH_TAG_RE = re.compile(
    r"\[\s*future-(?:doc|path)(?:\s*:[^\]]+)?\]",
    re.IGNORECASE,
)
_DEFERRED_DOC_MARKERS = (
    "optional",
    "deferred",
    "not required",
    "must not be pre-created",
    "not be pre-created",
    "may add",
    "may create",
    "to be created",
)


class ReferenceDocMetadata(BaseModel):
    path: str
    title: str | None = None
    declared_id: str | None = None
    expected_handover_id: str | None = None
    date: str | None = None
    author: str | None = None
    exists: bool
    headings: list[str] = Field(default_factory=list)


class ReferenceDocIssue(BaseModel):
    issue_type: str
    severity: str
    message: str
    evidence: str


def _resolve_doc_path(doc_path: str | Path, repo_root: Optional[Path]) -> tuple[Path, str]:
    root = repo_root or _REPO_ROOT
    candidate = Path(doc_path)
    if candidate.is_absolute():
        relative = candidate.relative_to(root).as_posix() if candidate.exists() else candidate.name
        return candidate, relative
    return root / candidate, candidate.as_posix()


def _is_handover_doc(relative_path: str) -> bool:
    return _HANDOVER_NAME_RE.search(Path(relative_path).name) is not None


def _normalise_doc_link_path(doc_path: str, repo_root: Optional[Path]) -> str:
    root = repo_root or _REPO_ROOT
    entry = resolve_policy_entry(doc_path, root)
    if entry is not None:
        return entry.current_path

    basename = Path(doc_path).name
    matches = [
        candidate.current_path
        for candidate in load_docs_policy_entries(root)
        if Path(candidate.current_path).name == basename
    ]
    unique_matches = sorted(set(matches))
    if len(unique_matches) == 1:
        return unique_matches[0]
    return doc_path


def _find_sentence(text: str, pos: int) -> str:
    """Return the sentence containing ``pos`` for nearby intent checks."""
    sent_start = 0
    for match in _SENTENCE_SEP_RE.finditer(text):
        if match.end() <= pos:
            sent_start = match.end()
        else:
            break
    after = _SENTENCE_SEP_RE.search(text, pos)
    sent_end = after.start() if after else len(text)
    return text[sent_start:sent_end]


def _link_is_deferred_or_optional(text: str, match_start: int) -> bool:
    sentence = _find_sentence(text, match_start).lower()
    return any(marker in sentence for marker in _DEFERRED_DOC_MARKERS)


def path_has_future_tag(
    text: str,
    match_start: int,
    match_end: int,
) -> bool:
    """Return whether an inline future-path/doc tag is attached to the path."""
    before = text[max(0, match_start - 32):match_start]
    after = text[match_end:min(len(text), match_end + 160)]
    return bool(
        _EXPLICIT_FUTURE_PATH_TAG_RE.search(before)
        or _EXPLICIT_FUTURE_PATH_TAG_RE.search(after)
    )


def link_is_inventory_exempt(text: str, match_start: int, match_end: int) -> bool:
    """Return whether a docs/*.md path is intentionally outside current inventory."""
    return path_has_future_tag(text, match_start, match_end) or (
        _link_is_deferred_or_optional(text, match_start)
    )


def extract_reference_doc_metadata(
    doc_path: str | Path,
    repo_root: Optional[Path] = None,
) -> ReferenceDocMetadata:
    """Extract minimal metadata from a referenced document."""
    resolved, relative = _resolve_doc_path(doc_path, repo_root)
    if not resolved.is_file():
        return ReferenceDocMetadata(path=relative, exists=False)

    text = resolved.read_text(encoding="utf-8")
    title_match = _TITLE_RE.search(text)
    id_match = _ID_RE.search(text)
    date_match = _DATE_RE.search(text)
    author_match = _AUTHOR_RE.search(text)
    expected_handover_id = None
    handover_match = _HANDOVER_NAME_RE.search(resolved.name)
    if handover_match:
        expected_handover_id = resolved.stem.replace("_DRAFT", "")

    return ReferenceDocMetadata(
        path=relative,
        title=title_match.group(1) if title_match else None,
        declared_id=id_match.group("value") if id_match else None,
        expected_handover_id=expected_handover_id,
        date=date_match.group("value") if date_match else None,
        author=author_match.group("value").strip() if author_match else None,
        exists=True,
        headings=[match.group(1).strip() for match in _H2_RE.finditer(text)],
    )


def validate_reference_doc_structure(
    doc_path: str | Path,
    repo_root: Optional[Path] = None,
) -> list[ReferenceDocIssue]:
    """Validate that a referenced doc is structurally usable as ground truth."""
    metadata = extract_reference_doc_metadata(doc_path, repo_root)
    if not metadata.exists:
        return [
            ReferenceDocIssue(
                issue_type="not_found",
                severity="error",
                message="reference doc does not exist.",
                evidence=metadata.path,
            )
        ]

    if not is_citable_doc(metadata.path, repo_root or _REPO_ROOT):
        return [
            ReferenceDocIssue(
                issue_type="not_citable",
                severity="error",
                message="reference doc is not citable under the docs lifecycle policy.",
                evidence=metadata.path,
            )
        ]

    issues: list[ReferenceDocIssue] = []
    if not metadata.title:
        issues.append(
            ReferenceDocIssue(
                issue_type="missing_title",
                severity="error",
                message="reference doc is missing a top-level title.",
                evidence=metadata.path,
            )
        )

    if _is_handover_doc(metadata.path):
        required_metadata = {
            "id": metadata.declared_id,
            "date": metadata.date,
            "author": metadata.author,
        }
        for key, value in required_metadata.items():
            if value:
                continue
            issues.append(
                ReferenceDocIssue(
                    issue_type="missing_metadata",
                    severity="error",
                    message=f"handover doc is missing `{key}` metadata.",
                    evidence=metadata.path,
                )
            )
        if (
            metadata.expected_handover_id
            and metadata.declared_id
            and metadata.declared_id != metadata.expected_handover_id
        ):
            issues.append(
                ReferenceDocIssue(
                    issue_type="id_mismatch",
                    severity="error",
                    message=(
                        f"handover id `{metadata.declared_id}` does not match "
                        f"filename-derived id `{metadata.expected_handover_id}`."
                    ),
                    evidence=metadata.path,
                )
            )

        required_headings = {
            "CONTEXT — READ THIS FIRST",
            "WHAT EXISTS TODAY",
            "TASK OVERVIEW",
        }
        if not any(heading in required_headings for heading in metadata.headings):
            issues.append(
                ReferenceDocIssue(
                    issue_type="missing_sections",
                    severity="error",
                    message="handover doc is missing expected level-2 sections.",
                    evidence=metadata.path,
                )
            )

    return issues


def validate_reference_doc_cross_links(
    doc_path: str | Path,
    all_docs: Optional[set[str]] = None,
    repo_root: Optional[Path] = None,
) -> list[ReferenceDocIssue]:
    """Validate docs/*.md cross-links inside a referenced document."""
    resolved, relative = _resolve_doc_path(doc_path, repo_root)
    if not resolved.is_file():
        return []

    inventory = all_docs or set()
    text = resolved.read_text(encoding="utf-8")
    issues: list[ReferenceDocIssue] = []
    seen: set[str] = set()
    for match in _DOC_LINK_RE.finditer(text):
        link = match.group("path")
        if link in seen:
            continue
        seen.add(link)
        normalised_link = _normalise_doc_link_path(link, repo_root)
        if link in inventory or normalised_link in inventory:
            continue
        if link_is_inventory_exempt(text, match.start(), match.end()):
            continue
        issues.append(
            ReferenceDocIssue(
                issue_type="cross_link_missing",
                severity="error",
                message=f"cross-linked doc `{link}` is not present in the docs inventory.",
                evidence=relative,
            )
        )
    return issues


def validate_reference_doc_freshness(
    doc_path: str | Path,
    *,
    reference_date: str | None,
    repo_root: Optional[Path] = None,
) -> list[ReferenceDocIssue]:
    """Warn when a reference doc is materially older than the draft date.

    This uses a simple 90-day threshold. That cutoff is an inference chosen to
    catch genuinely stale operational references without punishing nearby
    adjacent handovers.
    """
    if not reference_date:
        return []

    metadata = extract_reference_doc_metadata(doc_path, repo_root)
    if not metadata.exists or not metadata.date:
        return []

    try:
        current = date.fromisoformat(reference_date)
        referenced = date.fromisoformat(metadata.date)
    except ValueError:
        return []

    age_days = (current - referenced).days
    if age_days <= _STALE_REFERENCE_DAYS:
        return []

    return [
        ReferenceDocIssue(
            issue_type="stale_reference",
            severity="warning",
            message=(
                f"reference doc is {age_days} days older than the draft date; "
                "confirm it is still the right grounding source."
            ),
            evidence=metadata.path,
        )
    ]
