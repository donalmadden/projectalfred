"""Tests for the Alfred canonical promotion validator.

Covers:
    * a draft missing ``### Git History`` fails the contract
    * a canonical sample with all required sections passes
    * ``### Git History`` in the wrong parent section fails

Scope reminder: the validator targets Alfred canonical promotion. It is
deliberately separate from the permissive ``HandoverDocument`` parser,
which must continue to tolerate legacy BOB corpora.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_alfred_handover.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_alfred_handover", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_alfred_handover"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


CANONICAL_SAMPLE = """# Alfred's Handover Document #99 — Canonical Sample

## CONTEXT — READ THIS FIRST

Everything the reader needs before touching anything.

## WHAT EXISTS TODAY

### Git History

```
abc1234  phase5: real commit
def5678  phase5: another real commit
```

### Current Pipeline

Summary of pipeline state.

## HARD RULES

1. Do not skip the validator.

## WHAT THIS PHASE PRODUCES

- deliverable a

## TASK OVERVIEW

| # | Task | Deliverable |
|---|---|---|
| 1 | Do a thing | thing done |

## TASK 1 — Do a thing

**Goal:** Do the thing.

## WHAT NOT TO DO

1. Do not fabricate git history.

## POST-MORTEM

To be filled in after execution.
"""


MISSING_GIT_HISTORY = CANONICAL_SAMPLE.replace(
    "### Git History\n\n```\nabc1234  phase5: real commit\ndef5678  phase5: another real commit\n```\n\n",
    "",
)


# Git History moved out from under WHAT EXISTS TODAY to under HARD RULES.
WRONG_SECTION = """# Alfred's Handover Document #99 — Canonical Sample

## CONTEXT — READ THIS FIRST

Body.

## WHAT EXISTS TODAY

### Current Pipeline

Summary.

## HARD RULES

1. Do not skip the validator.

### Git History

```
abc1234  phase5: real commit
```

## TASK OVERVIEW

| # | Task | Deliverable |
|---|---|---|
| 1 | Do a thing | thing done |

## WHAT NOT TO DO

1. Do not fabricate git history.

## POST-MORTEM

To be filled in.
"""


def test_canonical_sample_passes():
    errors = validator.validate(CANONICAL_SAMPLE)
    assert errors == []


def test_missing_git_history_fails():
    errors = validator.validate(MISSING_GIT_HISTORY)
    assert any("Git History" in e for e in errors)
    assert any("Missing required H3" in e for e in errors)


def test_git_history_in_wrong_section_fails():
    errors = validator.validate(WRONG_SECTION)
    assert any(
        "Git History" in e and "not under" in e
        for e in errors
    ), f"expected placement error, got: {errors}"


def test_missing_required_h2_fails():
    doc = CANONICAL_SAMPLE.replace("## WHAT NOT TO DO\n\n1. Do not fabricate git history.\n\n", "")
    errors = validator.validate(doc)
    assert any("WHAT NOT TO DO" in e for e in errors)


def test_heading_prefix_with_suffix_is_accepted():
    # Real Alfred handovers often carry a suffix after the required prefix
    # (e.g. "### Git History — Relevant Baseline"). That must still pass.
    doc = CANONICAL_SAMPLE.replace("### Git History", "### Git History — Relevant Baseline")
    assert validator.validate(doc) == []


def test_headings_inside_fenced_code_are_ignored():
    # A ``### Git History`` token inside a code block is not a real heading
    # and must not satisfy the contract.
    injected = MISSING_GIT_HISTORY.replace(
        "## WHAT EXISTS TODAY\n\n### Current Pipeline",
        "## WHAT EXISTS TODAY\n\n```\n### Git History\n```\n\n### Current Pipeline",
    )
    errors = validator.validate(injected)
    assert any("Missing required H3" in e and "Git History" in e for e in errors)


def test_cli_fails_on_draft_missing_git_history(tmp_path: Path):
    draft = tmp_path / "draft.md"
    draft.write_text(MISSING_GIT_HISTORY, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(draft)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Git History" in result.stderr


def test_cli_passes_on_canonical_sample(tmp_path: Path):
    canonical = tmp_path / "canonical.md"
    canonical.write_text(CANONICAL_SAMPLE, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(canonical)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_cli_returns_usage_error_on_missing_file(tmp_path: Path):
    missing = tmp_path / "does_not_exist.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(missing)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


@pytest.mark.parametrize("heading", ["# TOP", "## ", "###"])
def test_malformed_headings_do_not_crash(heading: str):
    # Defensive: the parser must be permissive about weird input.
    validator.validate(heading + "\nbody\n")
