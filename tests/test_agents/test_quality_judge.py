"""Tests for the Quality Judge agent."""
from __future__ import annotations

import json
from typing import Any

import pytest

from alfred.agents import quality_judge
from alfred.schemas.agent import ExecutorOutput, QualityJudgeInput
from alfred.tools import llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _table(checkpoint_id: str, rows: list[dict[str, str]]) -> str:
    return json.dumps({"checkpoint_id": checkpoint_id, "rows": rows})


_STANDARD_TABLE = _table(
    "CHECKPOINT-1",
    [
        {"observation": "All tests pass and imports are clean", "verdict": "proceed"},
        {"observation": "Tests pass but interface needs adjustment", "verdict": "pivot"},
        {"observation": "Tests fail", "verdict": "stop"},
    ],
)

_HANDOVER_WITH_CHECKPOINT = (
    "# Handover\n\n"
    "## Checkpoint\n\n"
    "This handover uses checkpoint-gated execution and a handover document as protocol.\n"
    "Executor and reviewer are isolated. Inline post-mortem and forward plan included.\n"
    "Each session cold-starts from the document.\n"
)


@pytest.fixture(autouse=True)
def _restore_providers():
    original = dict(llm._PROVIDERS)
    yield
    llm._PROVIDERS.clear()
    llm._PROVIDERS.update(original)


def _install_fake(matched_index: int, reasoning: str = "test reason") -> None:
    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        return {"matched_index": matched_index, "reasoning": reasoning}, 0

    llm._PROVIDERS["fake"] = fake


# ---------------------------------------------------------------------------
# Decision-table verdict routing
# ---------------------------------------------------------------------------


def test_verdict_proceed_from_table() -> None:
    _install_fake(matched_index=0)
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE],
        executor_output=ExecutorOutput(task_id="t1", console_output="3 passed"),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")

    assert len(out.checkpoint_evaluations) == 1
    assert out.checkpoint_evaluations[0].verdict == "proceed"
    assert out.checkpoint_evaluations[0].checkpoint_id == "CHECKPOINT-1"


def test_verdict_pivot_from_table() -> None:
    _install_fake(matched_index=1)
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE],
        executor_output=ExecutorOutput(task_id="t1", console_output="passed but issues"),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    assert out.checkpoint_evaluations[0].verdict == "pivot"


def test_verdict_stop_from_table() -> None:
    _install_fake(matched_index=2)
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE],
        executor_output=ExecutorOutput(task_id="t1", console_output="2 failed"),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    assert out.checkpoint_evaluations[0].verdict == "stop"


def test_no_match_falls_through_to_escalate() -> None:
    _install_fake(matched_index=-1)
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE],
        executor_output=ExecutorOutput(task_id="t1", console_output="unexpected output"),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    assert out.checkpoint_evaluations[0].verdict == "escalate"


def test_out_of_range_index_falls_through_to_escalate() -> None:
    _install_fake(matched_index=99)
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE],
        executor_output=ExecutorOutput(task_id="t1", console_output="..."),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    assert out.checkpoint_evaluations[0].verdict == "escalate"


# ---------------------------------------------------------------------------
# HITL escalation
# ---------------------------------------------------------------------------


def test_hitl_required_for_stop_verdict() -> None:
    _install_fake(matched_index=2)  # stop
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE],
        executor_output=ExecutorOutput(task_id="t1", console_output="fail"),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    assert out.hitl_escalation_required is True
    assert out.hitl_escalation_reason is not None


def test_hitl_not_required_for_proceed_verdict() -> None:
    _install_fake(matched_index=0)  # proceed
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE],
        executor_output=ExecutorOutput(task_id="t1", console_output="all pass"),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    assert out.hitl_escalation_required is False


# ---------------------------------------------------------------------------
# Multiple checkpoints
# ---------------------------------------------------------------------------


