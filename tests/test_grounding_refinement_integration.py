"""Integration coverage for grounding refinement wiring."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from alfred.agents import planner
from alfred.orchestrator import _run_deterministic_validators
from alfred.schemas.agent import BoardState, PlannerInput

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_alfred_planning_facts import (  # noqa: E402
    ClaimCategory,
    validate_current_state_facts,
    validate_future_task_realism,
)


def _planner_input() -> PlannerInput:
    return PlannerInput(
        board_state=BoardState(
            sprint_number=7,
            sprint_start=date(2026, 4, 21),
            sprint_end=date(2026, 5, 5),
        )
    )


def test_end_to_end_typed_taxonomy_to_planner_to_validator() -> None:
    prompt = planner._build_prompt(_planner_input())
    findings = validate_current_state_facts(
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_7_DRAFT\n"
        "**date:** 2026-04-21\n"
        "**previous_handover:** ALFRED_HANDOVER_6\n\n"
        "## WHAT EXISTS TODAY\n"
        "The repo ships `src/alfred/state/`.\n"
    )

    assert "CLAIM TAXONOMY & PLACEMENT RULES" in prompt
    assert findings
    assert findings[0].category == ClaimCategory.CURRENT_PATH
    assert findings[0].finding_object.finding_type == "path"


def test_planner_prompt_contains_repo_growth_and_partial_state_constraints() -> None:
    prompt = planner._build_prompt(_planner_input())
    assert "REPO GROWTH CONVENTIONS" in prompt
    assert "PARTIAL-STATE FACTS" in prompt
    assert ".github/workflows/" in prompt
    assert "declared but unimplemented" in prompt


def test_validator_catches_placement_violations_with_typed_findings() -> None:
    findings = validate_future_task_realism(
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_7_DRAFT\n"
        "**date:** 2026-04-21\n"
        "**previous_handover:** ALFRED_HANDOVER_6\n\n"
        "## WHAT EXISTS TODAY\n"
        "FastAPI lives in `src/alfred/api.py`.\n\n"
        "## TASK OVERVIEW\n"
        "### Task 1 — Add release workflow\n"
        "Create `ci/release.yml`.\n"
        "Tests: validate YAML.\n"
    )
    assert findings
    assert findings[0].category == ClaimCategory.PLACEMENT
    assert findings[0].finding_object.finding_type == "placement"


def test_orchestrator_validator_pipeline_returns_typed_findings() -> None:
    findings, has_errors = _run_deterministic_validators(
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_7_DRAFT\n"
        "**date:** 2026-04-21\n"
        "**previous_handover:** ALFRED_HANDOVER_6\n\n"
        "## WHAT EXISTS TODAY\n"
        "The repo ships `src/alfred/state/`.\n",
        warnings_visible=True,
    )
    assert has_errors is True
    assert findings
    assert findings[0].category == ClaimCategory.CURRENT_PATH
    assert hasattr(findings[0], "finding_object")
