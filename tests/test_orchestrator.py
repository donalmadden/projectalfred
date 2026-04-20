"""Tests for the orchestrator control flow."""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from alfred import orchestrator
from alfred.orchestrator import CheckpointHalt, HumanEscalation, orchestrate, set_agent_runner
from alfred.schemas.checkpoint import Checkpoint, CheckpointResult, DecisionRule, DecisionTable
from alfred.schemas.config import AlfredConfig
from alfred.schemas.handover import (
    HandoverContext,
    HandoverDocument,
    HandoverTask,
    TaskResult,
)
from alfred.tools import llm

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_providers():
    original = dict(llm._PROVIDERS)
    original_runners = dict(orchestrator._AGENT_RUNNERS)
    yield
    llm._PROVIDERS.clear()
    llm._PROVIDERS.update(original)
    orchestrator._AGENT_RUNNERS.clear()
    orchestrator._AGENT_RUNNERS.update(original_runners)


def _config() -> AlfredConfig:
    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = ""  # disable persistence writes in tests
    cfg.github.org = ""     # disable board reads
    cfg.rag.index_path = "" # disable RAG reads
    return cfg


def _handover(tasks: list[HandoverTask]) -> HandoverDocument:
    return HandoverDocument(
        id="TEST_HANDOVER_1",
        title="Test",
        date=date.today(),
        author="Test",
        context=HandoverContext(narrative="Test handover."),
        tasks=tasks,
    )


def _checkpoint(
    cp_id: str,
    rows: list[tuple[str, str]],
) -> Checkpoint:
    rules = [DecisionRule(condition=c, likely_verdict=v) for c, v in rows]  # type: ignore[arg-type]
    return Checkpoint(
        id=cp_id,
        question=f"Evaluate {cp_id}",
        evidence_required="Paste output.",
        decision_table=DecisionTable(rules=rules),
    )


def _install_llm_fake(matched_index: int) -> None:
    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        return {"matched_index": matched_index, "reasoning": "test"}, 0
    llm._PROVIDERS["fake"] = fake


def _noop_runner(result: TaskResult):
    def runner(task, handover, config, db_path):
        return result
    return runner


# ---------------------------------------------------------------------------
# Task dispatch
# ---------------------------------------------------------------------------


def test_task_without_result_is_dispatched() -> None:
    dispatched = {"called": False}

    def runner(task, handover, config, db_path):
        dispatched["called"] = True
        return TaskResult(completed=True, output_summary="done")

    set_agent_runner("planner", runner)
    _install_llm_fake(matched_index=0)  # proceed

    task = HandoverTask(id="1", title="Plan sprint", goal="Plan it", agent_type="planner")
    h = _handover([task])
    orchestrate(h, _config())

    assert dispatched["called"] is True
    assert task.result is not None
    assert task.result.completed is True


def test_task_with_result_is_not_redispatched() -> None:
    dispatched = {"calls": 0}

    def runner(task, handover, config, db_path):
        dispatched["calls"] += 1
        return TaskResult(completed=True, output_summary="done again")

    set_agent_runner("planner", runner)

    task = HandoverTask(
        id="1", title="Plan sprint", goal="Plan it", agent_type="planner",
        result=TaskResult(completed=True, output_summary="already done"),
    )
    h = _handover([task])
    orchestrate(h, _config())

    assert dispatched["calls"] == 0
    assert task.result.output_summary == "already done"


def test_unknown_agent_type_writes_failed_result() -> None:
    task = HandoverTask(id="1", title="Mystery", goal="?", agent_type="unknown_agent")
    h = _handover([task])
    orchestrate(h, _config())

    assert task.result is not None
    assert task.result.completed is False


# ---------------------------------------------------------------------------
# Checkpoint verdict routing
# ---------------------------------------------------------------------------


def test_proceed_verdict_continues() -> None:
    _install_llm_fake(matched_index=0)  # proceed

    task = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="pass"),
        checkpoints=[
            _checkpoint("CP-1", [("All tests pass", "proceed"), ("Tests fail", "stop")])
        ],
    )
    h = _handover([task])
    result_doc = orchestrate(h, _config())

    assert task.checkpoints[0].verdict == "proceed"
    assert result_doc is h  # same object returned


def test_pivot_verdict_records_pivot_and_continues() -> None:
    _install_llm_fake(matched_index=1)  # index 1 = pivot

    task = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="partial"),
        checkpoints=[
            _checkpoint("CP-1", [
                ("All pass", "proceed"),
                ("Partial pass", "pivot"),
                ("All fail", "stop"),
            ])
        ],
    )
    h = _handover([task])
    orchestrate(h, _config())

    assert task.checkpoints[0].verdict == "pivot"
    assert task.result.pivot_taken is not None


def test_stop_verdict_raises_checkpoint_halt() -> None:
    _install_llm_fake(matched_index=2)  # index 2 = stop

    task = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="fail"),
        checkpoints=[
            _checkpoint("CP-1", [
                ("pass", "proceed"),
                ("partial", "pivot"),
                ("fail", "stop"),
            ])
        ],
    )
    h = _handover([task])

    with pytest.raises(CheckpointHalt, match="CP-1"):
        orchestrate(h, _config())


