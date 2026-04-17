"""
Story Generator — produces validated draft stories from the handover corpus.

Methodology property 2 (checkpoint-gated execution): stories cannot be written
to the board from here. The output is a DRAFT; the orchestrator applies a HITL
approval gate before create_story is called.

Rubric validation is deterministic — stories that fail the rubric are recorded
in `stories_failing_rubric` rather than silently dropped. The LLM call produces
candidate stories; this module validates them, never re-orders or alters them.
"""
from __future__ import annotations

from typing import Optional

from alfred.schemas.agent import (
    QualityRubric,
    Story,
    StoryGeneratorInput,
    StoryGeneratorOutput,
)
from alfred.tools import llm


def _build_prompt(input: StoryGeneratorInput) -> str:
    parts: list[str] = []

    parts.append(
        "You are the Story Generator agent. Produce well-formed draft user stories "
        "grounded in the handover corpus. Stories are DRAFTS — a human approves "
        "before any story reaches the board (checkpoint-gated execution).\n\n"
        "Each story must have:\n"
        "- A concise title\n"
        "- A clear description\n"
        "- Acceptance criteria (at least the minimum required by the rubric)\n"
        "- Story points from the Fibonacci set: 1, 2, 3, 5, 8, or 13\n"
    )

    rubric = input.quality_rubric
    criteria_block = "\n".join(f"  - {c}" for c in rubric.criteria)
    parts.append(
        f"QUALITY RUBRIC:\n"
        f"  Minimum acceptance criteria per story: {rubric.minimum_acceptance_criteria_count}\n"
        f"  Story points required: {rubric.require_story_points}\n"
        f"  Criteria to satisfy:\n{criteria_block}"
    )

    board = input.board_state
    if board.stories:
        existing = "\n".join(f"  - [{s.status}] {s.title}" for s in board.stories)
        sprint_label = f"Sprint {board.sprint_number}" if board.sprint_number else "current sprint"
        parts.append(f"EXISTING BOARD STORIES ({sprint_label}):\n{existing}")

    if input.handover_corpus_chunks:
        chunks = []
        for c in input.handover_corpus_chunks[:5]:
            chunks.append(f"  [{c.document_id} / {c.section_header}]\n  {c.content[:300]}")
        parts.append("HANDOVER CORPUS CONTEXT (top RAG hits):\n\n" + "\n\n".join(chunks))

    if input.generation_prompt:
        parts.append(f"GENERATION INSTRUCTIONS:\n{input.generation_prompt}")

    parts.append(
        "TASK: Generate stories. For each story set `quality_score` (0.0–1.0) and "
        "`quality_notes` explaining how it satisfies the rubric. Set `rubric_applied` "
        "to a one-sentence summary of the rubric used."
    )

    return "\n\n".join(parts)


def _apply_rubric(story: Story, rubric: QualityRubric) -> Optional[str]:
    """Return a failure reason string, or None if the story passes."""
    if len(story.acceptance_criteria) < rubric.minimum_acceptance_criteria_count:
        return (
            f"Too few acceptance criteria: "
            f"{len(story.acceptance_criteria)} < {rubric.minimum_acceptance_criteria_count}"
        )
    if rubric.require_story_points and story.story_points is None:
        return "Missing story points"
    return None


def run_story_generator(
    input: StoryGeneratorInput,
    *,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
    db_path: Optional[str] = None,
) -> StoryGeneratorOutput:
    """Generate rubric-validated draft stories. Never writes to the board directly."""
    prompt = _build_prompt(input)
    raw: StoryGeneratorOutput = llm.complete(
        prompt,
        StoryGeneratorOutput,
        provider=provider,
        model=model,
        db_path=db_path,
    )

    passing: list[Story] = []
    failing: list[str] = list(raw.stories_failing_rubric)

    for story in raw.stories:
        reason = _apply_rubric(story, input.quality_rubric)
        if reason is None:
            passing.append(story)
        else:
            failing.append(f"{story.title}: {reason}")

    return StoryGeneratorOutput(
        stories=passing,
        rubric_applied=raw.rubric_applied,
        stories_failing_rubric=failing,
    )
