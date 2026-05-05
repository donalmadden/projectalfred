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

# Markdown code spans whose content must be treated as verbatim, not as
# reference-tag candidates. This keeps the parser usable on docs that
# *describe* the tag grammar (e.g. `[future-doc:]` quoted as a label).
# Two narrow forms only: triple-backtick fenced blocks and inline
# single-backtick spans. This is targeted markdown awareness, not
# generalised markdown parsing.
_FENCED_BLOCK_RE = re.compile(r"```[^\n]*\n.*?\n```", re.DOTALL)
# Inline code span with arbitrary-length backtick delimiter (CommonMark):
# opening run of N backticks, content that may include shorter runs but
# not a run of exactly N, closing run of exactly N. The backreference
# enforces matching delimiter lengths so `` `[future-doc:]` `` (a
# double-backtick span containing a single-backtick token) is recognised
# as one inline span and skipped wholesale.
_INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1)[^\n])+?\1")


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


def _code_span_ranges(text: str) -> list[tuple[int, int]]:
    """Return sorted ``(start, end)`` ranges that must be treated as verbatim."""
    ranges: list[tuple[int, int]] = []
    for m in _FENCED_BLOCK_RE.finditer(text):
        ranges.append((m.start(), m.end()))
    for m in _INLINE_CODE_RE.finditer(text):
        # Skip inline matches that fall inside a fenced block.
        if any(s <= m.start() and m.end() <= e for s, e in ranges):
            continue
        ranges.append((m.start(), m.end()))
    ranges.sort()
    return ranges


def _in_any_range(pos: int, ranges: list[tuple[int, int]]) -> tuple[bool, int]:
    """Return ``(inside, range_end)``. ``range_end`` is meaningful when inside."""
    for start, end in ranges:
        if start <= pos < end:
            return True, end
        if start > pos:
            break
    return False, 0


def _walk(text: str) -> Iterator[ReferenceTag | ReferenceTagParseError]:
    """Yield ``ReferenceTag`` for canonical hits and ``ReferenceTagParseError``
    for malformed candidates, in document order. Never raises.
    """
    skip_ranges = _code_span_ranges(text)
    pos = 0
    n = len(text)
    while pos < n:
        cand = _CANDIDATE_RE.search(text, pos)
        if cand is None:
            return
        cand_start = cand.start()
        inside, range_end = _in_any_range(cand_start, skip_ranges)
        if inside:
            pos = range_end
            continue
        m = _CANONICAL_RE.match(text, cand_start)
        if m is None:
            line, col = _line_col(text, cand_start)
            yield ReferenceTagParseError(
                "malformed reference tag (expected `[future-doc: <path>]`"
                " or `[future-path: <path>]`)",
                line=line,
                col=col,
                snippet=_snippet(text, cand_start),
            )
            # Advance past the `[` so we keep scanning beyond the bad tag.
            pos = cand_start + 1
            continue
        path = m.group("path")
        if not path:
            line, col = _line_col(text, cand_start)
            yield ReferenceTagParseError(
                "reference tag has empty path",
                line=line,
                col=col,
                snippet=_snippet(text, cand_start),
            )
            pos = m.end()
            continue
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
    candidate. Tags yielded before the failing candidate remain valid.
    """
    for item in _walk(text):
        if isinstance(item, ReferenceTagParseError):
            raise item
        yield item


def scan_reference_tags(
    text: str,
) -> tuple[list[ReferenceTag], list[ReferenceTagParseError]]:
    """Return ``(tags, errors)`` collected from a single non-raising scan.

    Useful for validators that want to surface every malformed tag in a
    document instead of failing on the first one.
    """
    tags: list[ReferenceTag] = []
    errors: list[ReferenceTagParseError] = []
    for item in _walk(text):
        if isinstance(item, ReferenceTagParseError):
            errors.append(item)
        else:
            tags.append(item)
    return tags, errors
