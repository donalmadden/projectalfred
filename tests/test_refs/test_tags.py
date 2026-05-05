"""Tests for ``alfred.refs.tags``."""
from __future__ import annotations

import pytest

from alfred.refs.tags import (
    ReferenceTag,
    ReferenceTagParseError,
    extract_reference_tags,
    iter_reference_tags,
)


# ---------------------------------------------------------------------------
# Canonical-form acceptance
# ---------------------------------------------------------------------------


def test_extracts_future_doc_tag() -> None:
    text = "See `docs/CHARTER.md` [future-doc: demo workspace path]."
    tags = extract_reference_tags(text)
    assert len(tags) == 1
    tag = tags[0]
    assert tag.kind == "future-doc"
    assert tag.path == "demo workspace path"
    assert tag.line == 1
    # Column points at the opening `[`.
    assert text[tag.start] == "["
    assert text[tag.end - 1] == "]"


def test_extracts_future_path_tag() -> None:
    text = "Open `docs/handovers/` [future-path: external workspace dir]."
    tags = extract_reference_tags(text)
    assert len(tags) == 1
    assert tags[0].kind == "future-path"
    assert tags[0].path == "external workspace dir"


def test_extracts_multiple_tags_in_order() -> None:
    text = (
        "Line one with [future-doc: first].\n"
        "Line two with [future-path: second].\n"
        "Line three with [future-doc: third].\n"
    )
    tags = extract_reference_tags(text)
    assert [(t.kind, t.path, t.line) for t in tags] == [
        ("future-doc", "first", 1),
        ("future-path", "second", 2),
        ("future-doc", "third", 3),
    ]


def test_trims_whitespace_around_path() -> None:
    text = "x [future-doc:   spaced path   ] y"
    tags = extract_reference_tags(text)
    assert len(tags) == 1
    assert tags[0].path == "spaced path"


def test_path_may_contain_inner_brackets_text_but_not_closing_bracket() -> None:
    # The path may include almost any character except `]` or newline.
    text = "x [future-doc: with (parens) and a, comma] y"
    tags = extract_reference_tags(text)
    assert tags[0].path == "with (parens) and a, comma"


def test_returns_empty_list_when_no_tags() -> None:
    assert extract_reference_tags("plain prose with no tags") == []
    assert extract_reference_tags("") == []


def test_iter_reference_tags_is_an_iterator() -> None:
    text = "[future-doc: a] and [future-path: b]"
    it = iter_reference_tags(text)
    first = next(it)
    second = next(it)
    with pytest.raises(StopIteration):
        next(it)
    assert (first.kind, first.path) == ("future-doc", "a")
    assert (second.kind, second.path) == ("future-path", "b")


def test_location_metadata_is_accurate_across_lines() -> None:
    text = "alpha\nbeta [future-doc: x]\n"
    [tag] = extract_reference_tags(text)
    assert tag.line == 2
    # `[` is the 6th character of line 2 (after "beta ").
    assert tag.col == 6


# ---------------------------------------------------------------------------
# Strict rejection of malformed variants
# ---------------------------------------------------------------------------


def test_rejects_missing_colon() -> None:
    text = "x [future-doc demo workspace path] y"
    with pytest.raises(ReferenceTagParseError) as exc_info:
        extract_reference_tags(text)
    err = exc_info.value
    assert err.line == 1
    assert err.col == 3
    assert "malformed" in err.message
    assert "[future-doc" in err.snippet


def test_rejects_missing_closing_bracket() -> None:
    text = "x [future-path: dangling\nnext line"
    with pytest.raises(ReferenceTagParseError) as exc_info:
        extract_reference_tags(text)
    assert exc_info.value.line == 1


def test_rejects_empty_path() -> None:
    text = "x [future-doc:] y"
    with pytest.raises(ReferenceTagParseError) as exc_info:
        extract_reference_tags(text)
    assert "empty path" in exc_info.value.message


def test_rejects_empty_path_with_only_whitespace() -> None:
    text = "x [future-doc:    ] y"
    with pytest.raises(ReferenceTagParseError) as exc_info:
        extract_reference_tags(text)
    assert "empty path" in exc_info.value.message


def test_rejects_whitespace_before_colon() -> None:
    # Plan: "Require a colon after the prefix: `[future-doc:` not `[future-doc ]`."
    text = "x [future-doc : path] y"
    with pytest.raises(ReferenceTagParseError):
        extract_reference_tags(text)


def test_rejects_extended_prefix() -> None:
    text = "x [future-document: path] y"
    with pytest.raises(ReferenceTagParseError):
        extract_reference_tags(text)


def test_rejects_when_first_candidate_is_malformed_even_if_later_one_is_ok() -> None:
    text = "first [future-doc bad] then [future-doc: ok]"
    with pytest.raises(ReferenceTagParseError) as exc_info:
        extract_reference_tags(text)
    # Reports the first failing location, not the later good one.
    assert exc_info.value.col == 7


def test_error_includes_offending_snippet() -> None:
    text = "prose [future-doc bad-form] more"
    with pytest.raises(ReferenceTagParseError) as exc_info:
        extract_reference_tags(text)
    assert exc_info.value.snippet.startswith("[future-doc")


def test_case_sensitive_prefix_is_not_treated_as_candidate() -> None:
    # Wrong case is silently not recognised (it is not a "near miss" of the
    # canonical form; it is unrelated text). No error, no tag.
    text = "x [Future-Doc: path] y"
    assert extract_reference_tags(text) == []


# ---------------------------------------------------------------------------
# ReferenceTag dataclass
# ---------------------------------------------------------------------------


def test_reference_tag_is_frozen() -> None:
    tag = ReferenceTag(
        kind="future-doc", path="x", start=0, end=1, line=1, col=1
    )
    with pytest.raises(Exception):
        tag.path = "y"  # type: ignore[misc]
