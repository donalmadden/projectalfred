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


# ---------------------------------------------------------------------------
# Canonical scaffold injection (output-hardening task 2)
# ---------------------------------------------------------------------------

_SCAFFOLD_FIXTURE = (
    "# Alfred's Handover Document #<N> — <Title>\n\n"
    "## CONTEXT — READ THIS FIRST\n\n"
    "## WHAT EXISTS TODAY\n\n"
    "### Git History\n\n"
    "## HARD RULES\n\n"
    "## TASK OVERVIEW\n\n"
    "## WHAT NOT TO DO\n\n"
    "## POST-MORTEM\n"
)


def _capture_prompt() -> list[str]:
    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _VALID_OUTPUT, 0

    llm._PROVIDERS["fake"] = fake
    return captured


def test_prompt_injects_scaffold_when_canonical_template_provided() -> None:
    captured = _capture_prompt()
    inp = _minimal_input()
    inp.canonical_template = _SCAFFOLD_FIXTURE
    planner.run_planner(inp, provider="fake", model="m")

    prompt = captured[0]
    assert "SCAFFOLD BEGIN" in prompt
    assert "SCAFFOLD END" in prompt
    assert "### Git History" in prompt
    assert "## WHAT EXISTS TODAY" in prompt


def test_prompt_requires_house_style_headings_when_scaffold_provided() -> None:
    captured = _capture_prompt()
    inp = _minimal_input()
    inp.canonical_template = _SCAFFOLD_FIXTURE
    planner.run_planner(inp, provider="fake", model="m")

    prompt = captured[0]
    # Contract must be explicit — the scaffold alone is not enough.
    assert "NON-NEGOTIABLE" in prompt
    assert "verbatim" in prompt
    assert "## CONTEXT — READ THIS FIRST" in prompt
    assert "## POST-MORTEM" in prompt
    # Fabrication guard (Hard Rule 2 of the output-hardening handover).
    assert "fabricate" in prompt.lower()


def test_prompt_omits_scaffold_block_when_template_not_provided() -> None:
    captured = _capture_prompt()
    planner.run_planner(_minimal_input(), provider="fake", model="m")
    prompt = captured[0]
    assert "SCAFFOLD BEGIN" not in prompt
    assert "NON-NEGOTIABLE" not in prompt


# ---------------------------------------------------------------------------
# load_canonical_template helper
# ---------------------------------------------------------------------------


def test_load_canonical_template_reads_file(tmp_path) -> None:
    path = tmp_path / "scaffold.md"
    path.write_text("## WHAT EXISTS TODAY\n\n### Git History\n", encoding="utf-8")
    content = planner.load_canonical_template(str(path))
    assert content is not None
    assert "### Git History" in content


def test_load_canonical_template_returns_none_for_empty_path() -> None:
    assert planner.load_canonical_template("") is None


def test_load_canonical_template_returns_none_for_missing_file(tmp_path) -> None:
    missing = tmp_path / "does_not_exist.md"
    assert planner.load_canonical_template(str(missing)) is None


def test_load_canonical_template_resolves_repo_relative_default() -> None:
    # The default config ships configs/alfred_handover_template.md in the repo.
    # The helper must find it by relative path regardless of CWD.
    content = planner.load_canonical_template("configs/alfred_handover_template.md")
    assert content is not None
    assert "## CONTEXT — READ THIS FIRST" in content
    assert "### Git History" in content


# ---------------------------------------------------------------------------
# Structured git history input (output-hardening task 3)
# ---------------------------------------------------------------------------

_GIT_HISTORY = [
    "abc1234  output-hardening: task 2 — wire canonical scaffold",
    "def5678  output-hardening: task 1 — add alfred promotion validator",
    "ghi9012  phase5: task 6 — dogfood #2",
]


def test_prompt_includes_supplied_git_history() -> None:
    captured = _capture_prompt()
    inp = _minimal_input()
    inp.git_history_summary = _GIT_HISTORY
    planner.run_planner(inp, provider="fake", model="m")

    prompt = captured[0]
    assert "abc1234" in prompt
    assert "output-hardening: task 2" in prompt
    assert "phase5: task 6" in prompt


def test_prompt_forbids_inventing_git_history_when_supplied() -> None:
    captured = _capture_prompt()
    inp = _minimal_input()
    inp.git_history_summary = _GIT_HISTORY
    planner.run_planner(inp, provider="fake", model="m")

    prompt = captured[0]
    assert "Do NOT" in prompt or "do not" in prompt.lower()
    assert "invent" in prompt.lower() or "fabricat" in prompt.lower()


def test_prompt_labels_history_block() -> None:
    captured = _capture_prompt()
    inp = _minimal_input()
    inp.git_history_summary = _GIT_HISTORY
    planner.run_planner(inp, provider="fake", model="m")

    prompt = captured[0]
    assert "GIT HISTORY" in prompt


def test_prompt_omits_git_history_block_when_not_supplied() -> None:
    captured = _capture_prompt()
    planner.run_planner(_minimal_input(), provider="fake", model="m")
    prompt = captured[0]
    assert "GIT HISTORY" not in prompt


def test_scaffold_instruction_references_git_history_when_both_supplied() -> None:
    captured = _capture_prompt()
    inp = _minimal_input()
    inp.git_history_summary = _GIT_HISTORY
    inp.canonical_template = _SCAFFOLD_FIXTURE
    planner.run_planner(inp, provider="fake", model="m")

    prompt = captured[0]
    # When git history is supplied alongside the scaffold, the prompt should
    # reference the GIT HISTORY block instead of a TBD marker.
    assert "GIT HISTORY block supplied above" in prompt
    assert "TBD" not in prompt


def test_scaffold_instruction_uses_tbd_marker_when_no_git_history() -> None:
    captured = _capture_prompt()
    inp = _minimal_input()
    inp.canonical_template = _SCAFFOLD_FIXTURE
    planner.run_planner(inp, provider="fake", model="m")

    prompt = captured[0]
    assert "TBD" in prompt
