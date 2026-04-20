"""T1.2 — Orchestrator invariants.

Properties asserted:
- orchestrate() always returns the same HandoverDocument instance (in-place mutation)
- Tasks whose result is already set are never re-dispatched (statelessness property 5)
- Results written by the runner are visible on the document after orchestrate() returns
- A STOP checkpoint verdict raises CheckpointHalt with the checkpoint ID
- An ESCALATE checkpoint verdict raises HumanEscalation with the checkpoint ID
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from alfred import orchestrator
from alfred.orchestrator import CheckpointHalt, HumanEscalation, orchestrate, set_agent_runner
from alfred.schemas.checkpoint import Checkpoint, DecisionRule, DecisionTable
from alfred.schemas.config import AlfredConfig
from alfred.schemas.handover import HandoverContext, HandoverDocument, HandoverTask, TaskResult
from alfred.tools import llm

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config() -> AlfredConfig:
    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = ""
    cfg.github.org = ""
    cfg.rag.index_path = ""
    return cfg


def _document(tasks: list[HandoverTask]) -> HandoverDocument:
    return HandoverDocument(
        id="PROP",
        title="Property test",
        date=date.today(),
        author="hypothesis",
        context=HandoverContext(narrative="invariant test"),
        tasks=tasks,
    )


def _install_fake_llm(matched_index: int) -> None:
    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        return {"matched_index": matched_index, "reasoning": "prop"}, 0

    llm._PROVIDERS["fake"] = fake


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

_task_result_st = st.builds(
    TaskResult,
    completed=st.booleans(),
    output_summary=st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=50,
    ),
    commits=st.just([]),
    files_modified=st.just([]),
    pivot_taken=st.none(),
)

# ---------------------------------------------------------------------------
# T1.2 — Orchestrator invariants
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(st.lists(_task_result_st, min_size=0, max_size=5))
def test_orchestrate_returns_same_handover_document_instance(
    results: list[TaskResult],
) -> None:
    """orchestrate() returns the exact same HandoverDocument object it received."""
    tasks = [
        HandoverTask(id=str(i), title="t", goal="g", result=r)
        for i, r in enumerate(results)
    ]
    h = _document(tasks)
    returned = orchestrate(h, _config())
    assert returned is h
    assert isinstance(returned, HandoverDocument)


@settings(max_examples=100)
@given(st.lists(_task_result_st, min_size=1, max_size=5))
def test_tasks_with_results_are_not_redispatched(results: list[TaskResult]) -> None:
    """Any task whose result field is already set must not trigger the agent runner."""
    dispatch_count = {"n": 0}

    def counting_runner(task, handover, config, db_path):
        dispatch_count["n"] += 1
        return TaskResult(completed=True, output_summary="should not run")

    original_runners = dict(orchestrator._AGENT_RUNNERS)
    set_agent_runner("planner", counting_runner)
    try:
        tasks = [
            HandoverTask(id=str(i), title="t", goal="g", agent_type="planner", result=r)
            for i, r in enumerate(results)
        ]
        h = _document(tasks)
        orchestrate(h, _config())
        assert dispatch_count["n"] == 0
    finally:
        orchestrator._AGENT_RUNNERS.clear()
        orchestrator._AGENT_RUNNERS.update(original_runners)


@settings(max_examples=100)
@given(st.lists(_task_result_st, min_size=1, max_size=5))
def test_runner_results_written_back_to_document(runner_results: list[TaskResult]) -> None:
    """Results returned by the agent runner are written back into each task's result field."""
    results_copy = list(runner_results)
    result_iter = iter(results_copy)

    original_runners = dict(orchestrator._AGENT_RUNNERS)
    set_agent_runner("planner", lambda task, handover, config, db_path: next(result_iter))
    try:
        tasks = [
            HandoverTask(id=str(i), title="t", goal="g", agent_type="planner")
            for i in range(len(runner_results))
        ]
        h = _document(tasks)
        orchestrate(h, _config())
        for i, task in enumerate(h.tasks):
            assert task.result is not None
            assert task.result.completed == results_copy[i].completed
            assert task.result.output_summary == results_copy[i].output_summary
    finally:
        orchestrator._AGENT_RUNNERS.clear()
        orchestrator._AGENT_RUNNERS.update(original_runners)


def test_stop_checkpoint_verdict_raises_checkpoint_halt() -> None:
    """A STOP checkpoint verdict raises CheckpointHalt naming the halting checkpoint."""
    _install_fake_llm(matched_index=0)  # matched_index=0 selects rule[0] → "stop"
    original_providers = dict(llm._PROVIDERS)
    try:
        task = HandoverTask(
            id="1",
            title="t",
            goal="g",
            result=TaskResult(completed=True, output_summary="done"),
            checkpoints=[
                Checkpoint(
                    id="CP-STOP",
                    question="Q",
                    evidence_required="E",
                    decision_table=DecisionTable(
                        rules=[DecisionRule(condition="any", likely_verdict="stop")],
                        default_verdict="stop",
                    ),
                )
            ],
        )
        h = _document([task])
        with pytest.raises(CheckpointHalt, match="CP-STOP"):
            orchestrate(h, _config())
    finally:
        llm._PROVIDERS.clear()
        llm._PROVIDERS.update(original_providers)


def test_escalate_checkpoint_verdict_raises_human_escalation() -> None:
    """An ESCALATE checkpoint verdict raises HumanEscalation naming the checkpoint."""
    _install_fake_llm(matched_index=0)  # matched_index=0 selects rule[0] → "escalate"
    original_providers = dict(llm._PROVIDERS)
    try:
        task = HandoverTask(
            id="1",
            title="t",
            goal="g",
            result=TaskResult(completed=True, output_summary="done"),
            checkpoints=[
                Checkpoint(
                    id="CP-ESC",
                    question="Q",
                    evidence_required="E",
                    decision_table=DecisionTable(
                        rules=[DecisionRule(condition="any", likely_verdict="escalate")],
                        default_verdict="escalate",
                    ),
                )
            ],
        )
        h = _document([task])
        with pytest.raises(HumanEscalation, match="CP-ESC"):
            orchestrate(h, _config())
    finally:
        llm._PROVIDERS.clear()
        llm._PROVIDERS.update(original_providers)
