"""Tests for the Planner agent."""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from alfred.agents import planner
from alfred.schemas.agent import (
    BoardState,
    BoardStory,
    PlannerInput,
    RAGChunk,
    VelocityRecord,
)
from alfred.tools import llm


# ---------------------------------------------------------------------------
# Fake LLM provider
# ---------------------------------------------------------------------------

_VALID_OUTPUT = {
    "draft_handover_markdown": "# Draft Handover\n\n## Checkpoint\n\nSome content.",
    "sprint_plan": {
        "sprint_number": 5,
        "proposed_capacity_points": 21,
        "committed_story_ids": ["ITEM_1", "ITEM_2"],
        "rationale": "Based on 85% historical completion rate.",
    },
    "task_decomposition": ["Task A", "Task B"],
    "open_questions": ["Should we defer item X?"],
}


@pytest.fixture(autouse=True)
def _restore_providers():
    original = dict(llm._PROVIDERS)
    yield
    llm._PROVIDERS.clear()
    llm._PROVIDERS.update(original)


def _install_fake(response: dict[str, Any]) -> dict[str, int]:
    state = {"calls": 0}

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        state["calls"] += 1
        return response, 10

    llm._PROVIDERS["fake"] = fake
    return state


def _minimal_input() -> PlannerInput:
    return PlannerInput(
        board_state=BoardState(
            sprint_number=5,
            sprint_start=date(2026, 4, 1),
            sprint_end=date(2026, 4, 14),
            stories=[
                BoardStory(id="ITEM_1", title="Build login page", status="In Progress", story_points=3),
                BoardStory(id="ITEM_2", title="Fix DB migration", status="Todo", story_points=5),
            ],
        )
    )


# ---------------------------------------------------------------------------
# Return type and schema validation
# ---------------------------------------------------------------------------


def test_run_planner_returns_planner_output() -> None:
    from alfred.schemas.agent import PlannerOutput
    _install_fake(_VALID_OUTPUT)
    out = planner.run_planner(_minimal_input(), provider="fake", model="m")
    assert isinstance(out, PlannerOutput)
    assert out.draft_handover_markdown.startswith("# Draft Handover")


def test_run_planner_sprint_plan_populated() -> None:
    _install_fake(_VALID_OUTPUT)
    out = planner.run_planner(_minimal_input(), provider="fake", model="m")
    assert out.sprint_plan is not None
    assert out.sprint_plan.sprint_number == 5
    assert out.sprint_plan.proposed_capacity_points == 21


def test_run_planner_task_decomposition() -> None:
    _install_fake(_VALID_OUTPUT)
    out = planner.run_planner(_minimal_input(), provider="fake", model="m")
    assert out.task_decomposition == ["Task A", "Task B"]


def test_run_planner_open_questions() -> None:
    _install_fake(_VALID_OUTPUT)
    out = planner.run_planner(_minimal_input(), provider="fake", model="m")
    assert len(out.open_questions) == 1


# ---------------------------------------------------------------------------
# Prompt construction — verify key inputs appear in prompt
# ---------------------------------------------------------------------------


def test_prompt_includes_board_stories() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _VALID_OUTPUT, 0

    llm._PROVIDERS["fake"] = fake
    planner.run_planner(_minimal_input(), provider="fake", model="m")

    prompt = captured[0]
    assert "Build login page" in prompt
    assert "Fix DB migration" in prompt
    assert "Sprint 5" in prompt


def test_prompt_includes_velocity_history() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _VALID_OUTPUT, 0

    llm._PROVIDERS["fake"] = fake

    inp = _minimal_input()
    inp.velocity_history = [
        VelocityRecord(sprint_number=3, points_committed=20, points_completed=17, completion_rate=0.85),
    ]
    planner.run_planner(inp, provider="fake", model="m")

    assert "Sprint 3" in captured[0]
    assert "17/20" in captured[0]


def test_prompt_includes_rag_chunks() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _VALID_OUTPUT, 0

    llm._PROVIDERS["fake"] = fake

    inp = _minimal_input()
    inp.prior_handover_summaries = [
        RAGChunk(
            document_id="handover_12",
            section_header="Decisions",
            content="We decided to deprecate the legacy adapter.",
            relevance_score=0.9,
        )
    ]
    planner.run_planner(inp, provider="fake", model="m")

    assert "handover_12" in captured[0]
    assert "deprecate the legacy adapter" in captured[0]


def test_prompt_includes_sprint_goal() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _VALID_OUTPUT, 0

    llm._PROVIDERS["fake"] = fake

    inp = _minimal_input()
    inp.sprint_goal = "Ship the auth refactor"
    planner.run_planner(inp, provider="fake", model="m")

    assert "Ship the auth refactor" in captured[0]


def test_prompt_references_methodology_properties() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _VALID_OUTPUT, 0

    llm._PROVIDERS["fake"] = fake
    planner.run_planner(_minimal_input(), provider="fake", model="m")

    prompt = captured[0]
    assert "Document as protocol" in prompt
    assert "Checkpoint-gated" in prompt
    assert "Reasoning/execution isolation" in prompt


# ---------------------------------------------------------------------------
# Minimal input (empty board)
# ---------------------------------------------------------------------------


def test_run_planner_empty_board() -> None:
    _install_fake(_VALID_OUTPUT)
    inp = PlannerInput(board_state=BoardState())
    out = planner.run_planner(inp, provider="fake", model="m")
    assert out.draft_handover_markdown  # still produces output
