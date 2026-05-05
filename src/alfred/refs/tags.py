"""Deterministic reference-tag parser.

Canonical syntax (from ``CONTEXT.md``):

* ``[future-doc: <path>]`` — path lives in an external/future workspace.
* ``[future-path: <path>]`` — same, for non-doc paths.

Only these two forms are recognised. The parser is strict and
case-sensitive: anything that begins with ``[future-doc`` or
``[future-path`` but does not match the canonical shape is reported as a
:class:`ReferenceTagParseError` with line/column metadata so a validator
can print a stable, testable message.

This module is the single source of reference-tag semantics for Alfred
validators; ad-hoc regexes elsewhere should be migrated onto it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Literal

ReferenceTagKind = Literal["future-doc", "future-path"]

# Canonical, strict form. Must match `[future-doc: <path>]` or
# `[future-path: <path>]` exactly:
#   - opening `[`
#   - exact prefix `future-doc` or `future-path` (case-sensitive)
#   - colon directly after the prefix
#   - optional ASCII spaces, then a non-empty path that may not contain
#     `]` or a newline
#   - closing `]`
# Trailing whitespace inside the brackets is trimmed from the captured path.
_CANONICAL_RE = re.compile(
    r"\[(?P<kind>future-doc|future-path):[ \t]*(?P<path>[^\]\n]*?)[ \t]*\]"
)

# Candidate detection. Any `[` followed by the literal `future-doc` or
# `future-path` is treated as an attempted reference tag and must satisfy
# the canonical form. This catches malformed near-misses like missing
# colon, missing closing bracket, empty path, or stray whitespace inside
# the prefix.
_CANDIDATE_RE = re.compile(r"\[(?:future-doc|future-path)")


@dataclass(frozen=True)
class ReferenceTag:
    """A single canonical reference tag found in markdown text."""

    kind: ReferenceTagKind
    path: str
    start: int  # char offset of opening `[`, inclusive
    end: int  # char offset just past closing `]`, exclusive
    line: int  # 1-based line of the opening `[`
    col: int  # 1-based column of the opening `[`


class ReferenceTagParseError(Exception):
    """Raised for a malformed `[future-doc:...]` / `[future-path:...]`."""

    def __init__(
        self,
        message: str,
        *,
        line: int,
        col: int,
        snippet: str,
    ) -> None:
        super().__init__(
            f"{message} at line {line}, col {col}: {snippet!r}"
        )
        self.message = message
        self.line = line
        self.col = col
        self.snippet = snippet


def _line_col(text: str, offset: int) -> tuple[int, int]:
    """Return 1-based ``(line, col)`` for ``offset`` in ``text``."""
    prefix = text[:offset]
    line = prefix.count("\n") + 1
    last_nl = prefix.rfind("\n")
    col = offset - last_nl  # if last_nl == -1 → offset + 1
    return line, col


def _snippet(text: str, start: int, max_len: int = 60) -> str:
    """Return a short, single-line snippet starting at ``start``."""
    end = min(len(text), start + max_len)
    nl = text.find("\n", start, end)
    if nl != -1:
        end = nl
    return text[start:end]


def extract_reference_tags(text: str) -> list[ReferenceTag]:
    """Return every canonical reference tag in ``text``.

    Raises :class:`ReferenceTagParseError` on the first malformed
    candidate (something that begins with ``[future-doc`` or
    ``[future-path`` but does not match the canonical form).
    """
    return list(iter_reference_tags(text))


def iter_reference_tags(text: str) -> Iterator[ReferenceTag]:
    """Yield canonical reference tags in document order.

    Raises :class:`ReferenceTagParseError` on the first malformed
    candidate. Iteration up to that point still completes.
    """
    pos = 0
    n = len(text)
    while pos < n:
        cand = _CANDIDATE_RE.search(text, pos)
        if cand is None:
            return
        cand_start = cand.start()
        m = _CANONICAL_RE.match(text, cand_start)
        if m is None:
            line, col = _line_col(text, cand_start)
            raise ReferenceTagParseError(
                "malformed reference tag (expected `[future-doc: <path>]`"
                " or `[future-path: <path>]`)",
                line=line,
                col=col,
                snippet=_snippet(text, cand_start),
            )
        path = m.group("path")
        if not path:
            line, col = _line_col(text, cand_start)
            raise ReferenceTagParseError(
                "reference tag has empty path",
                line=line,
                col=col,
                snippet=_snippet(text, cand_start),
            )
        line, col = _line_col(text, cand_start)
        kind: ReferenceTagKind = m.group("kind")  # type: ignore[assignment]
        yield ReferenceTag(
            kind=kind,
            path=path,
            start=cand_start,
            end=m.end(),
            line=line,
            col=col,
        )
        pos = m.end()
