"""
Planner — reads board and corpus context, produces draft handovers and sprint plans.

Methodology property 3 (reasoning/execution isolation): the Planner is on the
reasoning side. It never executes tasks, never modifies the board, never writes
code. It produces DRAFTS; a human must approve before any draft becomes protocol
(methodology property: Alfred drafts, humans approve).

The prompt structure references all five methodology properties so the LLM
output is grounded in them. Schema validation and retry are delegated entirely
to llm.complete — this agent does not re-implement that logic.
"""
from __future__ import annotations

from typing import Optional

from alfred.schemas.agent import PlannerInput, PlannerOutput
from alfred.tools import llm


def _build_prompt(input: PlannerInput) -> str:
    parts: list[str] = []

    parts.append(
        "You are the Planner agent in a document-mediated, checkpoint-gated "
        "coordination system. Your role is REASONING ONLY — you produce drafts "
        "for human approval. You never execute tasks, modify the board, or write code.\n\n"
        "METHODOLOGY PROPERTIES (your output must respect all five):\n"
        "1. Document as protocol — the handover document is the control surface.\n"
        "2. Checkpoint-gated execution — deterministic decision tables at defined gates.\n"
        "3. Reasoning/execution isolation — you are the reasoning side; never execute.\n"
        "4. Inline post-mortem → forward plan — failure analysis lives in the artifact.\n"
        "5. Statelessness by design — each session cold-starts from the document.\n"
    )

    board = input.board_state
    sprint_label = f"Sprint {board.sprint_number}" if board.sprint_number else "current sprint"
    stories_block = ""
    if board.stories:
        lines = []
        for s in board.stories:
            pts = f" [{s.story_points}pts]" if s.story_points else ""
            lines.append(f"  - [{s.status}]{pts} {s.title}")
        stories_block = "\n".join(lines)
    else:
        stories_block = "  (no stories)"

    parts.append(
        f"BOARD STATE ({sprint_label}):\n"
        f"  Sprint dates: {board.sprint_start} – {board.sprint_end}\n"
        f"  Last sprint velocity: {board.velocity_last_sprint}\n"
        f"Stories:\n{stories_block}"
    )

    if input.velocity_history:
        rows = []
        for v in input.velocity_history[-5:]:
            rows.append(
                f"  Sprint {v.sprint_number}: {v.points_completed}/{v.points_committed} "
                f"({v.completion_rate:.0%})"
            )
        parts.append("VELOCITY HISTORY (last 5 sprints):\n" + "\n".join(rows))

    if input.prior_handover_summaries:
        chunks = []
        for c in input.prior_handover_summaries[:5]:
            chunks.append(f"  [{c.document_id} / {c.section_header}]\n  {c.content[:300]}")
        parts.append("PRIOR HANDOVER CONTEXT (top RAG hits):\n" + "\n\n".join(chunks))

    if input.current_handover_context:
        parts.append(f"CURRENT HANDOVER CONTEXT:\n{input.current_handover_context}")

    if input.sprint_goal:
        parts.append(f"SPRINT GOAL:\n{input.sprint_goal}")

    parts.append(
        "TASK:\n"
        "Produce a draft handover document in markdown. Include:\n"
        "- Sprint context and goals\n"
        "- Task decomposition with clear acceptance criteria\n"
        "- At least one checkpoint with a decision table\n"
        "- Open questions requiring human judgment\n"
        "This is a DRAFT — a human will review and approve before it becomes protocol.\n"
        "Also produce an optional sprint plan with capacity estimate and story selection rationale."
    )

    return "\n\n".join(parts)


def run_planner(
    input: PlannerInput,
    *,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
    db_path: Optional[str] = None,
) -> PlannerOutput:
    """Produce a draft handover and optional sprint plan. Drafts only — never writes to the board."""
    prompt = _build_prompt(input)
    return llm.complete(
        prompt,
        PlannerOutput,
        provider=provider,
        model=model,
        db_path=db_path,
    )
