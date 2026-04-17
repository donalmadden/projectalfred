"""Tests for the Retro Analyst agent."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from alfred.agents import retro_analyst
from alfred.schemas.agent import (
    MetricsHistory,
    RAGChunk,
    RetroAnalystInput,
    RetroAnalystOutput,
    VelocityRecord,
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


_VALID_OUTPUT: dict[str, Any] = {
    "pattern_report": [
        {
            "pattern_type": "failure",
            "description": "Late integration testing causes last-minute failures.",
            "frequency": 3,
            "example_handover_ids": ["handover_5", "handover_7"],
            "recommendation": "Shift integration tests earlier in the sprint.",
        }
    ],
    "velocity_trend": None,
    "retrospective_summary": "Sprint 5 showed stable velocity with one late integration failure.",
    "handovers_analysed": 3,
    "top_risks": ["Late integration", "Scope creep"],
    "top_successes": ["Consistent deployment pipeline"],
}


def _install_fake(response: dict[str, Any] | None = None) -> list[str]:
    captured: list[str] = []
    resp = response or _VALID_OUTPUT

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return resp, 0

    llm._PROVIDERS["fake"] = fake
    return captured


def _velocity(sprint: int, committed: int, completed: int) -> VelocityRecord:
    return VelocityRecord(
        sprint_number=sprint,
        points_committed=committed,
        points_completed=completed,
        completion_rate=completed / committed,
    )


# ---------------------------------------------------------------------------
# Return type and schema conformance
# ---------------------------------------------------------------------------


def test_returns_retro_analyst_output() -> None:
    _install_fake()
    inp = RetroAnalystInput()
    out = retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert isinstance(out, RetroAnalystOutput)


def test_pattern_report_populated() -> None:
    _install_fake()
    inp = RetroAnalystInput()
    out = retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert len(out.pattern_report) == 1
    assert out.pattern_report[0].pattern_type == "failure"


def test_top_risks_and_successes_populated() -> None:
    _install_fake()
    inp = RetroAnalystInput()
    out = retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert "Late integration" in out.top_risks
    assert "Consistent deployment pipeline" in out.top_successes


# ---------------------------------------------------------------------------
# Velocity trend — deterministic computation
# ---------------------------------------------------------------------------


def test_velocity_trend_stable() -> None:
    _install_fake()
    inp = RetroAnalystInput(
        velocity_data=[
            _velocity(1, 20, 18),
            _velocity(2, 20, 19),
            _velocity(3, 20, 17),
        ]
    )
    out = retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert out.velocity_trend is not None
    assert out.velocity_trend.sprints_analysed == 3
    assert out.velocity_trend.trend_direction == "stable"


def test_velocity_trend_improving() -> None:
    _install_fake()
    inp = RetroAnalystInput(
        velocity_data=[
            _velocity(1, 20, 10),  # 50%
            _velocity(2, 20, 12),
            _velocity(3, 20, 18),  # 90%
            _velocity(4, 20, 19),
        ]
    )
    out = retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert out.velocity_trend.trend_direction == "improving"


def test_velocity_trend_declining() -> None:
    _install_fake()
    inp = RetroAnalystInput(
        velocity_data=[
            _velocity(1, 20, 19),
            _velocity(2, 20, 18),
            _velocity(3, 20, 10),
            _velocity(4, 20, 9),
        ]
    )
    out = retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert out.velocity_trend.trend_direction == "declining"


def test_velocity_trend_insufficient_data_when_empty() -> None:
    _install_fake()
    inp = RetroAnalystInput()
    out = retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert out.velocity_trend.trend_direction == "insufficient_data"
    assert out.velocity_trend.sprints_analysed == 0


def test_velocity_trend_overrides_llm_trend() -> None:
    """Trend is computed deterministically; LLM value in velocity_trend field is ignored."""
    resp = {
        **_VALID_OUTPUT,
        "velocity_trend": {
            "average_completion_rate": 0.99,
            "trend_direction": "improving",
            "sprints_analysed": 99,
        },
    }
    _install_fake(resp)
    inp = RetroAnalystInput(velocity_data=[_velocity(1, 20, 10)])
    out = retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert out.velocity_trend.sprints_analysed == 1  # our computation, not LLM's 99


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def test_prompt_includes_velocity_data() -> None:
    captured = _install_fake()
    inp = RetroAnalystInput(velocity_data=[_velocity(3, 20, 17)])
    retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert "Sprint 3" in captured[0]
    assert "17/20" in captured[0]


def test_prompt_includes_rag_chunks() -> None:
    captured = _install_fake()
    inp = RetroAnalystInput(
        handover_corpus_chunks=[
            RAGChunk(
                document_id="handover_9",
                section_header="Post-Mortem",
                content="Deployment failed due to missing env var.",
                relevance_score=0.88,
            )
        ]
    )
    retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert "handover_9" in captured[0]
    assert "missing env var" in captured[0]


def test_prompt_includes_analysis_focus() -> None:
    captured = _install_fake()
    inp = RetroAnalystInput(analysis_focus="Focus on deployment failures only.")
    retro_analyst.run_retro_analyst(inp, provider="fake", model="m")
    assert "Focus on deployment failures only." in captured[0]


# ---------------------------------------------------------------------------
# No write-path imports
# ---------------------------------------------------------------------------


def test_no_write_tools_called() -> None:
    """Retro Analyst must not call persistence writes or github_api."""
    _install_fake()
    inp = RetroAnalystInput(velocity_data=[_velocity(1, 20, 18)])

    with patch("alfred.tools.persistence.record_velocity") as mock_rv, \
         patch("alfred.tools.persistence.record_agent_invocation") as mock_rai, \
         patch("alfred.tools.github_api.create_story") as mock_cs:

        retro_analyst.run_retro_analyst(inp, provider="fake", model="m")

        mock_rv.assert_not_called()
        mock_cs.assert_not_called()
        # record_agent_invocation is only called when db_path is set; here it's None
        mock_rai.assert_not_called()
