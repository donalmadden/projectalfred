"""Customer Onboarding Portal kickoff demo execution harness.

Phase 2 deliverable per ``docs/canonical/ALFRED_HANDOVER_9.md`` Task 2. The
harness:

  1. Verifies (or initialises) the demo workspace at ``--workspace``.
  2. Renders the kickoff handover markdown from the frozen charter and
     outline, then persists it to
     ``<workspace>/docs/handovers/ALFRED_HANDOVER_1.md``.
  3. Compiles the markdown into a ``HandoverDocument`` via the compiler
     agent (or an injected compile function for tests).
  4. Routes ``TASK-SEED-BOARD-001`` through ``orchestrate(...)``, capturing
     the structured ``StoryProposal`` items via a ``set_agent_runner`` hook.
  5. Halts at the approval gate, printing the verbatim approval prompt and
     a human-readable proposal listing. No GitHub writes occur.

HARD RULE 4 is respected: dispatch goes through ``orchestrate(...)``. The
capture hook uses the documented ``set_agent_runner`` mechanism to retain
the structured output the default runner discards.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import IO, Optional

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import init_demo_workspace  # noqa: E402
from alfred import orchestrator  # noqa: E402
from alfred.orchestrator import orchestrate, set_agent_runner  # noqa: E402
from alfred.schemas.agent import (  # noqa: E402
    BoardState,
    QualityRubric,
    StoryGeneratorInput,
    StoryGeneratorOutput,
)
from alfred.schemas.config import AlfredConfig  # noqa: E402
from alfred.schemas.handover import (  # noqa: E402
    HandoverDocument,
    HandoverTask,
    TaskResult,
)

CHARTER_SRC: Path = REPO_ROOT / "docs" / "active" / "CUSTOMER_ONBOARDING_PORTAL_CHARTER.md"
OUTLINE_SRC: Path = REPO_ROOT / "docs" / "active" / "KICKOFF_HANDOVER_OUTLINE.md"

KICKOFF_HANDOVER_ID: str = "ALFRED_HANDOVER_1"
KICKOFF_HANDOVER_FILENAME: str = f"{KICKOFF_HANDOVER_ID}.md"
KICKOFF_TASK_ID: str = "TASK-SEED-BOARD-001"
STORY_GENERATOR_AGENT: str = "story_generator"
APPROVAL_PROMPT_TEMPLATE: str = (
    "Alfred has proposed {n} draft backlog items for the Customer Onboarding Portal. "
    "Reviewing now will not modify the board. "
    "Approve to write these items to the GitHub Project."
)

CompileFn = Callable[[str], HandoverDocument]


# ---------------------------------------------------------------------------
# Kickoff handover rendering
# ---------------------------------------------------------------------------


def build_kickoff_markdown(charter_text: str) -> str:
    """Render the kickoff handover markdown for the demo project.

    The shape follows ``docs/active/KICKOFF_HANDOVER_OUTLINE.md`` exactly.
    A single task block is emitted for ``TASK-SEED-BOARD-001`` so the
    compiler can extract a ``HandoverTask`` with ``agent_type=
    "story_generator"``.
    """
    charter_block = charter_text.strip()
    return f"""# Alfred's Handover Document #1 — Customer Onboarding Portal Kickoff

## CONTEXT — READ THIS FIRST

**id:** {KICKOFF_HANDOVER_ID}
**author:** Alfred
**previous_handover:** none

This kickoff handover seeds the Customer Onboarding Portal demo project. The workspace begins nearly blank — only `README.md`, `docs/CHARTER.md`, and an empty `docs/handovers/` directory exist. The GitHub Project board starts at zero items. Project docs are the source of truth; the board is a downstream projection. Board writes are gated behind explicit human approval. This run translates the charter into the first governed kickoff handover, compiles it, produces 6–8 draft backlog items, then halts at the approval gate before any board mutation.

### Charter (verbatim from `docs/CHARTER.md`)

{charter_block}

## WHAT EXISTS TODAY

- The demo workspace contains `README.md`, `docs/CHARTER.md`, and an empty `docs/handovers/` directory.
- There is no prior delivery history, no `src/` tree, no tests, and no CI workflow inside the demo workspace at kickoff.
- The GitHub Project board has zero items.

## KICKOFF GOALS

1. Persist the first governed handover artifact at `docs/handovers/ALFRED_HANDOVER_1.md` inside the demo project.
2. Translate the charter into a credible first-cut backlog (6–8 stories) for the blank GitHub Project.
3. Keep the docs artifact authoritative; treat the board as a downstream projection.
4. Make the approval gate visible and understandable to a senior manager.

## PROPOSED BACKLOG — CUSTOMER ONBOARDING PORTAL

The proposed backlog is generated at runtime by `TASK-SEED-BOARD-001`. Final proposals must remain traceable to the charter and the count must stay within 6–8 items. Benchmark titles for review:

