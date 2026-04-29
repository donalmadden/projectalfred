"""Tests for orchestrator-side story-proposal persistence.

Phase 3 Task 3: when ``TASK-SEED-BOARD-001`` runs through
``orchestrate(...)``, the story_generator output must land on
``TaskResult.proposed_story_ids`` *and* (when a db_path is configured)
in the ``story_proposals`` SQLite table — without any harness-side
``set_agent_runner`` interception.

The unit tests target the ``_persist_story_output`` helper directly so
they can fabricate a ``StoryGeneratorOutput`` and assert behaviour
deterministically. The integration test exercises the real
``_story_runner`` by installing a fake LLM provider that returns
story-shaped output, then runs ``orchestrate(...)``.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from alfred import orchestrator
from alfred.orchestrator import _persist_story_output, orchestrate
from alfred.schemas.agent import Story, StoryGeneratorOutput
from alfred.schemas.config import AlfredConfig
from alfred.schemas.handover import (
    HandoverContext,
    HandoverDocument,
    HandoverTask,
)
from alfred.tools import llm, persistence


@pytest.fixture(autouse=True)
def _restore_providers_and_runners():
    original_providers = dict(llm._PROVIDERS)
    original_runners = dict(orchestrator._AGENT_RUNNERS)
    yield
    llm._PROVIDERS.clear()
    llm._PROVIDERS.update(original_providers)
    orchestrator._AGENT_RUNNERS.clear()
    orchestrator._AGENT_RUNNERS.update(original_runners)


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "alfred.db")


def _config(db: str = "") -> AlfredConfig:
    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = db
    cfg.github.org = ""
    cfg.rag.index_path = ""
    return cfg


def _handover(task: HandoverTask, doc_id: str = "ALFRED_HANDOVER_1") -> HandoverDocument:
    return HandoverDocument(
        id=doc_id,
        title="Kickoff",
        date=date(2026, 4, 30),
        author="Alfred",
        context=HandoverContext(narrative="Test."),
        tasks=[task],
    )


def _seed_task() -> HandoverTask:
    return HandoverTask(
        id="TASK-SEED-BOARD-001",
        title="Generate kickoff backlog",
        goal="Produce 6-8 StoryProposal items.",
        agent_type="story_generator",
    )


def _stories(n: int, *, missing_points: int = 0) -> list[Story]:
    out: list[Story] = []
    for i in range(n):
        out.append(
            Story(
                title=f"Story {i+1}",
                description=f"Description {i+1}",
                acceptance_criteria=["AC1", "AC2"],
                story_points=None if i < missing_points else 3,
            )
        )
    return out


def _generator_output(n: int, *, missing_points: int = 0) -> StoryGeneratorOutput:
    return StoryGeneratorOutput(
        stories=_stories(n, missing_points=missing_points),
        rubric_applied="test",
        stories_failing_rubric=[],
    )


# ---------------------------------------------------------------------------
# Unit tests — _persist_story_output directly
# ---------------------------------------------------------------------------


def test_persist_writes_records_and_returns_ids(db_path: str) -> None:
    handover = _handover(_seed_task())
    task = handover.tasks[0]

    result = _persist_story_output(
        task, handover, _generator_output(7), db_path=db_path
    )

    assert result.completed is True
    assert len(result.proposed_story_ids) == 7
    assert "Generated 7 story proposals" in result.output_summary
    assert "persisted" in result.output_summary

    rows = persistence.list_story_proposals(
        db_path, handover_id="ALFRED_HANDOVER_1", task_id="TASK-SEED-BOARD-001"
    )
    assert [r.proposed_story_id for r in rows] == result.proposed_story_ids
    assert all(r.approval_status == "pending" for r in rows)
    assert all(r.handover_id == "ALFRED_HANDOVER_1" for r in rows)


def test_persist_skips_db_write_when_no_db_path() -> None:
    handover = _handover(_seed_task())
    task = handover.tasks[0]

    result = _persist_story_output(
        task, handover, _generator_output(6), db_path=None
    )

    assert result.completed is True
    assert len(result.proposed_story_ids) == 6
    assert "not persisted" in result.output_summary


@pytest.mark.parametrize("n", [0, 5, 9, 12])
def test_persist_marks_incomplete_when_count_out_of_range(db_path: str, n: int) -> None:
    handover = _handover(_seed_task())
    task = handover.tasks[0]

    result = _persist_story_output(
        task, handover, _generator_output(n), db_path=db_path
    )

    assert result.completed is False
    assert result.proposed_story_ids == []
    assert f"Generated {n} valid proposals" in result.output_summary
    assert "expected 6-8" in result.output_summary
    # Critically: when the count is out of range, nothing is persisted.
    assert persistence.list_story_proposals(db_path) == []


def test_persist_skips_stories_missing_story_points(db_path: str) -> None:
    """Stories without story_points are dropped before count validation,
    so a generator that emits 7 with 1 missing yields 6 valid records."""
    handover = _handover(_seed_task())
    task = handover.tasks[0]

    result = _persist_story_output(
        task,
        handover,
        _generator_output(7, missing_points=1),
        db_path=db_path,
    )

    assert result.completed is True
    assert len(result.proposed_story_ids) == 6
    assert "missing story_points" in result.output_summary
    rows = persistence.list_story_proposals(db_path)
    assert len(rows) == 6


def test_persist_includes_rubric_failure_count_in_summary(db_path: str) -> None:
    handover = _handover(_seed_task())
    task = handover.tasks[0]
    output = StoryGeneratorOutput(
        stories=_stories(7),
        rubric_applied="test",
        stories_failing_rubric=["bad story 1", "bad story 2"],
    )

    result = _persist_story_output(task, handover, output, db_path=db_path)

    assert "2 failed rubric" in result.output_summary


def test_persist_uses_handover_and_task_ids_for_linkage(db_path: str) -> None:
    handover = _handover(_seed_task(), doc_id="ALFRED_HANDOVER_99")
    task = handover.tasks[0]

    _persist_story_output(task, handover, _generator_output(6), db_path=db_path)

    rows = persistence.list_story_proposals(
        db_path, handover_id="ALFRED_HANDOVER_99"
    )
    assert len(rows) == 6
    assert all(r.task_id == "TASK-SEED-BOARD-001" for r in rows)


# ---------------------------------------------------------------------------
# Integration test — full orchestrate path with fake LLM provider
# ---------------------------------------------------------------------------


def _install_story_llm_fake(stories_payload: list[dict]) -> None:
    """Install a fake provider that returns a story-generator-shaped dict.

    The orchestrator's default _story_runner calls ``run_story_generator``
    which calls ``llm.complete``. Installing this provider means the
    real _story_runner code path executes — no set_agent_runner override.
    """
    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        return (
            {
                "stories": stories_payload,
                "rubric_applied": "test",
                "stories_failing_rubric": [],
            },
            0,
        )
    llm._PROVIDERS["fake"] = fake


def test_orchestrate_persists_via_default_story_runner(db_path: str) -> None:
    handover = _handover(_seed_task())

    payload = [
        {
            "title": f"Story {i+1}",
            "description": f"Description {i+1}",
            "acceptance_criteria": ["AC1", "AC2"],
            "story_points": 3,
        }
        for i in range(7)
    ]
    _install_story_llm_fake(payload)

    orchestrate(handover, _config(db=db_path))

    task_result = handover.tasks[0].result
    assert task_result is not None
    assert task_result.completed is True
    assert len(task_result.proposed_story_ids) == 7

    rows = persistence.list_story_proposals(
        db_path, handover_id="ALFRED_HANDOVER_1", task_id="TASK-SEED-BOARD-001"
    )
    assert len(rows) == 7
    assert {r.proposed_story_id for r in rows} == set(task_result.proposed_story_ids)


def test_orchestrate_marks_task_incomplete_when_count_out_of_range(
    db_path: str,
) -> None:
    handover = _handover(_seed_task())
    payload = [
        {
            "title": f"Story {i+1}",
            "description": "x",
            "acceptance_criteria": ["a", "b"],
            "story_points": 3,
        }
        for i in range(4)  # too few
    ]
    _install_story_llm_fake(payload)

    orchestrate(handover, _config(db=db_path))

    task_result = handover.tasks[0].result
    assert task_result is not None
    assert task_result.completed is False
    assert task_result.proposed_story_ids == []
    assert persistence.list_story_proposals(db_path) == []
