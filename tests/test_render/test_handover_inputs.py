"""Renderer-fixture tests for ``alfred.render.handover_inputs``.

Per the Concern X, Slice 6 plan and ``docs/active/HANDOVER_WORKFLOW_DISCUSSION.md``
section D, these tests fixture a known ledger/brief and assert the renderer's
deterministic output rather than prose-level substring properties.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from alfred.ledger.loader import load_ledger
from alfred.ledger.models import Brief, Phase, PhaseLedger, TaskSeed
from alfred.render.handover_inputs import (
    HandoverInputs,
    NoActivePhaseError,
    render_handover_inputs,
    select_active_phase,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_LEDGER_PATH = REPO_ROOT / "docs/active/PHASE_LEDGER.yaml"


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
                previous_handover="ALFRED_HANDOVER_17",
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

    # Goal lead, then hard rules, then task lock-down list, then DoD, then OoS.
    assert first.startswith(
        "Replace hand-edited identity constants in the canonical "
        "handover generator with a deterministic renderer over "
        "PhaseLedger + active Brief."
    )
    assert "Hard rules (protocol invariants — do not relax):" in first
    assert "- Renderer must be deterministic (no LLM, no network)." in first
    assert "- Preserve Slice 5 ContextBundle seam." in first
    assert "This phase must lock down:" in first
    assert "- 1. Add the renderer surface: " in first
    assert "- 2. Wire the generator to the renderer: " in first
    assert "Out of scope:" in first
    assert "- Slice 7+ validator-chain expansion." in first

    # Hard rules block must precede the task block.
    assert first.index("Hard rules") < first.index("This phase must lock down:")


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
                previous_handover="ALFRED_HANDOVER_1",
                brief=None,
            ),
        ],
    )
    with pytest.raises(NoActivePhaseError):
        render_handover_inputs(ledger)


def test_render_handover_inputs_rejects_title_mismatch_between_phase_and_brief():
    """``DISPLAY_TITLE`` has one source of truth: enforced phase/brief equality.

    The renderer reads ``brief.title``, but ``phase.title`` and
    ``brief.title`` must agree so neither field can drift silently.
    """
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
                title="Phase title written one way",
                status="planning",
                handover_id="ALFRED_HANDOVER_2",
                previous_handover="ALFRED_HANDOVER_1",
                brief=Brief(
                    title="Brief title written a different way",
                    goal="goal",
                ),
            ),
        ],
    )
    with pytest.raises(NoActivePhaseError, match="title mismatch"):
        render_handover_inputs(ledger)


def test_render_handover_inputs_accepts_matching_phase_and_brief_titles():
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
                title="Matched title",
                status="planning",
                handover_id="ALFRED_HANDOVER_2",
                previous_handover="ALFRED_HANDOVER_1",
                brief=Brief(title="Matched title", goal="goal"),
            ),
        ],
    )
    inputs = render_handover_inputs(ledger)
    assert inputs.display_title == "Matched title"


def test_real_ledger_loads_and_active_phase_selection_is_deterministic():
    """The seeded planning row in the real ledger must drive the renderer."""
    ledger = load_ledger(REAL_LEDGER_PATH)
    active = select_active_phase(ledger)
    assert active.status == "planning"
    assert active.handover_id == "ALFRED_HANDOVER_20"
    assert active.brief is not None
    assert active.brief.hard_rules, "Slice 8 brief must declare hard rules"
    assert any(
        task.id == "1" for task in active.brief.tasks
    ), "Slice 8 brief must declare ordered task seeds"

    # Calling render twice must be byte-identical: the renderer is pure.
    inputs_a = render_handover_inputs(ledger)
    inputs_b = render_handover_inputs(ledger)
    assert inputs_a == inputs_b
    assert inputs_a.handover_id == "ALFRED_HANDOVER_20"
    assert active.previous_handover == "ALFRED_HANDOVER_19"
    assert inputs_a.previous_handover == "ALFRED_HANDOVER_19"
    assert inputs_a.argparse_defaults.source_default == (
        "docs/canonical/ALFRED_HANDOVER_19.md"
    )
    assert "Hard rules" in inputs_a.sprint_goal


def test_render_handover_inputs_requires_explicit_previous_handover():
    """Renderer refuses to infer continuity from phase-id ordering."""
    ledger = PhaseLedger(
        project="x",
        phases=[
            Phase(
                id=1,
                title="Prior",
                status="ratified",
                handover_id="ALFRED_HANDOVER_99",
            ),
            Phase(
                id=2,
                title="Active",
                status="planning",
                handover_id="ALFRED_HANDOVER_100",
                # previous_handover deliberately omitted
                brief=Brief(title="Active", goal="goal"),
            ),
        ],
    )
    with pytest.raises(NoActivePhaseError, match="previous_handover"):
        render_handover_inputs(ledger)


def test_render_handover_inputs_uses_explicit_previous_handover_not_phase_order():
    """``previous_handover`` is explicit; ledger-row order must not override it."""
    ledger = PhaseLedger(
        project="x",
        phases=[
            Phase(
                id=5,
                title="Most recent ratified by id",
                status="ratified",
                handover_id="ALFRED_HANDOVER_50",
            ),
            Phase(
                id=6,
                title="Active",
                status="planning",
                handover_id="ALFRED_HANDOVER_51",
                # Cross-track continuity: planning row points at a different
                # ratified handover than the highest-id ratified phase.
                previous_handover="ALFRED_HANDOVER_42",
                brief=Brief(title="Active", goal="goal"),
            ),
        ],
    )
    inputs = render_handover_inputs(ledger)
    assert inputs.previous_handover == "ALFRED_HANDOVER_42"
    assert inputs.argparse_defaults.source_default == (
        "docs/canonical/ALFRED_HANDOVER_42.md"
    )