1. Define onboarding journey end-to-end
2. Stand up signup and identity verification surface
3. Build customer profile data model
4. Wire up document-upload and KYC checks
5. Compose welcome and activation email flow
6. Add internal-ops review queue for flagged customers
7. Instrument funnel analytics
8. Define rollout and pilot-cohort plan

## TASK {KICKOFF_TASK_ID} — Generate Kickoff Backlog

**Goal:** Produce a structured list of 6–8 `StoryProposal` items for the Customer Onboarding Portal kickoff backlog, each carrying `title`, `description`, `acceptance_criteria` (2–3 bullets), and `story_points`. Stories must be traceable to the charter.

**Agent type:** {STORY_GENERATOR_AGENT}

**Input:** the compiled `HandoverDocument` produced from this approved kickoff handover.

**Output:** structured `StoryProposal` list (6–8 items) returned by the story generator.

**Gate:** execution halts immediately after story generation; no board writes occur until the approval gate has been passed.

**Failure mode:** if fewer than 6 or more than 8 proposals are generated, the task fails and must be re-run before approval is requested.

## APPROVAL GATE

Once `TASK-SEED-BOARD-001` returns 6–8 `StoryProposal` items, the harness presents the following prompt verbatim, with `N` replaced by the actual count:

> Alfred has proposed N draft backlog items for the Customer Onboarding Portal. Reviewing now will not modify the board. Approve to write these items to the GitHub Project.

This wording is locked for Phase 4 reuse. The harness halts after printing the prompt; it does not perform the board write.

## WHAT NOT TO DO

1. Do not write to the GitHub Project before the approval gate is passed.
2. Do not emit fewer than 6 or more than 8 proposals.
3. Do not collapse structured story fields into summary prose only.
4. Do not treat benchmark titles as hardcoded output when the charter supports cleaner phrasing.
5. Do not broaden scope into retrospectives, multi-sprint planning, or story editing.

## POST-MORTEM

*Executor to fill: what worked, what was harder than expected, decisions made during execution, forward plan.*

