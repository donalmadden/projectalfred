"""Render handover-generator identity inputs from PhaseLedger + active Brief.

The output of :func:`render_handover_inputs` replaces hand-edited constants
inside ``scripts/generate_next_canonical_handover.py``. The rendering is
deterministic: same ledger in, same strings out, no LLM call.

Authority flow (per ``CONTEXT.md``): the ledger is a derived view; the
unratified ``planning`` phase carries the human-authored ``Brief`` that seeds
the next handover. This renderer reads — never mutates — that seed.
"""
from __future__ import annotations

from dataclasses import dataclass

from alfred.ledger.models import Brief, Phase, PhaseLedger


class NoActivePhaseError(ValueError):
    """Raised when the ledger has no phase with ``status == "planning"``."""


@dataclass(frozen=True)
class ArgparseDefaults:
    """Default CLI values derived from the active phase identity."""

    source_default: str
    output_default: str
    failed_output_default: str
    source_help: str
    output_help: str
    failed_output_help: str


@dataclass(frozen=True)
class HandoverInputs:
    """Identity/constants the generator script previously hand-edited."""

    handover_id: str
    previous_handover: str
    display_title: str
    sprint_goal: str
    demo_plan_grounding: str
    module_docstring: str
    argparse_defaults: ArgparseDefaults


def select_active_phase(ledger: PhaseLedger) -> Phase:
    """Return the next phase whose ``status`` is ``planning``.

    Selection is deterministic: the first phase in ledger order that is
    unratified. Multiple planning phases are an authoring error — surface it
    rather than silently picking one.
    """
    planning = [p for p in ledger.phases if p.status == "planning"]
    if not planning:
        raise NoActivePhaseError(
            "Ledger has no phase with status='planning'; "
            "the next handover cannot be rendered."
        )
    if len(planning) > 1:
        ids = ", ".join(str(p.id) for p in planning)
        raise NoActivePhaseError(
            f"Ledger has multiple planning phases (ids: {ids}); "
            "exactly one unratified phase is expected."
        )
    return planning[0]


def _previous_handover_id(active: Phase) -> str:
    """Return the explicit ``previous_handover`` declared on the planning row.

    The ledger is multi-track (the kickoff demo and the Alfred-meta seam-
    discipline work share one file), so phase-id ordering is not a reliable
    way to find the immediately-preceding canonical handover. The planning
    row therefore declares ``previous_handover`` explicitly and the renderer
    refuses to guess.
    """
    if active.previous_handover is None:
        raise NoActivePhaseError(
            f"Active phase {active.id} is missing previous_handover; the "
            "planning row must declare it explicitly so renderer continuity "
            "is deterministic and not inferred from phase-id ordering."
        )
    return active.previous_handover


def _require_brief(active: Phase) -> Brief:
    if active.brief is None:
        raise NoActivePhaseError(
            f"Phase {active.id} (status='planning') is missing a brief; "
            "renderer needs the editorial seed to produce identity inputs."
        )
    if active.brief.title.strip() != active.title.strip():
        raise NoActivePhaseError(
            f"Phase {active.id} title mismatch: phase.title="
            f"{active.title!r} but brief.title={active.brief.title!r}. "
            "The two must agree so the rendered DISPLAY_TITLE has a single "
            "deterministic source of truth."
        )
    return active.brief


def _render_sprint_goal(brief: Brief) -> str:
    parts: list[str] = [brief.goal.strip()]

    if brief.hard_rules:
        parts.append("Hard rules (protocol invariants — do not relax):")
        for rule in brief.hard_rules:
            parts.append(f"- {rule}")

    if brief.tasks:
        parts.append("This phase must lock down:")
        for task in brief.tasks:
            parts.append(f"- {task.id}. {task.title}: {task.intent}")

    if brief.definition_of_done:
        parts.append("Definition of done:")
        for item in brief.definition_of_done:
            parts.append(f"- {item}")

    if brief.out_of_scope:
        parts.append("Out of scope:")
        for item in brief.out_of_scope:
            parts.append(f"- {item}")

    if brief.followups_from_prior_phase:
        parts.append("Follow-ups carried from the prior phase:")
        for item in brief.followups_from_prior_phase:
            parts.append(f"- {item}")

    return "\n\n".join(_group_paragraphs(parts))


