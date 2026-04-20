#!/usr/bin/env python3
"""
Alfred canonical promotion validator.

Gates promotion of drafts into canonical ``docs/ALFRED_HANDOVER_*.md``
files. A draft that is missing required house-style sections cannot
silently become protocol: this script exits non-zero and lists the
specific structural failures.

Scope: Alfred canonical handovers only. Legacy BOB documents and other
permissive corpora are out of scope; the base ``HandoverDocument``
parser in ``src/alfred/schemas/handover.py`` must remain tolerant of
those.

Usage::

    python scripts/validate_alfred_handover.py PATH

Exit codes: 0 = valid, 1 = structural failure, 2 = usage/IO error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Required level-2 headings. Matching is case-insensitive, whitespace-
# collapsed, and dash-normalised; a heading may carry an additional
# suffix after the required text (e.g. "## POST-MORTEM — summary").
REQUIRED_H2: tuple[str, ...] = (
    "CONTEXT — READ THIS FIRST",
    "WHAT EXISTS TODAY",
    "HARD RULES",
    "TASK OVERVIEW",
    "WHAT NOT TO DO",
    "POST-MORTEM",
)

# Required level-3 headings mapped to the level-2 parent they must live
# under. An occurrence elsewhere in the document does not satisfy the
# contract.
REQUIRED_H3_UNDER: dict[str, str] = {
    "Git History": "WHAT EXISTS TODAY",
}


_DASH_RE = re.compile(r"[\u2010-\u2015\-]+")
_WS_RE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    """Lower-case, collapse whitespace, unify dash variants to em-dash."""
    text = text.strip().lower()
    text = _DASH_RE.sub("\u2014", text)
    text = _WS_RE.sub(" ", text)
    return text


def _heading_matches(actual: str, required: str) -> bool:
    """True iff ``actual`` equals ``required`` or extends it at a word boundary."""
    a = _normalise(actual)
    r = _normalise(required)
    if a == r:
        return True
    if not a.startswith(r):
        return False
    # Require a separator after the required prefix so "Git History" does
    # not match "Git Historyology".
    return a[len(r)] in (" ", "\u2014", ":")


def parse_headings(markdown: str) -> list[tuple[int, str, int]]:
    """Return ``[(level, text, line_number), ...]`` for ATX headings.

    Fenced code blocks are skipped so inline commit tables or example
    handovers do not trigger false matches.
    """
    headings: list[tuple[int, str, int]] = []
    in_fence = False
    for line_no, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).rstrip("#").strip()
            headings.append((level, text, line_no))
    return headings


def validate(markdown: str) -> list[str]:
    """Return a list of human-readable errors. Empty list means the
    document satisfies the Alfred canonical promotion contract.
    """
    errors: list[str] = []
    headings = parse_headings(markdown)

    h2_texts = [text for level, text, _ in headings if level == 2]
    for required in REQUIRED_H2:
        if not any(_heading_matches(h, required) for h in h2_texts):
            errors.append(f"Missing required H2: ## {required}")

    # Build (h3_text, parent_h2_text) pairs so placement is checkable.
    h3_pairs: list[tuple[str, str | None]] = []
    current_h2: str | None = None
    for level, text, _ in headings:
        if level == 2:
            current_h2 = text
        elif level == 3:
            h3_pairs.append((text, current_h2))

    for h3_required, parent_required in REQUIRED_H3_UNDER.items():
        matches = [(h3, parent) for h3, parent in h3_pairs if _heading_matches(h3, h3_required)]
        if not matches:
            errors.append(
                f"Missing required H3: ### {h3_required} "
                f"(must appear under ## {parent_required})"
            )
            continue
        under_correct = any(
            parent is not None and _heading_matches(parent, parent_required)
            for _, parent in matches
        )
        if not under_correct:
            found_parents = [parent or "(document root)" for _, parent in matches]
            errors.append(
                f"H3 '### {h3_required}' present but not under "
                f"'## {parent_required}' (found under: {', '.join(found_parents)})"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a markdown file against the Alfred canonical promotion contract.",
    )
    parser.add_argument("path", type=Path, help="Path to the handover markdown file")
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"error: not a file: {args.path}", file=sys.stderr)
        return 2

    try:
        markdown = args.path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: could not read {args.path}: {exc}", file=sys.stderr)
        return 2

    errors = validate(markdown)
    if errors:
        print(f"FAIL {args.path}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK   {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