**next_handover_id:** ALFRED_HANDOVER_2
"""


# ---------------------------------------------------------------------------
# Compile path — real implementation calls the compiler agent (LLM-backed)
# ---------------------------------------------------------------------------


def compile_via_alfred(markdown: str) -> HandoverDocument:
    """Real compile path. Invokes ``run_compiler`` and returns the handover."""
    from alfred.agents.compiler import run_compiler
    from alfred.schemas.agent import CompilerInput

    out = run_compiler(
        CompilerInput(
            draft_handover_markdown=markdown,
            handover_id=KICKOFF_HANDOVER_ID,
            author="Alfred",
        )
    )
    return out.handover


# ---------------------------------------------------------------------------
# Story-generator capture: install a runner that mirrors the default behaviour
# while retaining the structured StoryGeneratorOutput for the approval gate.
# ---------------------------------------------------------------------------


def _install_capture_runner(
    captured: list[StoryGeneratorOutput],
    *,
    inner_runner: Optional[Callable[..., StoryGeneratorOutput]] = None,
) -> None:
    """Install a story_generator runner that captures structured output.

    ``inner_runner`` lets tests inject a deterministic story generator. When
    omitted, the wrapper calls the real ``run_story_generator`` with the same
    inputs the orchestrator's default runner constructs.
    """
    from alfred.schemas.agent import RAGChunk

    def runner(
        task: HandoverTask,
        handover: HandoverDocument,
        config: AlfredConfig,
        db_path: Optional[str],
    ) -> TaskResult:
        story_input = StoryGeneratorInput(
            quality_rubric=QualityRubric(
                criteria=["Clear title", "Acceptance criteria present"],
                minimum_acceptance_criteria_count=2,
                require_story_points=True,
            ),
            board_state=BoardState(),
            handover_corpus_chunks=cast_list_rag(),
            generation_prompt=task.goal or None,
        )
        if inner_runner is not None:
            out = inner_runner(story_input)
        else:
            from alfred.agents.story_generator import run_story_generator
            from alfred.tools.llm import resolve_model

            provider, model = resolve_model("generate", config)
            out = run_story_generator(
                story_input, provider=provider, model=model, db_path=db_path
            )
        captured.append(out)
        summary = (
            f"Generated {len(out.stories)} stories; "
            f"{len(out.stories_failing_rubric)} failed rubric."
        )
        return TaskResult(completed=True, output_summary=summary)

    set_agent_runner(STORY_GENERATOR_AGENT, runner)


def cast_list_rag() -> list:  # narrow shim to keep typing local
    return []


# ---------------------------------------------------------------------------
# Approval-gate display
# ---------------------------------------------------------------------------


def render_proposal_listing(output: StoryGeneratorOutput) -> str:
    """Render proposals in human-readable form for terminal display."""
    lines: list[str] = []
    lines.append(f"[STORIES] {len(output.stories)} proposals generated:")
    for i, story in enumerate(output.stories, 1):
        pts = story.story_points if story.story_points is not None else "?"
        lines.append(f"  {i}. {story.title} ({pts} pts)")
        if story.description:
            lines.append(f"     {story.description}")
        for ac in story.acceptance_criteria:
            lines.append(f"     - {ac}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Handover persistence
# ---------------------------------------------------------------------------


def persist_kickoff_handover(workspace: Path, markdown: str) -> Path:
    """Write the kickoff markdown to its frozen path inside the workspace.

    Returns the destination path. Idempotent — overwrites the file if it
    already exists. The harness's own re-run guard is handled by the
    caller (see ``run_demo``).
    """
    handovers_dir = workspace / "docs" / "handovers"
    if not handovers_dir.is_dir():
        raise FileNotFoundError(
            f"{handovers_dir} does not exist; run init_demo_workspace.py first."
        )
    target = handovers_dir / KICKOFF_HANDOVER_FILENAME
    target.write_text(markdown, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Default config for the harness — no GitHub board, no RAG, no DB writes
# ---------------------------------------------------------------------------


def default_demo_config() -> AlfredConfig:
    cfg = AlfredConfig()
    cfg.llm.provider = "anthropic"
    cfg.llm.model = "claude-sonnet-4-6"
    cfg.github.org = ""
    cfg.github.project_number = 0
    cfg.rag.index_path = ""
    cfg.database.path = ""
    return cfg


# ---------------------------------------------------------------------------
# Public entry point — used by both CLI and tests
# ---------------------------------------------------------------------------


class HarnessError(Exception):
    """Raised when the harness cannot complete its run (e.g. count out of range)."""


def run_demo(
    workspace: Path,
    *,
    compile_fn: CompileFn = compile_via_alfred,
    config: Optional[AlfredConfig] = None,
    inner_story_runner: Optional[Callable[..., StoryGeneratorOutput]] = None,
    out_stream: Optional[IO[str]] = None,
    charter_path: Path = CHARTER_SRC,
) -> int:
    """Drive the kickoff demo end to end. Returns a process exit code.

    Returns 0 on success (approval gate reached cleanly). Raises
    ``HarnessError`` on validation failures (e.g. missing task,
    out-of-range proposal count) so callers see a structured error.
    """
    out: IO[str] = out_stream if out_stream is not None else sys.stdout

    # 1. Workspace must already match the frozen layout.
    readme_text = init_demo_workspace.extract_readme_text()
    if not init_demo_workspace.workspace_matches_spec(
        workspace, init_demo_workspace.CHARTER_SRC, readme_text
    ):
        raise HarnessError(
            f"{workspace} is not initialised; run "
            "scripts/init_demo_workspace.py --workspace "
            f"{workspace} first."
        )
    print(f"[INIT] Workspace verified at {workspace}", file=out)

    # 2. Render and persist the kickoff handover markdown.
    charter_text = charter_path.read_text(encoding="utf-8")
    markdown = build_kickoff_markdown(charter_text)
    handover_path = persist_kickoff_handover(workspace, markdown)
    print(f"[PERSIST] Wrote {handover_path}", file=out)

    # 3. Compile to HandoverDocument.
    handover = compile_fn(markdown)
    task_ids = [t.id for t in handover.tasks]
    print(
        f"[COMPILE] HandoverDocument compiled; tasks: {task_ids}",
        file=out,
    )
    if not any(t.id == KICKOFF_TASK_ID for t in handover.tasks):
        raise HarnessError(
            f"Compiled HandoverDocument is missing task {KICKOFF_TASK_ID}; "
            "compiler did not extract the kickoff task from the markdown."
        )

    # 4. Install capture runner; orchestrator dispatches story_generator
    #    through it, retaining the structured StoryGeneratorOutput.
    captured: list[StoryGeneratorOutput] = []
    # Reset so set_agent_runner doesn't preserve a stale runner from another test.
    orchestrator._AGENT_RUNNERS.clear()
    _install_capture_runner(captured, inner_runner=inner_story_runner)

    cfg = config if config is not None else default_demo_config()

    # 5. Dispatch via orchestrate(...).
    print(
        f"[ORCHESTRATE] Dispatching {KICKOFF_TASK_ID} via orchestrate(...)",
        file=out,
    )
    orchestrate(handover, cfg)

    if not captured:
        raise HarnessError(
            "Story generator runner was not invoked by the orchestrator. "
            "Check that the compiled task carries agent_type='story_generator'."
        )

    output = captured[-1]
    n = len(output.stories)
    if not 6 <= n <= 8:
        raise HarnessError(
            f"{KICKOFF_TASK_ID} produced {n} proposals; expected 6–8."
        )

    # 6. Approval gate — print proposals and verbatim prompt; halt cleanly.
    print(render_proposal_listing(output), file=out)
    print("", file=out)
    print("APPROVAL GATE", file=out)
    print(APPROVAL_PROMPT_TEMPLATE.format(n=n), file=out)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Customer Onboarding Portal kickoff demo.",
    )
    parser.add_argument(
        "--workspace",
        required=True,
        type=Path,
        help="Path to the demo project root directory (must be initialised first).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_demo(args.workspace)
    except HarnessError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