def _group_paragraphs(parts: list[str]) -> list[str]:
    """Collapse adjacent bullet lines under their preceding header into one block."""
    blocks: list[str] = []
    buffer: list[str] = []
    for line in parts:
        if line.startswith("- "):
            buffer.append(line)
        else:
            if buffer:
                blocks.append("\n".join(buffer))
                buffer = []
            buffer.append(line)
    if buffer:
        blocks.append("\n".join(buffer))
    return blocks


def _render_demo_plan_grounding(
    ledger: PhaseLedger,
    active: Phase,
) -> str:
    lines: list[str] = []
    lines.append(
        "Authoritative scope sources for this handover "
        "(derived from PhaseLedger + active Brief):"
    )
    if ledger.plan_path:
        lines.append(f"- `{ledger.plan_path}` — plan-of-record for this milestone.")
    for src in active.scope_sources:
        lines.append(f"- `{src}` — phase-specific scope source.")

    carry_phases = [p for p in ledger.phases if p.id in active.scope_carry_forward]
    for phase in carry_phases:
        for src in phase.scope_sources:
            lines.append(
                f"- `{src}` — carried forward from ratified phase {phase.id} "
                f"({phase.title})."
            )
        if phase.handover_id:
            lines.append(
                f"- `docs/canonical/{phase.handover_id}.md` — ratified handover "
                f"for phase {phase.id}."
            )

    lines.append(
        "Treat the contents of those docs as the source of truth for scope. "
        "Do not invent deliverables outside the active brief. Validation is "
        "deterministic; no LLM judgment is invoked at the seams."
    )
    return "\n".join(lines)


def _render_display_title(brief: Brief) -> str:
    return brief.title.strip()


def _render_module_docstring(
    handover_id: str,
    previous_handover: str,
    display_title: str,
) -> str:
    return (
        f"Generate the canonical handover {handover_id} ({display_title}).\n\n"
        f"Inputs are derived deterministically from "
        f"`docs/active/PHASE_LEDGER.yaml` and the active phase's `Brief`. "
        f"The previous ratified handover is {previous_handover}. "
        f"This module performs no editorial judgment; see "
        f"`src/alfred/render/handover_inputs.py` for the renderer surface."
    )


def _render_argparse_defaults(
    handover_id: str,
    previous_handover: str,
) -> ArgparseDefaults:
    source_default = f"docs/canonical/{previous_handover}.md"
    output_default = f"docs/canonical/{handover_id}.md"
    failed_output_default = f"docs/archive/{handover_id}_FAILED_CANDIDATE.md"
    return ArgparseDefaults(
        source_default=source_default,
        output_default=output_default,
        failed_output_default=failed_output_default,
        source_help=(
            "Historical handover to use for continuity "
            f"(default: {source_default})"
        ),
        output_help=(
            "Canonical output path to write on success "
            f"(default: {output_default})"
        ),
        failed_output_help=(
            "Where to write a failed candidate when validation blocks promotion "
            f"(default: {failed_output_default})"
        ),
    )


def render_handover_inputs(ledger: PhaseLedger) -> HandoverInputs:
    """Derive all generator identity/constants from the ledger.

    The single entry point intentionally returns one frozen object so callers
    cannot accidentally split the identity across stale/fresh inputs.
    """
    active = select_active_phase(ledger)
    brief = _require_brief(active)
    if active.handover_id is None:
        raise NoActivePhaseError(
            f"Active phase {active.id} is missing handover_id; the brief "
            "must declare the next handover identity."
        )

    handover_id = active.handover_id
    previous_handover = _previous_handover_id(active)
    display_title = _render_display_title(brief)
    sprint_goal = _render_sprint_goal(brief)
    demo_plan_grounding = _render_demo_plan_grounding(ledger, active)
    module_docstring = _render_module_docstring(
        handover_id, previous_handover, display_title
    )
    argparse_defaults = _render_argparse_defaults(handover_id, previous_handover)

    return HandoverInputs(
        handover_id=handover_id,
        previous_handover=previous_handover,
        display_title=display_title,
        sprint_goal=sprint_goal,
        demo_plan_grounding=demo_plan_grounding,
        module_docstring=module_docstring,
        argparse_defaults=argparse_defaults,
    )