def test_multiple_checkpoints_evaluated_independently() -> None:
    table2 = _table(
        "CHECKPOINT-2",
        [
            {"observation": "All agents implemented", "verdict": "proceed"},
            {"observation": "Agent missing", "verdict": "stop"},
        ],
    )
    call_count = {"n": 0}

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        idx = 0 if call_count["n"] == 0 else 1
        call_count["n"] += 1
        return {"matched_index": idx, "reasoning": "ok"}, 0

    llm._PROVIDERS["fake"] = fake

    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE, table2],
        executor_output=ExecutorOutput(task_id="t1", console_output="..."),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")

    assert len(out.checkpoint_evaluations) == 2
    assert out.checkpoint_evaluations[0].verdict == "proceed"
    assert out.checkpoint_evaluations[1].verdict == "stop"
    assert out.hitl_escalation_required is True


# ---------------------------------------------------------------------------
# Quality score
# ---------------------------------------------------------------------------


def test_quality_score_all_proceed() -> None:
    _install_fake(matched_index=0)
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[_STANDARD_TABLE],
        executor_output=ExecutorOutput(task_id="t1", console_output="pass"),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    assert out.overall_quality_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Unparseable definition
# ---------------------------------------------------------------------------


def test_unparseable_definition_escalates_without_llm_call() -> None:
    called = {"n": 0}

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        called["n"] += 1
        return {"matched_index": 0, "reasoning": "ok"}, 0

    llm._PROVIDERS["fake"] = fake

    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=["not valid json"],
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")

    assert out.checkpoint_evaluations[0].verdict == "escalate"
    assert called["n"] == 0  # LLM not called for unparseable table


# ---------------------------------------------------------------------------
# Methodology compliance
# ---------------------------------------------------------------------------


def test_methodology_compliance_detected() -> None:
    inp = QualityJudgeInput(
        handover_document_markdown=_HANDOVER_WITH_CHECKPOINT,
        checkpoint_definitions=[],
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    assert out.methodology_compliance["1"] is True  # "handover" present
    assert out.methodology_compliance["2"] is True  # "checkpoint" present


def test_missing_checkpoint_section_creates_warning() -> None:
    inp = QualityJudgeInput(
        handover_document_markdown="# No checkpoints here",
        checkpoint_definitions=[],
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    warnings = [i for i in out.validation_issues if i.severity == "warning"]
    assert any("checkpoint" in w.description.lower() for w in warnings)


def test_compliance_scan_ignores_executor_output() -> None:
    """Executor output has no methodology keywords; handover markdown has all five."""
    markdown = (
        "# Handover\n\n"
        "## Checkpoint\n\n"
        "This document is the handover protocol.\n"
        "Checkpoint-gated execution with verdict routing.\n"
        "Executor and reviewer are isolated from each other.\n"
        "Inline post-mortem and forward plan after failure.\n"
        "Each cold-start resumes from a stateless session document.\n"
    )
    inp = QualityJudgeInput(
        handover_document_markdown=markdown,
        checkpoint_definitions=[],
        executor_output=ExecutorOutput(
            task_id="t1",
            console_output="build: 0 errors. no relevant output here.",
        ),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    for prop in ["1", "2", "3", "4", "5"]:
        assert out.methodology_compliance[prop] is True, f"property {prop} not detected"


def test_compliance_scan_uses_markdown_only() -> None:
    """Keywords only in executor output must not flip compliance flags to True."""
    executor_keywords = (
        "handover document as protocol, checkpoint verdict gate, "
        "executor reviewer isolation, post-mortem forward plan failure analysis, "
        "cold-start stateless session"
    )
    inp = QualityJudgeInput(
        handover_document_markdown="# Sprint Notes\n\nNothing relevant here.",
        checkpoint_definitions=[],
        executor_output=ExecutorOutput(
            task_id="t1",
            console_output=executor_keywords,
        ),
    )
    out = quality_judge.run_quality_judge(inp, provider="fake", model="m")
    for prop in ["1", "2", "3", "4", "5"]:
        assert out.methodology_compliance[prop] is False, f"property {prop} wrongly True"
