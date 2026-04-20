"""Tests for the Story Generator agent."""
from __future__ import annotations

from typing import Any

import pytest

from alfred.agents import story_generator
from alfred.schemas.agent import (
    BoardState,
    BoardStory,
    QualityRubric,
    RAGChunk,
    StoryGeneratorInput,
    StoryGeneratorOutput,
)
from alfred.tools import llm

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_providers():
    original = dict(llm._PROVIDERS)
    yield
    llm._PROVIDERS.clear()
    llm._PROVIDERS.update(original)


def _install_fake(response: dict[str, Any]) -> None:
    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        return response, 0

    llm._PROVIDERS["fake"] = fake


def _rubric(min_ac: int = 2, require_points: bool = True) -> QualityRubric:
    return QualityRubric(
        criteria=["Clear title", "Acceptance criteria present"],
        minimum_acceptance_criteria_count=min_ac,
        require_story_points=require_points,
    )


def _story_response(stories: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stories": stories,
        "rubric_applied": "Fibonacci points + min 2 ACs",
        "stories_failing_rubric": [],
    }


def _good_story(title: str = "My story", points: int = 3) -> dict[str, Any]:
    return {
        "title": title,
        "description": "As a user I want...",
        "acceptance_criteria": ["AC1", "AC2"],
        "story_points": points,
        "labels": [],
        "quality_score": 0.9,
        "quality_notes": "Meets rubric.",
    }


def _minimal_input(rubric: QualityRubric | None = None) -> StoryGeneratorInput:
    return StoryGeneratorInput(
        quality_rubric=rubric or _rubric(),
        board_state=BoardState(sprint_number=5),
    )


# ---------------------------------------------------------------------------
# Return type and schema conformance
# ---------------------------------------------------------------------------


def test_returns_story_generator_output() -> None:
    _install_fake(_story_response([_good_story()]))
    out = story_generator.run_story_generator(_minimal_input(), provider="fake", model="m")
    assert isinstance(out, StoryGeneratorOutput)
    assert len(out.stories) == 1


def test_story_points_are_fibonacci() -> None:
    _install_fake(_story_response([_good_story(points=5), _good_story("B", points=8)]))
    out = story_generator.run_story_generator(_minimal_input(), provider="fake", model="m")
    for story in out.stories:
        assert story.story_points in (1, 2, 3, 5, 8, 13)


def test_rubric_applied_field_propagated() -> None:
    _install_fake(_story_response([_good_story()]))
    out = story_generator.run_story_generator(_minimal_input(), provider="fake", model="m")
    assert out.rubric_applied == "Fibonacci points + min 2 ACs"


# ---------------------------------------------------------------------------
# Rubric enforcement
# ---------------------------------------------------------------------------


def test_story_failing_min_ac_is_excluded() -> None:
    bad = {**_good_story(), "acceptance_criteria": ["only one AC"]}
    _install_fake(_story_response([_good_story(), bad]))
    out = story_generator.run_story_generator(_minimal_input(_rubric(min_ac=2)), provider="fake", model="m")
    assert len(out.stories) == 1
    assert len(out.stories_failing_rubric) == 1
    assert "Too few acceptance criteria" in out.stories_failing_rubric[0]


def test_story_missing_points_excluded_when_required() -> None:
    no_points = {**_good_story(), "story_points": None}
    _install_fake(_story_response([no_points]))
    out = story_generator.run_story_generator(_minimal_input(_rubric(require_points=True)), provider="fake", model="m")
    assert out.stories == []
    assert any("Missing story points" in f for f in out.stories_failing_rubric)


def test_story_without_points_allowed_when_not_required() -> None:
    no_points = {**_good_story(), "story_points": None}
    _install_fake(_story_response([no_points]))
    out = story_generator.run_story_generator(_minimal_input(_rubric(require_points=False)), provider="fake", model="m")
    assert len(out.stories) == 1


def test_llm_failing_rubric_list_preserved() -> None:
    resp = _story_response([_good_story()])
    resp["stories_failing_rubric"] = ["Legacy story: no description"]
    _install_fake(resp)
    out = story_generator.run_story_generator(_minimal_input(), provider="fake", model="m")
    assert "Legacy story: no description" in out.stories_failing_rubric


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def test_prompt_includes_rubric_criteria() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _story_response([_good_story()]), 0

    llm._PROVIDERS["fake"] = fake

    rubric = QualityRubric(
        criteria=["Must have acceptance criteria", "Must have story points"],
        minimum_acceptance_criteria_count=2,
        require_story_points=True,
    )
    story_generator.run_story_generator(_minimal_input(rubric), provider="fake", model="m")

    assert "Must have acceptance criteria" in captured[0]
    assert "Must have story points" in captured[0]


def test_prompt_includes_rag_context() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _story_response([_good_story()]), 0

    llm._PROVIDERS["fake"] = fake

    inp = _minimal_input()
    inp.handover_corpus_chunks = [
        RAGChunk(
            document_id="handover_7",
            section_header="Decisions",
            content="Decided to move auth to a microservice.",
            relevance_score=0.95,
        )
    ]
    story_generator.run_story_generator(inp, provider="fake", model="m")

    assert "handover_7" in captured[0]
    assert "auth to a microservice" in captured[0]


def test_prompt_includes_board_state() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _story_response([_good_story()]), 0

    llm._PROVIDERS["fake"] = fake

    inp = StoryGeneratorInput(
        quality_rubric=_rubric(),
        board_state=BoardState(
            sprint_number=7,
            stories=[BoardStory(id="X", title="Existing task", status="Done")],
        ),
    )
    story_generator.run_story_generator(inp, provider="fake", model="m")

    assert "Existing task" in captured[0]
    assert "Sprint 7" in captured[0]


def test_prompt_includes_generation_instructions() -> None:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _story_response([_good_story()]), 0

    llm._PROVIDERS["fake"] = fake

    inp = _minimal_input()
    inp.generation_prompt = "Focus on authentication stories only."
    story_generator.run_story_generator(inp, provider="fake", model="m")

    assert "Focus on authentication stories only." in captured[0]
