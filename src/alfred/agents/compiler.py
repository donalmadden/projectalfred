"""
Compiler — extracts a structured HandoverDocument from an approved prose draft.

Methodology property: the human approves prose; the compiler fires only after
approval (via POST /compile). It never runs as part of POST /generate.

The compiler makes one focused LLM call: extract structure from prose.
It does not invent tasks, checkpoints, or content absent from the draft.
"""
from __future__ import annotations

from typing import Optional

from alfred.schemas.agent import CompilerInput, CompilerOutput
from alfred.tools import llm


def _build_prompt(input: CompilerInput) -> str:
    from alfred.schemas.handover import HandoverDocument

    schema_json = HandoverDocument.model_json_schema()

    return (
        "You are the Compiler agent. Your sole job is to extract structure from an "
        "already-approved prose handover document.\n\n"
        "RULES:\n"
        "1. Extract only what is explicitly present in the draft. Do NOT invent tasks, "
        "checkpoints, goals, or any content not in the source text.\n"
        "2. Every HandoverTask must have a non-empty id, title, and goal.\n"
        "3. If the draft has no tasks, return an empty tasks list — the caller treats "
        "this as a compilation failure.\n"
        "4. Add a compilation warning (in compilation_warnings) for each task that has "
        "no checkpoint defined.\n"
        "5. Preserve the author and handover_id as provided.\n\n"
        f"HANDOVER SCHEMA (for reference):\n{schema_json}\n\n"
        f"AUTHOR: {input.author}\n"
        f"HANDOVER ID: {input.handover_id}\n\n"
        "DRAFT MARKDOWN TO COMPILE:\n"
        "---\n"
        f"{input.draft_handover_markdown}\n"
        "---\n\n"
        "Produce a CompilerOutput with:\n"
        "- handover: a fully populated HandoverDocument extracted from the draft above\n"
        "- compilation_warnings: list of warning strings (e.g. tasks with no checkpoint)\n"
        "The handover.id must equal the provided HANDOVER ID. "
        "The handover.author must equal the provided AUTHOR."
    )


def run_compiler(
    input: CompilerInput,
    *,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
    db_path: Optional[str] = None,
) -> CompilerOutput:
    """Extract a structured HandoverDocument from an approved prose draft."""
    prompt = _build_prompt(input)
    result = llm.complete(
        prompt,
        CompilerOutput,
        provider=provider,
        model=model,
        db_path=db_path,
    )
    if not result.handover.tasks:
        raise ValueError(
            f"Compiler produced no tasks from draft for handover '{input.handover_id}'. "
            "The draft may not contain any parseable task sections."
        )
    return result
