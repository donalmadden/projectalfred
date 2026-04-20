"""Tests for HandoverDocument schema — render/parse round-trips and Alfred canonical fields."""
from __future__ import annotations

from datetime import date

from alfred.schemas.handover import HandoverContext, HandoverDocument

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GIT_HISTORY = [
    "abc1234  output-hardening: task 3 — feed real git history",
    "def5678  output-hardening: task 2 — wire canonical scaffold",
    "ghi9012  output-hardening: task 1 — add alfred promotion validator",
]

_WHAT_EXISTS = [
    "Alfred planner + critique loop fully wired",
    "Promotion validator at scripts/validate_alfred_handover.py",
]


def _make_doc(**kwargs) -> HandoverDocument:
    defaults = dict(
        id="ALFRED_HANDOVER_4",
        title="Output Hardening",
        date=date(2026, 4, 20),
        author="alfred",
        context=HandoverContext(narrative="Hardening Alfred output shape."),
    )
    defaults.update(kwargs)
    return HandoverDocument(**defaults)


# ---------------------------------------------------------------------------
# render_markdown — Alfred canonical fields present
# ---------------------------------------------------------------------------


def test_render_emits_what_exists_today_heading_when_git_history_set() -> None:
    doc = _make_doc(git_history=_GIT_HISTORY)
    md = doc.render_markdown()
    assert "## WHAT EXISTS TODAY" in md


def test_render_emits_git_history_heading() -> None:
    doc = _make_doc(git_history=_GIT_HISTORY)
    md = doc.render_markdown()
    assert "### Git History" in md


def test_render_git_history_commits_appear_in_output() -> None:
    doc = _make_doc(git_history=_GIT_HISTORY)
    md = doc.render_markdown()
    for commit in _GIT_HISTORY:
        assert commit in md


def test_render_what_exists_today_bullets_appear() -> None:
    doc = _make_doc(what_exists_today=_WHAT_EXISTS)
    md = doc.render_markdown()
    assert "## WHAT EXISTS TODAY" in md
    for item in _WHAT_EXISTS:
        assert item in md


def test_render_both_fields_together() -> None:
    doc = _make_doc(git_history=_GIT_HISTORY, what_exists_today=_WHAT_EXISTS)
    md = doc.render_markdown()
    assert "### Git History" in md
    assert _GIT_HISTORY[0] in md
    assert _WHAT_EXISTS[0] in md


# ---------------------------------------------------------------------------
# render_markdown — Alfred canonical fields absent (legacy compat)
# ---------------------------------------------------------------------------


def test_render_omits_what_exists_today_when_fields_empty() -> None:
    doc = _make_doc()
    md = doc.render_markdown()
    assert "## WHAT EXISTS TODAY" not in md
    assert "### Git History" not in md


# ---------------------------------------------------------------------------
# from_markdown — parse Alfred canonical section
# ---------------------------------------------------------------------------

_ALFRED_SAMPLE = """\
# Alfred's Handover Document #4 — Output Hardening

## CONTEXT — READ THIS FIRST

**Author:** alfred
**Document Date:** 2026-04-20

Hardening Alfred output shape.

## WHAT EXISTS TODAY

### Git History

```
abc1234  output-hardening: task 3 — feed real git history
def5678  output-hardening: task 2 — wire canonical scaffold
ghi9012  output-hardening: task 1 — add alfred promotion validator
```

- Alfred planner + critique loop fully wired
- Promotion validator at scripts/validate_alfred_handover.py

## HARD RULES

1. Do not fabricate git history.

## TASK OVERVIEW

| # | Task | Deliverable |
|---|---|---|
| 1 | Round-trip test | passing tests |

## WHAT NOT TO DO

1. Do not break legacy parsing.

## POST-MORTEM

All tasks completed successfully.
"""


def test_parse_extracts_git_history() -> None:
    doc = HandoverDocument.from_markdown(_ALFRED_SAMPLE)
    assert doc.git_history == [
        "abc1234  output-hardening: task 3 — feed real git history",
        "def5678  output-hardening: task 2 — wire canonical scaffold",
        "ghi9012  output-hardening: task 1 — add alfred promotion validator",
    ]


def test_parse_extracts_what_exists_today_bullets() -> None:
    doc = HandoverDocument.from_markdown(_ALFRED_SAMPLE)
    assert "Alfred planner + critique loop fully wired" in doc.what_exists_today
    assert "Promotion validator at scripts/validate_alfred_handover.py" in doc.what_exists_today


def test_parse_hard_rules_still_work() -> None:
    doc = HandoverDocument.from_markdown(_ALFRED_SAMPLE)
    assert any("fabricate" in r for r in doc.hard_rules)


def test_parse_anti_patterns_still_work() -> None:
    doc = HandoverDocument.from_markdown(_ALFRED_SAMPLE)
    assert any("legacy" in a for a in doc.anti_patterns)


# ---------------------------------------------------------------------------
# Round-trip: render → parse → render
# ---------------------------------------------------------------------------


def test_round_trip_git_history() -> None:
    original = _make_doc(git_history=_GIT_HISTORY)
    md = original.render_markdown()
    parsed = HandoverDocument.from_markdown(md)
    assert parsed.git_history == _GIT_HISTORY


def test_round_trip_what_exists_today() -> None:
    original = _make_doc(what_exists_today=_WHAT_EXISTS)
    md = original.render_markdown()
    parsed = HandoverDocument.from_markdown(md)
    assert parsed.what_exists_today == _WHAT_EXISTS


def test_round_trip_both_fields() -> None:
    original = _make_doc(git_history=_GIT_HISTORY, what_exists_today=_WHAT_EXISTS)
    md = original.render_markdown()
    parsed = HandoverDocument.from_markdown(md)
    assert parsed.git_history == _GIT_HISTORY
    assert parsed.what_exists_today == _WHAT_EXISTS


# ---------------------------------------------------------------------------
# Legacy / BOB-style documents parse cleanly with empty new fields
# ---------------------------------------------------------------------------

_BOB_SAMPLE = """\
# Bob's Handover Document #36 — Hyperparameter Sweep

## CONTEXT — READ THIS FIRST

**Author:** Bob
**Document Date:** 2025-11-01

Legacy-style document with no WHAT EXISTS TODAY section.

## HARD RULES

1. Keep the sweep reproducible.

## WHAT NOT TO DO

1. Do not hardcode learning rate.

## POST-MORTEM

Sweep completed.
"""


def test_legacy_document_parses_without_new_fields() -> None:
    doc = HandoverDocument.from_markdown(_BOB_SAMPLE)
    assert doc.git_history == []
    assert doc.what_exists_today == []


def test_legacy_document_other_fields_unaffected() -> None:
    doc = HandoverDocument.from_markdown(_BOB_SAMPLE)
    assert any("reproducible" in r for r in doc.hard_rules)
    assert any("hardcode" in a for a in doc.anti_patterns)
