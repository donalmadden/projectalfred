"""Tests for the Compiler agent."""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from alfred.agents import compiler
from alfred.schemas.agent import CompilerInput
from alfred.tools import llm


# ---------------------------------------------------------------------------
# Fake LLM provider helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_providers():
    original = dict(llm._PROVIDERS)
    yield
    llm._PROVIDERS.clear()
    llm._PROVIDERS.update(original)


def _make_output(tasks: list[dict], warnings: list[str] = ()) -> dict[str, Any]:
    """Build a minimal CompilerOutput dict the fake LLM returns."""
    return {
        "handover": {
            "schema_version": "1.0",
            "id": "TEST_HANDOVER_1",
            "title": "Test Handover",
            "date": date.today().isoformat(),
            "author": "Alice",
            "context": {"narrative": "Test context.", "what_changes": [], "what_does_not_change": [], "important_notices": []},
            "tasks": tasks,
        },
        "compilation_warnings": list(warnings),
    }


def _make_task(task_id: str, title: str, *, has_checkpoint: bool = True) -> dict[str, Any]:
    checkpoints = []
    if has_checkpoint:
        checkpoints = [{
            "id": f"CHECKPOINT-{task_id}",
            "question": "Does the task pass?",
            "evidence_required": "Test output.",
            "decision_table": {"rules": [], "default_verdict": "stop"},
        }]
    return {
        "id": task_id,
        "title": title,
        "goal": f"Complete {title}.",
        "steps": ["Step 1", "Step 2"],
        "checkpoints": checkpoints,
    }


def _install_fake(response: dict[str, Any]) -> dict[str, int]:
    state = {"calls": 0}

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        state["calls"] += 1
        return response, 20

    llm._PROVIDERS["fake"] = fake
    return state


def _minimal_input(markdown: str = "# Draft\n\n## TASK 1 — Do something\n\nGoal: do it.") -> CompilerInput:
    return CompilerInput(
        draft_handover_markdown=markdown,
        handover_id="TEST_HANDOVER_1",
        author="Alice",
    )


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


def test_compiler_returns_compiler_output_with_two_tasks() -> None:
    """A draft with two tasks compiles to a document with exactly 2 tasks."""
    from alfred.schemas.agent import CompilerOutput

    tasks = [_make_task("1", "First Task"), _make_task("2", "Second Task")]
    _install_fake(_make_output(tasks))

    result = compiler.run_compiler(_minimal_input(), provider="fake", model="m")

    assert isinstance(result, CompilerOutput)
    assert len(result.handover.tasks) == 2
    assert result.handover.tasks[0].title == "First Task"
    assert result.handover.tasks[1].title == "Second Task"


def test_compiler_surfaces_warnings_for_tasks_without_checkpoints() -> None:
    """Compilation warnings are returned (not silently dropped) when a task has no checkpoint."""
    tasks = [
        _make_task("1", "Task With Checkpoint", has_checkpoint=True),
        _make_task("2", "Task Without Checkpoint", has_checkpoint=False),
    ]
    warnings = ["Task 2 has no checkpoint defined."]
    _install_fake(_make_output(tasks, warnings))

    result = compiler.run_compiler(_minimal_input(), provider="fake", model="m")

    assert len(result.compilation_warnings) == 1
    assert "Task 2" in result.compilation_warnings[0]


def test_compiler_raises_on_empty_task_list() -> None:
    """An LLM response with no tasks raises ValueError."""
    _install_fake(_make_output(tasks=[]))

    with pytest.raises(ValueError, match="no tasks"):
        compiler.run_compiler(_minimal_input(), provider="fake", model="m")


# ---------------------------------------------------------------------------
# Prompt content
# ---------------------------------------------------------------------------


def test_prompt_includes_draft_markdown() -> None:
    """The draft markdown appears verbatim in the prompt sent to the LLM."""
    captured: list[str] = []
    tasks = [_make_task("1", "Task A")]

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _make_output(tasks), 0

    llm._PROVIDERS["fake"] = fake

    draft = "# My Draft\n\n## TASK 1 — Build the thing\n\nGoal: build it."
    compiler.run_compiler(
        CompilerInput(draft_handover_markdown=draft, handover_id="X_1", author="Bob"),
        provider="fake",
        model="m",
    )

    assert draft in captured[0]
    assert "Bob" in captured[0]
    assert "X_1" in captured[0]


def test_prompt_instructs_extract_only() -> None:
    """The prompt tells the model not to invent content."""
    captured: list[str] = []
    tasks = [_make_task("1", "Task A")]

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _make_output(tasks), 0

    llm._PROVIDERS["fake"] = fake
    compiler.run_compiler(_minimal_input(), provider="fake", model="m")

    assert "Do NOT invent" in captured[0] or "not invent" in captured[0].lower()
