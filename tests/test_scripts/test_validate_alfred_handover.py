"""Regression tests for the Alfred canonical promotion validator.

These tests reproduce the original miss (a draft missing ### Git History
silently becoming protocol) and prove the validator is fail-closed.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_alfred_handover import validate

# ---------------------------------------------------------------------------
# Minimal valid document used as the baseline for all mutation tests
# ---------------------------------------------------------------------------

_VALID_ALFRED_DOC = """\
# Alfred's Handover Document #5 — Phase 6

## CONTEXT — READ THIS FIRST

**Author:** alfred
**Document Date:** 2026-04-20

Narrative context here.

## WHAT EXISTS TODAY

### Git History

```
abc1234  output-hardening: task 3 — feed real git history
def5678  output-hardening: task 2 — wire canonical scaffold
```

- Planner agent wired end-to-end.

## HARD RULES

1. Do not fabricate git history.

## TASK OVERVIEW

| # | Task | Deliverable |
|---|---|---|
| 1 | Implement feature | passing tests |

## WHAT NOT TO DO

1. Do not break legacy parsing.

## POST-MORTEM

All tasks completed.
"""


# ---------------------------------------------------------------------------
# Original miss: draft missing ### Git History cannot promote
# ---------------------------------------------------------------------------

_MISSING_GIT_HISTORY = """\
# Alfred's Handover Document #5 — Phase 6

## CONTEXT — READ THIS FIRST

**Author:** alfred
**Document Date:** 2026-04-20

Narrative context here.

## WHAT EXISTS TODAY

- Planner agent wired end-to-end.

## HARD RULES

1. Do not fabricate git history.

## TASK OVERVIEW

| # | Task | Deliverable |
|---|---|---|
| 1 | Implement feature | passing tests |

## WHAT NOT TO DO

1. Do not break legacy parsing.

## POST-MORTEM

All tasks completed.
"""


def test_missing_git_history_fails_validation() -> None:
    """Regression: the original miss — omitting ### Git History must block promotion."""
    errors = validate(_MISSING_GIT_HISTORY)
    assert any("Git History" in e for e in errors), (
        f"Expected Git History error but got: {errors}"
    )


def test_missing_git_history_error_names_parent_section() -> None:
    errors = validate(_MISSING_GIT_HISTORY)
    git_err = next((e for e in errors if "Git History" in e), None)
    assert git_err is not None
    assert "WHAT EXISTS TODAY" in git_err


# ---------------------------------------------------------------------------
# Other required sections also block promotion when absent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("heading", [
    "## CONTEXT — READ THIS FIRST",
    "## WHAT EXISTS TODAY",
    "## HARD RULES",
    "## TASK OVERVIEW",
    "## WHAT NOT TO DO",
    "## POST-MORTEM",
])
def test_missing_required_h2_fails(heading: str) -> None:
    doc = "\n".join(
        line for line in _VALID_ALFRED_DOC.splitlines()
        if line.strip() != heading.strip()
    )
    errors = validate(doc)
    assert errors, f"Expected failure when '{heading}' is removed but got no errors"


def test_git_history_under_wrong_section_fails() -> None:
    """### Git History under ## HARD RULES must not satisfy the contract."""
    doc = _VALID_ALFRED_DOC.replace(
        "## WHAT EXISTS TODAY\n\n### Git History",
        "## WHAT EXISTS TODAY\n\n",
    ).replace(
        "## HARD RULES\n\n1. Do not fabricate git history.",
        "## HARD RULES\n\n### Git History\n\n```\nabc1234 some commit\n```\n\n1. Do not fabricate git history.",
    )
    errors = validate(doc)
    assert any("Git History" in e for e in errors)


# ---------------------------------------------------------------------------
# Canonical passing sample — the baseline document promotes cleanly
# ---------------------------------------------------------------------------

def test_canonical_passing_sample_validates() -> None:
    """The canonical sample document must produce zero errors."""
    assert validate(_VALID_ALFRED_DOC) == []


def test_valid_document_exits_zero_via_cli(tmp_path: Path) -> None:
    """End-to-end CLI: a valid document exits 0."""
    f = tmp_path / "handover.md"
    f.write_text(_VALID_ALFRED_DOC, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/validate_alfred_handover.py", str(f)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_invalid_document_exits_one_via_cli(tmp_path: Path) -> None:
    """End-to-end CLI: a document missing ### Git History exits 1."""
    f = tmp_path / "bad_handover.md"
    f.write_text(_MISSING_GIT_HISTORY, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/validate_alfred_handover.py", str(f)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
    assert "Git History" in result.stderr


# ---------------------------------------------------------------------------
# ALFRED_HANDOVER_5_DRAFT.md passes the validator
# ---------------------------------------------------------------------------

def test_alfred_handover_5_draft_passes_promotion() -> None:
    """The canonical Phase 6 draft must pass the promotion validator."""
    draft = Path("docs/archive/ALFRED_HANDOVER_5_DRAFT.md")
    assert draft.is_file(), "docs/archive/ALFRED_HANDOVER_5_DRAFT.md not found"
    errors = validate(draft.read_text(encoding="utf-8"))
    assert errors == [], f"Promotion blocked: {errors}"


def test_alfred_handover_5_draft_exits_zero_via_cli() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_alfred_handover.py", "docs/archive/ALFRED_HANDOVER_5_DRAFT.md"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Heading in fenced code block must not satisfy contract
# ---------------------------------------------------------------------------

def test_heading_inside_code_block_does_not_count() -> None:
    """A ### Git History inside a ``` block must not satisfy the structural contract."""
    doc = """\
# Alfred's Handover Document #5 — Phase 6

## CONTEXT — READ THIS FIRST

**Author:** alfred

Narrative.

## WHAT EXISTS TODAY

Example of a handover format:

```
### Git History
```

## HARD RULES

1. No fabrication.

## TASK OVERVIEW

| # | Task | Deliverable |
|---|---|---|
| 1 | Implement feature | passing tests |

## WHAT NOT TO DO

1. Do not break legacy.

## POST-MORTEM

Done.
"""
    errors = validate(doc)
    assert any("Git History" in e for e in errors)
