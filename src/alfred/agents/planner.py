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

from pathlib import Path
from typing import Optional

from alfred.schemas.agent import PlannerInput, PlannerOutput
from alfred.tools import llm

# Repo root is resolved from this file's location so the template path in
# config (relative to the repo root) works from any CWD.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def load_canonical_template(template_path: str) -> Optional[str]:
    """Read the Alfred canonical scaffold markdown from ``template_path``.

    Returns ``None`` if the path is empty or the file cannot be read. The
    path is resolved against the current working directory first and then
    against the repo root, so CLI scripts, the FastAPI server, and tests
    all see consistent behaviour.
    """
    if not template_path:
        return None
    candidates = [Path(template_path)]
    if not Path(template_path).is_absolute():
        candidates.append(_REPO_ROOT / template_path)
    for candidate in candidates:
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8")
            except OSError:
                continue
    return None


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

    if input.repo_facts_summary:
        facts_block = "\n".join(f"  - {line}" for line in input.repo_facts_summary)
        parts.append(
            "REPOSITORY FACTS (authoritative current state — DO NOT CONTRADICT):\n"
            "The bullets below are derived by direct inspection of the workspace.\n"
            "They are the ground truth for any `## WHAT EXISTS TODAY` claim. Rules:\n"
            "  - Present-tense claims about modules, agents, endpoints, tooling, or\n"
            "    packaging MUST match these facts verbatim.\n"
            "  - If a file, package, or module is NOT listed below, do NOT claim it\n"
            "    exists today. Put it in a future-tense section instead (e.g.\n"
            "    `## WHAT THIS PHASE PRODUCES` or a TASK description).\n"
            "  - Do NOT rename agents, tool modules, or packages. The names in the\n"
            "    facts block are the real names.\n"
            "  - Do NOT claim `mypy` is in use unless the facts block says so. The\n"
            "    repository uses `pyright`.\n"
            "  - Do NOT claim `pyproject.toml` lacks packaging metadata when the facts\n"
            "    block shows `[project]=True`. Distinguish existing-but-incomplete\n"
            "    from missing.\n"
            "  - Do NOT claim the FastAPI app lives anywhere other than the\n"
            "    `FastAPI module path` given below.\n\n"
            "THREE-STATE VOCABULARY (use these exact phrases):\n"
            "  When describing any file, module, or workflow, you MUST use one of:\n"
            "  • `exists today` — a concrete file/module visible in the workspace right now.\n"
            "  • `declared but unimplemented` — referenced in pyproject.toml or config\n"
            "    but the implementation file is absent (e.g. CLI entry declared, no cli.py).\n"
            "  • `to be created in this phase` — proposed by this plan; does not exist yet.\n"
            "  Never collapse 'declared but unimplemented' into either 'exists' or 'missing'.\n"
            "  Any `Partial state:` bullet in the facts below identifies declared-but-absent items.\n\n"
            f"{facts_block}"
        )

    identity_lines: list[str] = []
    if input.generation_date:
        identity_lines.append(f"  - Today's date: {input.generation_date}")
    if input.expected_handover_id:
        identity_lines.append(f"  - Expected draft id (use verbatim): {input.expected_handover_id}")
    if input.expected_previous_handover:
        identity_lines.append(
            f"  - Expected previous_handover (use verbatim): {input.expected_previous_handover}"
        )
    if identity_lines:
        parts.append(
            "GENERATION METADATA (use verbatim in the `## CONTEXT — READ THIS FIRST`\n"
            "metadata block — do NOT infer these values from RAG context):\n"
            + "\n".join(identity_lines)
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

    if input.prior_critique:
        last = input.prior_critique[-1]
        issues_text = "\n".join(f"  - {issue}" for issue in last.validation_issues)
        parts.append(
            f"PRIOR CRITIQUE (iteration {last.iteration}, score {last.quality_score:.2f}):\n"
            "The previous draft was reviewed and found the following issues to address:\n"
            f"{issues_text}\n"
            "Please revise the draft to address these issues."
        )

    if input.deterministic_findings:
        findings_block = "\n".join(f"  - {f}" for f in input.deterministic_findings)
        parts.append(
            "DETERMINISTIC VALIDATOR FINDINGS:\n"
            "Each finding below is a deterministic, non-negotiable failure. You MUST\n"
            "address every ERROR-severity finding before this draft can be promoted.\n"
            "WARNINGs are advisory but should be considered.\n\n"
            f"{findings_block}"
        )

    if input.git_history_summary:
        history_block = "\n".join(input.git_history_summary)
        parts.append(
            "GIT HISTORY (real repository state — use verbatim under ### Git History):\n"
            "The commits below are the authoritative recent history of this repository.\n"
            "You MUST render them verbatim inside the `### Git History` section of your\n"
            "draft. Do NOT add, remove, or alter any commit hash or message. Do NOT\n"
            "invent commits that are not listed here.\n\n"
            "```\n"
            f"{history_block}\n"
            "```"
        )

    if input.canonical_template:
        git_history_instruction = (
            "  - `## WHAT EXISTS TODAY` (must contain a `### Git History` subsection\n"
            "    populated with the GIT HISTORY block supplied above)"
            if input.git_history_summary
            else
            "  - `## WHAT EXISTS TODAY` (must contain a `### Git History` subsection;\n"
            "    do NOT fabricate history — leave a `TBD — git log to be injected` marker)"
        )
        parts.append(
            "CANONICAL OUTPUT SCAFFOLD (Alfred house style — NON-NEGOTIABLE):\n"
            "Your draft MUST preserve every `##` and `###` heading from the scaffold\n"
            "below, verbatim and in the same order. Content under each heading is\n"
            "yours to write; the headings themselves are contracts checked by the\n"
            "promotion validator. The following sections are REQUIRED:\n"
            "  - `## CONTEXT — READ THIS FIRST`\n"
            f"{git_history_instruction}\n"
            "  - `## HARD RULES`\n"
            "  - `## TASK OVERVIEW`\n"
            "  - `## WHAT NOT TO DO`\n"
            "  - `## POST-MORTEM`\n\n"
            "---SCAFFOLD BEGIN---\n"
            f"{input.canonical_template}\n"
            "---SCAFFOLD END---"
        )

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
