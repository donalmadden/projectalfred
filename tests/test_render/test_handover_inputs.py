"""Renderer-fixture tests for ``alfred.render.handover_inputs``.

Per the Concern X, Slice 6 plan and ``docs/active/HANDOVER_WORKFLOW_DISCUSSION.md``
section D, these tests fixture a known ledger/brief and assert the renderer's
deterministic output rather than prose-level substring properties.
"""
from __future__ import annotations

import pytest

from alfred.ledger.models import Brief, Phase, PhaseLedger, TaskSeed
from alfred.render.handover_inputs import (
    HandoverInputs,
    NoActivePhaseError,
    render_handover_inputs,
    select_active_phase,
)


def _fixture_ledger() -> PhaseLedger:
    return PhaseLedger(
        project="alfred_seam_discipline",
        plan_path="docs/active/POST_GRILL_1.md",
        phases=[
            Phase(
                id=4,
                title="Slice 4 — Doc-class contracts",
                status="ratified",
                handover_id="ALFRED_HANDOVER_16",
                scope_sources=["docs/active/SLICE_4_SCOPE.md"],
            ),
            Phase(
                id=5,
                title="Slice 5 — Typed three-role context bundle",
                status="ratified",
                handover_id="ALFRED_HANDOVER_17",
                scope_carry_forward=[4],
            ),
            Phase(
                id=6,
                title="Slice 6 — Renderer Replaces Hand-Edited Identity Constants",
                status="planning",
                handover_id="ALFRED_HANDOVER_18",
                scope_sources=["docs/active/POST_GRILL_1.md"],
                scope_carry_forward=[5],
                brief=Brief(
                    title="Slice 6 — Renderer Replaces Hand-Edited Identity Constants",
                    goal=(
                        "Replace hand-edited identity constants in the canonical "
                        "handover generator with a deterministic renderer over "
                        "PhaseLedger + active Brief."
                    ),
                    hard_rules=[
                        "Renderer must be deterministic (no LLM, no network).",
                        "Preserve Slice 5 ContextBundle seam.",
                    ],
                    tasks=[
                        TaskSeed(
                            id="1",
                            title="Add the renderer surface",
                            intent=(
                                "Create src/alfred/render/handover_inputs.py "
                                "and unit tests."
                            ),
                        ),
                        TaskSeed(
                            id="2",
                            title="Wire the generator to the renderer",
                            intent="Remove hand-edited constants from the script.",
                        ),
                    ],
                    out_of_scope=[
                        "Slice 7+ validator-chain expansion.",
                        "Failed-candidate filename logic.",
                    ],
                    definition_of_done=[
                        "Generator script contains no hand-edited identity literals.",
                    ],
                    followups_from_prior_phase=[],
                ),
            ),
        ],
    )


def test_select_active_phase_picks_the_planning_phase():
    ledger = _fixture_ledger()
    active = select_active_phase(ledger)
    assert active.id == 6
    assert active.handover_id == "ALFRED_HANDOVER_18"


def test_select_active_phase_errors_when_no_planning_phase():
    ledger = PhaseLedger(
        project="x",
        phases=[
            Phase(
                id=0,
                title="Done",
                status="ratified",
                handover_id="ALFRED_HANDOVER_1",
            ),
        ],
    )
    with pytest.raises(NoActivePhaseError):
        select_active_phase(ledger)


def test_select_active_phase_errors_on_multiple_planning_phases():
    ledger = PhaseLedger(
        project="x",
        phases=[
            Phase(id=1, title="A", status="planning", handover_id="A"),
            Phase(id=2, title="B", status="planning", handover_id="B"),
        ],
    )
    with pytest.raises(NoActivePhaseError):
        select_active_phase(ledger)


def test_render_handover_inputs_returns_frozen_identity():
    ledger = _fixture_ledger()
    inputs = render_handover_inputs(ledger)

    assert isinstance(inputs, HandoverInputs)
    assert inputs.handover_id == "ALFRED_HANDOVER_18"
    assert inputs.previous_handover == "ALFRED_HANDOVER_17"
    assert inputs.display_title == (
        "Slice 6 — Renderer Replaces Hand-Edited Identity Constants"
    )


def test_render_handover_inputs_sprint_goal_is_deterministic():
    ledger = _fixture_ledger()
    first = render_handover_inputs(ledger).sprint_goal
    second = render_handover_inputs(ledger).sprint_goal
    assert first == second

    # Goal lead, then task lock-down list, then DoD, then out-of-scope.
    assert first.startswith(
        "Replace hand-edited identity constants in the canonical "
        "handover generator with a deterministic renderer over "
        "PhaseLedger + active Brief."
    )
    assert "This phase must lock down:" in first
    assert "- 1. Add the renderer surface: " in first
    assert "- 2. Wire the generator to the renderer: " in first
    assert "Out of scope:" in first
    assert "- Slice 7+ validator-chain expansion." in first


def test_render_handover_inputs_demo_plan_grounding_uses_ledger_paths():
    ledger = _fixture_ledger()
    grounding = render_handover_inputs(ledger).demo_plan_grounding

    assert "`docs/active/POST_GRILL_1.md`" in grounding
    assert (
        "`docs/canonical/ALFRED_HANDOVER_17.md`" in grounding
    ), "carry-forward phase 5's handover must be cited"
    assert "deterministic" in grounding


def test_render_handover_inputs_argparse_defaults_match_identity():
    ledger = _fixture_ledger()
    defaults = render_handover_inputs(ledger).argparse_defaults

    assert defaults.source_default == "docs/canonical/ALFRED_HANDOVER_17.md"
    assert defaults.output_default == "docs/canonical/ALFRED_HANDOVER_18.md"
    assert defaults.failed_output_default == (
        "docs/archive/ALFRED_HANDOVER_18_FAILED_CANDIDATE.md"
    )
    assert "ALFRED_HANDOVER_17.md" in defaults.source_help
    assert "ALFRED_HANDOVER_18.md" in defaults.output_help


def test_render_handover_inputs_module_docstring_carries_identity():
    ledger = _fixture_ledger()
    docstring = render_handover_inputs(ledger).module_docstring
    assert "ALFRED_HANDOVER_18" in docstring
    assert "ALFRED_HANDOVER_17" in docstring
    assert "PHASE_LEDGER.yaml" in docstring


def test_render_handover_inputs_requires_a_brief():
    ledger = PhaseLedger(
        project="x",
        phases=[
            Phase(
                id=1,
                title="Prior",
                status="ratified",
                handover_id="ALFRED_HANDOVER_1",
            ),
            Phase(
                id=2,
                title="Active",
                status="planning",
                handover_id="ALFRED_HANDOVER_2",
                brief=None,
            ),
        ],
    )
    with pytest.raises(NoActivePhaseError):
        render_handover_inputs(ledger)


def test_render_handover_inputs_requires_a_prior_ratified_phase():
    ledger = PhaseLedger(
        project="x",
        phases=[
            Phase(
                id=0,
                title="Active",
                status="planning",
                handover_id="ALFRED_HANDOVER_1",
                brief=Brief(title="Active", goal="goal"),
            ),
        ],
    )
    with pytest.raises(NoActivePhaseError):
        render_handover_inputs(ledger)
