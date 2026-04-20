"""T1.4 — PlannerOutput invariants.

Property: PlannerOutput produced by run_planner() must always contain a
non-empty draft_handover_markdown string. Two angles:

1. Schema invariant — draft_handover_markdown survives round-trip serialisation
   with its value intact (no silent truncation or coercion).
2. Agent invariant — run_planner() with a mock LLM that returns a non-empty
   string always delivers that string in the output; the agent does not
   silently discard or replace it.
"""
from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from alfred.schemas.agent import BoardState, PlannerInput, PlannerOutput
from alfred.tools import llm

_text = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    min_size=1,
    max_size=500,
)

# ---------------------------------------------------------------------------
# T1.4a — Schema invariant
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(_text)
def test_planner_output_draft_markdown_preserved_through_roundtrip(markdown: str) -> None:
    """draft_handover_markdown is preserved exactly through JSON serialisation."""
    output = PlannerOutput(
        draft_handover_markdown=markdown,
        task_decomposition=[],
        open_questions=[],
    )
    assert output.draft_handover_markdown == markdown
    restored = PlannerOutput.model_validate(output.model_dump(mode="json"))
    assert restored.draft_handover_markdown == markdown


@settings(max_examples=100)
@given(_text)
def test_planner_output_draft_markdown_is_always_a_str(markdown: str) -> None:
    """draft_handover_markdown field is always str (never None or other type)."""
    output = PlannerOutput(
        draft_handover_markdown=markdown,
        task_decomposition=[],
        open_questions=[],
    )
    assert isinstance(output.draft_handover_markdown, str)
    assert len(output.draft_handover_markdown) > 0


# ---------------------------------------------------------------------------
# T1.4b — Agent invariant: run_planner preserves the LLM's draft
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(_text)
def test_run_planner_preserves_non_empty_draft_markdown(markdown: str) -> None:
    """run_planner() passes the LLM's draft_handover_markdown through unchanged."""
    from alfred.agents.planner import run_planner

    original = dict(llm._PROVIDERS)

    def mock_provider(
        prompt: str, output_schema: Any, model: str
    ) -> tuple[dict[str, Any], int]:
        return {
            "draft_handover_markdown": markdown,
            "task_decomposition": [],
            "open_questions": [],
        }, 0

    llm._PROVIDERS["mock"] = mock_provider
    try:
        planner_input = PlannerInput(
            board_state=BoardState(stories=[]),
            velocity_history=[],
            prior_handover_summaries=[],
            git_history_summary=[],
        )
        result = run_planner(planner_input, provider="mock", model="m")
        assert isinstance(result.draft_handover_markdown, str)
        assert len(result.draft_handover_markdown) > 0
        assert result.draft_handover_markdown == markdown
    finally:
        llm._PROVIDERS.clear()
        llm._PROVIDERS.update(original)
