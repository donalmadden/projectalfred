"""Tests for the planner–judge critique loop in the orchestrator."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pytest

from alfred.orchestrator import _run_critique_loop
from alfred.schemas.agent import (
    PlannerInput,
    PlannerOutput,
    QualityJudgeInput,
    QualityJudgeOutput,
    ValidationIssue,
)
from alfred.schemas.config import AlfredConfig, AgentsConfig, PlannerAgentConfig
from alfred.schemas.handover import CritiqueEntry, HandoverContext, HandoverDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(max_iters: int = 2, threshold: float = 0.8) -> AlfredConfig:
    cfg = AlfredConfig()
    cfg.agents = AgentsConfig(
        planner=PlannerAgentConfig(
            enabled=True,
            max_critique_iterations=max_iters,
            critique_quality_threshold=threshold,
        )
    )
    cfg.llm.provider = "anthropic"
    cfg.llm.model = "m"
    return cfg


def _make_handover() -> HandoverDocument:
    return HandoverDocument(
        id="TEST_HANDOVER_1",
        title="Test",
        date=date.today(),
        author="Alice",
        context=HandoverContext(narrative=""),
    )


def _judge_passing() -> QualityJudgeOutput:
    return QualityJudgeOutput(validation_issues=[], overall_quality_score=0.9)


def _judge_failing(description: str = "Issue.", score: float = 0.5) -> QualityJudgeOutput:
    return QualityJudgeOutput(
        validation_issues=[
            ValidationIssue(severity="warning", section="draft", description=description)
        ],
        overall_quality_score=score,
    )


def _planner_out(draft: str = "# Revised Draft\n\nRevised content.") -> PlannerOutput:
    return PlannerOutput(
        draft_handover_markdown=draft,
        task_decomposition=[],
        open_questions=[],
    )


# ---------------------------------------------------------------------------
# Test 1: loop runs exactly 2 iterations when first judge fails, second passes
# ---------------------------------------------------------------------------


def test_loop_stops_when_judge_passes_on_second_iteration(monkeypatch: Any) -> None:
    """First judge returns one issue; second returns none. Loop runs exactly 2 judge calls."""
    judge_calls: list[QualityJudgeInput] = []
    planner_calls: list[PlannerInput] = []

    def mock_judge(inp: QualityJudgeInput, *, provider: str, model: str, db_path: Optional[str] = None) -> QualityJudgeOutput:
        judge_calls.append(inp)
        return _judge_failing() if len(judge_calls) == 1 else _judge_passing()

    def mock_planner(inp: PlannerInput, *, provider: str, model: str, db_path: Optional[str] = None) -> PlannerOutput:
        planner_calls.append(inp)
        return _planner_out("# Revised\n\n## CHECKPOINT-1\n\nAll good.")

    monkeypatch.setattr("alfred.agents.quality_judge.run_quality_judge", mock_judge)
    monkeypatch.setattr("alfred.agents.planner.run_planner", mock_planner)

    result = _run_critique_loop(
        "# Initial Draft\n\nContent.",
        _make_handover(),
        _make_config(max_iters=2),
        None,
    )

    assert len(judge_calls) == 2
    assert len(planner_calls) == 1
    assert "Revised" in result


# ---------------------------------------------------------------------------
# Test 2: loop stops at max_critique_iterations when judge always fails
# ---------------------------------------------------------------------------


def test_loop_stops_at_max_iterations_when_judge_always_fails(monkeypatch: Any) -> None:
    """Judge always returns issues. Loop stops at max_critique_iterations; returns best draft."""
    judge_calls: list[QualityJudgeInput] = []
    scores = [0.4, 0.6]

    def mock_judge(inp: QualityJudgeInput, *, provider: str, model: str, db_path: Optional[str] = None) -> QualityJudgeOutput:
        score = scores[min(len(judge_calls), len(scores) - 1)]
        judge_calls.append(inp)
        return _judge_failing(score=score)

    def mock_planner(inp: PlannerInput, *, provider: str, model: str, db_path: Optional[str] = None) -> PlannerOutput:
        return _planner_out("# Better Draft\n\nImproved.")

    monkeypatch.setattr("alfred.agents.quality_judge.run_quality_judge", mock_judge)
    monkeypatch.setattr("alfred.agents.planner.run_planner", mock_planner)

    result = _run_critique_loop(
        "# Initial Draft\n\nContent.",
        _make_handover(),
        _make_config(max_iters=2),
        None,
    )

    assert len(judge_calls) == 2
    # Better Draft scored 0.6 > initial 0.4 — should be returned
    assert "Better Draft" in result


# ---------------------------------------------------------------------------
# Test 3: critique_history is written to the HandoverDocument after each iteration
# ---------------------------------------------------------------------------


def test_critique_history_written_to_handover(monkeypatch: Any) -> None:
    """critique_history entries are appended to the document after each failing iteration."""

    def mock_judge(inp: QualityJudgeInput, *, provider: str, model: str, db_path: Optional[str] = None) -> QualityJudgeOutput:
        return _judge_failing("Needs a checkpoint.", score=0.5)

    def mock_planner(inp: PlannerInput, *, provider: str, model: str, db_path: Optional[str] = None) -> PlannerOutput:
        return _planner_out()

    monkeypatch.setattr("alfred.agents.quality_judge.run_quality_judge", mock_judge)
    monkeypatch.setattr("alfred.agents.planner.run_planner", mock_planner)

    handover = _make_handover()
    _run_critique_loop("# Draft\n\nContent.", handover, _make_config(max_iters=2), None)

    assert len(handover.critique_history) == 1
    entry = handover.critique_history[0]
    assert isinstance(entry, CritiqueEntry)
    assert entry.iteration == 0
    assert entry.quality_score == 0.5
    assert "Needs a checkpoint." in entry.validation_issues


# ---------------------------------------------------------------------------
# Test 4: planner receives prior_critique on revision iteration
# ---------------------------------------------------------------------------


def test_planner_receives_prior_critique_on_revision(monkeypatch: Any) -> None:
    """The planner input on revision includes the critique from the previous iteration."""
    judge_calls: list[QualityJudgeInput] = []
    planner_inputs: list[PlannerInput] = []

    def mock_judge(inp: QualityJudgeInput, *, provider: str, model: str, db_path: Optional[str] = None) -> QualityJudgeOutput:
        judge_calls.append(inp)
        return _judge_failing("Add a proper checkpoint section.") if len(judge_calls) == 1 else _judge_passing()

    def mock_planner(inp: PlannerInput, *, provider: str, model: str, db_path: Optional[str] = None) -> PlannerOutput:
        planner_inputs.append(inp)
        return _planner_out()

    monkeypatch.setattr("alfred.agents.quality_judge.run_quality_judge", mock_judge)
    monkeypatch.setattr("alfred.agents.planner.run_planner", mock_planner)

    _run_critique_loop("# Draft\n\nContent.", _make_handover(), _make_config(max_iters=2), None)

    assert len(planner_inputs) == 1
    assert planner_inputs[0].prior_critique is not None
    assert len(planner_inputs[0].prior_critique) == 1
    assert "Add a proper checkpoint section." in planner_inputs[0].prior_critique[0].validation_issues
