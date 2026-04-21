"""Tests for the critique-loop wiring of the deterministic validators.

Covers C5 of the factual validator / realism plan: deterministic findings
produced by `validate_current_state_facts` + `validate_future_task_realism`
must flow into the next planner iteration via `PlannerInput.deterministic_findings`,
and the loop's early-exit must consider both feedback channels.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from alfred import orchestrator
from alfred.orchestrator import _run_critique_loop
from alfred.schemas.agent import (
    PlannerOutput,
    QualityJudgeOutput,
    ValidationIssue,
)
from alfred.schemas.config import AlfredConfig
from alfred.schemas.handover import HandoverContext, HandoverDocument


@pytest.fixture(autouse=True)
def _restore_runners():
    original = dict(orchestrator._AGENT_RUNNERS)
    yield
    orchestrator._AGENT_RUNNERS.clear()
    orchestrator._AGENT_RUNNERS.update(original)


def _config(max_iters: int = 2, threshold: float = 0.99) -> AlfredConfig:
    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = ""
    cfg.github.org = ""
    cfg.rag.index_path = ""
    cfg.handover.template_path = ""  # skip scaffold load
    cfg.agents.planner.max_critique_iterations = max_iters
    cfg.agents.planner.critique_quality_threshold = threshold
    return cfg


def _handover() -> HandoverDocument:
    return HandoverDocument(
        id="TEST_HANDOVER_1",
        title="Test",
        date=date.today(),
        author="Test",
        context=HandoverContext(narrative="Test handover."),
    )


_FACTUALLY_BAD_DRAFT = """# Alfred's Handover Document #6 — Test

## CONTEXT — READ THIS FIRST
**Document Date:** 2026-04-21

## WHAT EXISTS TODAY
- `src/alfred/state/` module handles persistence today.
- `.github/workflows/release.yml` is already wired into CI today.

## HARD RULES
1. No classes.

## TASK OVERVIEW
| # | Task | Deliverable |
|---|---|---|
| 1 | Add thing | thing |

## TASK 1 — Add thing
Goal.

## WHAT NOT TO DO
1. Don't break things.

## POST-MORTEM
TBD
"""

_CLEAN_DRAFT = """# Alfred's Handover Document #6 — Test

## CONTEXT — READ THIS FIRST
**Document Date:** 2026-04-21

## WHAT EXISTS TODAY
- `src/alfred/orchestrator.py` coordinates task dispatch today.

## HARD RULES
1. No classes.

## TASK OVERVIEW
| # | Task | Deliverable |
|---|---|---|
| 1 | Add thing | thing |

## TASK 1 — Add thing
Goal.

## WHAT NOT TO DO
1. Don't break things.

## POST-MORTEM
TBD
"""


def _patch_judge(monkeypatch: pytest.MonkeyPatch, *, score: float, issues: list[str]) -> None:
    def fake_judge(inp: Any, **_: Any) -> QualityJudgeOutput:
        return QualityJudgeOutput(
            checkpoint_evaluations=[],
            validation_issues=[
                ValidationIssue(severity="error", section="x", description=msg)
                for msg in issues
            ],
            overall_quality_score=score,
        )

    monkeypatch.setattr(
        "alfred.agents.quality_judge.run_quality_judge", fake_judge
    )


def _patch_planner(monkeypatch: pytest.MonkeyPatch, drafts: list[str]) -> list[Any]:
    """Install a fake planner that returns ``drafts`` in order; records each input."""
    received: list[Any] = []
    iter_index = {"i": 0}

    def fake_planner(inp: Any, **_: Any) -> PlannerOutput:
        received.append(inp)
        idx = min(iter_index["i"], len(drafts) - 1)
        iter_index["i"] += 1
        return PlannerOutput(draft_handover_markdown=drafts[idx])

    monkeypatch.setattr("alfred.agents.planner.run_planner", fake_planner)
    monkeypatch.setattr(
        "alfred.agents.planner.load_canonical_template", lambda _path: None
    )
    monkeypatch.setattr("alfred.tools.git_log.read_git_log", lambda: [])
    monkeypatch.setattr("alfred.tools.llm.resolve_model", lambda *_a, **_k: ("fake", "m"))
    return received


def test_factual_errors_flow_into_next_planner_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A draft with factual errors triggers deterministic_findings in the next
    iteration's PlannerInput."""
    _patch_judge(monkeypatch, score=0.5, issues=["needs revision"])
    received = _patch_planner(monkeypatch, drafts=[_CLEAN_DRAFT])

    cfg = _config(max_iters=2, threshold=0.99)
    h = _handover()

    _run_critique_loop(
        _FACTUALLY_BAD_DRAFT,
        h,
        cfg,
        db_path=None,
        repo_facts_summary=["Agents: planner"],
        generation_date="2026-04-21",
    )

    assert received, "planner should have been called for the revision iteration"
    findings = received[0].deterministic_findings
    assert findings, "bad draft should have produced deterministic findings"
    joined = "\n".join(f.format() for f in findings)
    # The bogus `src/alfred/state/` path is the kind of claim the factual
    # validator catches; the exact message format is covered by validator tests.
    assert "src/alfred/state" in joined or "ERROR" in joined


def test_critique_history_records_deterministic_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_judge(monkeypatch, score=0.5, issues=["needs revision"])
    _patch_planner(monkeypatch, drafts=[_CLEAN_DRAFT])

    cfg = _config(max_iters=2, threshold=0.99)
    h = _handover()

    _run_critique_loop(
        _FACTUALLY_BAD_DRAFT,
        h,
        cfg,
        db_path=None,
        repo_facts_summary=[],
    )

    assert len(h.critique_history) == 1
    entry = h.critique_history[0]
    assert entry.validation_issues == ["needs revision"]
    assert entry.deterministic_findings, "findings should be recorded on the critique entry"


def test_clean_draft_with_high_score_exits_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When judge gives a passing score AND validator findings are empty,
    the loop exits without a revision call."""
    _patch_judge(monkeypatch, score=1.0, issues=[])
    received = _patch_planner(monkeypatch, drafts=[_FACTUALLY_BAD_DRAFT])

    cfg = _config(max_iters=3, threshold=0.8)
    h = _handover()

    best = _run_critique_loop(
        _CLEAN_DRAFT,
        h,
        cfg,
        db_path=None,
        repo_facts_summary=[],
    )

    assert best == _CLEAN_DRAFT
    assert received == [], "planner should not be called when draft is already clean"
    assert h.critique_history == []


def test_validator_errors_prevent_early_exit_despite_passing_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even when the judge gives a passing score, deterministic ERRORs must
    force another revision iteration."""
    _patch_judge(monkeypatch, score=1.0, issues=[])
    received = _patch_planner(monkeypatch, drafts=[_CLEAN_DRAFT])

    cfg = _config(max_iters=2, threshold=0.8)
    h = _handover()

    _run_critique_loop(
        _FACTUALLY_BAD_DRAFT,
        h,
        cfg,
        db_path=None,
        repo_facts_summary=[],
    )

    assert received, "validator errors should trigger a revision call"
    assert received[0].deterministic_findings