def test_escalate_verdict_raises_human_escalation() -> None:
    _install_llm_fake(matched_index=0)  # index 0 = escalate

    task = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="unclear"),
        checkpoints=[
            _checkpoint("CP-1", [("ambiguous output", "escalate")])
        ],
    )
    h = _handover([task])

    with pytest.raises(HumanEscalation, match="CP-1"):
        orchestrate(h, _config())


def test_no_match_falls_through_to_escalate() -> None:
    _install_llm_fake(matched_index=-1)  # no match → escalate

    task = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="..."),
        checkpoints=[_checkpoint("CP-1", [("something", "proceed")])],
    )
    h = _handover([task])

    with pytest.raises(HumanEscalation):
        orchestrate(h, _config())


# ---------------------------------------------------------------------------
# Checkpoint write-back
# ---------------------------------------------------------------------------


def test_checkpoint_result_written_to_document() -> None:
    _install_llm_fake(matched_index=0)  # proceed

    cp = _checkpoint("CP-1", [("pass", "proceed")])
    task = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="pass"),
        checkpoints=[cp],
    )
    h = _handover([task])
    orchestrate(h, _config())

    assert cp.result is not None
    assert cp.result.verdict == "proceed"
    assert cp.result.evidence_provided is not None


def test_already_evaluated_checkpoint_is_skipped() -> None:
    calls = {"n": 0}

    def counting_fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        calls["n"] += 1
        return {"matched_index": 0, "reasoning": "ok"}, 0

    llm._PROVIDERS["fake"] = counting_fake

    cp = _checkpoint("CP-1", [("pass", "proceed")])
    cp.result = CheckpointResult(verdict="proceed", evidence_provided="pre-set", reasoning="already done")

    task = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="pass"),
        checkpoints=[cp],
    )
    h = _handover([task])
    orchestrate(h, _config())

    assert calls["n"] == 0  # LLM not called for already-evaluated checkpoint


# ---------------------------------------------------------------------------
# Post-mortem write-back on STOP
# ---------------------------------------------------------------------------


def test_stop_writes_post_mortem() -> None:
    _install_llm_fake(matched_index=0)  # stop

    task = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="fail"),
        checkpoints=[_checkpoint("CP-1", [("fail", "stop")])],
    )
    h = _handover([task])

    with pytest.raises(CheckpointHalt):
        orchestrate(h, _config())

    assert h.post_mortem is not None
    assert "CP-1" in h.post_mortem.summary


# ---------------------------------------------------------------------------
# Multiple tasks — sequential execution, stops at halt
# ---------------------------------------------------------------------------


def test_multiple_tasks_executed_in_order() -> None:
    order = []

    def make_runner(name: str):
        def runner(task, handover, config, db_path):
            order.append(name)
            return TaskResult(completed=True, output_summary=name)
        return runner

    set_agent_runner("planner", make_runner("planner"))
    set_agent_runner("retro_analyst", make_runner("retro"))

    tasks = [
        HandoverTask(id="1", title="Plan", goal="p", agent_type="planner"),
        HandoverTask(id="2", title="Retro", goal="r", agent_type="retro_analyst"),
    ]
    h = _handover(tasks)
    orchestrate(h, _config())

    assert order == ["planner", "retro"]


def test_halt_stops_subsequent_tasks() -> None:
    _install_llm_fake(matched_index=0)  # stop in CP

    executed = {"second": False}

    def second_runner(task, handover, config, db_path):
        executed["second"] = True
        return TaskResult(completed=True, output_summary="should not run")

    set_agent_runner("retro_analyst", second_runner)

    task1 = HandoverTask(
        id="1", title="t", goal="g",
        result=TaskResult(completed=True, output_summary="fail"),
        checkpoints=[_checkpoint("CP-1", [("fail", "stop")])],
    )
    task2 = HandoverTask(id="2", title="t2", goal="g2", agent_type="retro_analyst")
    h = _handover([task1, task2])

    with pytest.raises(CheckpointHalt):
        orchestrate(h, _config())

    assert executed["second"] is False


# ---------------------------------------------------------------------------
# Statelessness — re-runnable from partial handover
# ---------------------------------------------------------------------------


def test_rerunnable_from_partial_handover() -> None:
    dispatched = {"calls": 0}

    def runner(task, handover, config, db_path):
        dispatched["calls"] += 1
        return TaskResult(completed=True, output_summary="done")

    set_agent_runner("planner", runner)
    _install_llm_fake(matched_index=0)  # proceed

    # task1 already done with proceed checkpoint; task2 still pending
    cp = _checkpoint("CP-1", [("done", "proceed")])
    cp.result = CheckpointResult(verdict="proceed", evidence_provided="done", reasoning="ok")

    task1 = HandoverTask(
        id="1", title="done task", goal="g", agent_type="planner",
        result=TaskResult(completed=True, output_summary="already done"),
        checkpoints=[cp],
    )
    task2 = HandoverTask(id="2", title="pending task", goal="g2", agent_type="planner")
    h = _handover([task1, task2])

    orchestrate(h, _config())

    assert dispatched["calls"] == 1  # only task2 dispatched
    assert task2.result is not None
