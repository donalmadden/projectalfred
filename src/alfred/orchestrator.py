"""
Orchestrator — executes a HandoverDocument by iterating its tasks, routing each
to the appropriate agent, and enforcing checkpoint-gated control flow.

The orchestrator is a plain Python function. It is not a graph, not a framework,
not an actor system. Composition flows through the document: each agent reads
from and writes to the HandoverDocument, and the next agent reads what the
previous one produced.

Methodology properties encoded structurally here:
  1. Document as protocol    — the HandoverDocument is the single argument and single return
  2. Checkpoint-gated control — Quality Judge verdicts route control flow explicitly
  3. Reasoning/execution isolation — agents are dispatched by role, each under its own schema
  4. Inline post-mortem      — failures are written back into handover.post_mortem before raising
  5. Statelessness           — no global state; a cold start can resume from the returned document
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Optional

from alfred.schemas.agent import (
    BoardState,
    ExecutorOutput,
    PlannerInput,
    QualityJudgeInput,
    QualityRubric,
    RAGChunk,
    RetroAnalystInput,
    StoryGeneratorInput,
)
from alfred.schemas.checkpoint import Checkpoint, Verdict
from alfred.schemas.config import AlfredConfig
from alfred.schemas.handover import (
    CritiqueEntry,  # noqa: E401 (needed before class defs)
    HandoverDocument,
    HandoverTask,
    PostMortem,
    TaskResult,
)
from alfred.schemas.validator_findings import FormattedFinding


class CheckpointHalt(Exception):
    """Raised when a checkpoint returns a STOP verdict."""


class HumanEscalation(Exception):
    """Raised when a checkpoint returns an ESCALATE verdict requiring human decision."""


# ---------------------------------------------------------------------------
# Agent dispatch table — replaceable for tests
# ---------------------------------------------------------------------------

AgentRunner = Callable[[HandoverTask, HandoverDocument, AlfredConfig, Optional[str]], TaskResult]

_AGENT_RUNNERS: dict[str, AgentRunner] = {}


def _register_runners() -> None:
    """Populate the dispatch table. Deferred to avoid circular imports at module load."""
    from alfred.agents.planner import run_planner
    from alfred.agents.retro_analyst import run_retro_analyst
    from alfred.agents.story_generator import run_story_generator
    from alfred.tools.llm import resolve_model

    def _planner_runner(
        task: HandoverTask,
        handover: HandoverDocument,
        config: AlfredConfig,
        db_path: Optional[str],
    ) -> TaskResult:
        board = _get_board_state(config)
        velocity = _get_velocity_history(config, db_path)
        chunks = _retrieve_rag(task.goal or task.title, config)
        inp = PlannerInput(
            board_state=board,
            velocity_history=velocity,
            prior_handover_summaries=chunks,
            sprint_goal=task.goal or None,
        )
        provider, model = resolve_model("plan", config)
        out = run_planner(inp, provider=provider, model=model, db_path=db_path)
        return TaskResult(
            completed=True,
            output_summary=out.draft_handover_markdown[:200],
        )

    def _story_runner(
        task: HandoverTask,
        handover: HandoverDocument,
        config: AlfredConfig,
        db_path: Optional[str],
    ) -> TaskResult:
        board = _get_board_state(config)
        chunks = _retrieve_rag(task.goal or task.title, config)
        inp = StoryGeneratorInput(
            quality_rubric=QualityRubric(
                criteria=["Clear title", "Acceptance criteria present"],
                minimum_acceptance_criteria_count=2,
                require_story_points=True,
            ),
            board_state=board,
            handover_corpus_chunks=chunks,
            generation_prompt=task.goal or None,
        )
        provider, model = resolve_model("generate", config)
        out = run_story_generator(inp, provider=provider, model=model, db_path=db_path)
        summary = f"Generated {len(out.stories)} stories; {len(out.stories_failing_rubric)} failed rubric."
        return TaskResult(completed=True, output_summary=summary)

    def _retro_runner(
        task: HandoverTask,
        handover: HandoverDocument,
        config: AlfredConfig,
        db_path: Optional[str],
    ) -> TaskResult:
        velocity = _get_velocity_history(config, db_path)
        chunks = _retrieve_rag(task.goal or task.title, config)
        inp = RetroAnalystInput(
            handover_corpus_chunks=chunks,
            velocity_data=velocity,
            analysis_focus=task.goal or None,
        )
        provider, model = resolve_model("retro", config)
        out = run_retro_analyst(inp, provider=provider, model=model, db_path=db_path)
        return TaskResult(completed=True, output_summary=out.retrospective_summary[:200])

    _AGENT_RUNNERS["planner"] = _planner_runner
    _AGENT_RUNNERS["story_generator"] = _story_runner
    _AGENT_RUNNERS["retro_analyst"] = _retro_runner


def set_agent_runner(agent_type: str, runner: AgentRunner) -> None:
    """Replace an agent runner. Tests use this to inject fakes."""
    _AGENT_RUNNERS[agent_type] = runner


# ---------------------------------------------------------------------------
# Tool helpers
# ---------------------------------------------------------------------------


def _get_board_state(config: AlfredConfig) -> BoardState:
    if not config.github.org or not config.github.project_number:
        return BoardState()
    from alfred.tools.github_api import get_board_state
    token = os.environ.get(config.github.token_env_var, "")
    if not token:
        return BoardState()
    return get_board_state(config.github.org, config.github.project_number, token)


def _get_velocity_history(config: AlfredConfig, db_path: Optional[str]) -> list:
    path = db_path or config.database.path
    if not path:
        return []
    from alfred.tools.persistence import get_velocity_history
    return get_velocity_history(path, sprint_count=5)


def _retrieve_rag(query: str, config: AlfredConfig) -> list[RAGChunk]:
    if not config.rag.index_path or not query:
        return []
    try:
        from alfred.tools.rag import retrieve
        return retrieve(query, config.rag.index_path, top_k=5)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Checkpoint serialisation — Checkpoint → Quality Judge format
# ---------------------------------------------------------------------------


def _checkpoint_to_definition(cp: Checkpoint) -> str:
    rows = [
        {"observation": rule.condition, "verdict": rule.likely_verdict}
        for rule in (cp.decision_table.rules or [])
    ]
    return json.dumps({"checkpoint_id": cp.id, "rows": rows})


# ---------------------------------------------------------------------------
# Control-flow primitives
# ---------------------------------------------------------------------------


def _dispatch_task(
    task: HandoverTask,
    handover: HandoverDocument,
    config: AlfredConfig,
    db_path: Optional[str],
) -> None:
    """Route a task to the correct agent and write the result back."""
    if not _AGENT_RUNNERS:
        _register_runners()

    agent_type = (task.agent_type or "").lower()
    runner = _AGENT_RUNNERS.get(agent_type)
    if runner is None:
        task.result = TaskResult(
            completed=False,
            output_summary=f"No runner registered for agent_type={agent_type!r}; task skipped.",
        )
        return

    result = runner(task, handover, config, db_path)
    task.result = result


def _evaluate_task_checkpoints(
    task: HandoverTask,
    handover: HandoverDocument,
    config: AlfredConfig,
    db_path: Optional[str],
) -> None:
    """Evaluate each unevaluated checkpoint; route on verdict."""
    from alfred.agents.quality_judge import run_quality_judge
    from alfred.tools.llm import resolve_model
    from alfred.tools.persistence import record_checkpoint

    executor_output: Optional[ExecutorOutput] = None
    if task.result is not None:
        executor_output = ExecutorOutput(
            task_id=task.id,
            console_output=task.result.output_summary,
            files_modified=task.result.files_modified,
        )

    for cp in task.checkpoints:
        if cp.is_evaluated:
            continue

        definition = _checkpoint_to_definition(cp)
        judge_input = QualityJudgeInput(
            handover_document_markdown=handover.render_markdown(),
            checkpoint_definitions=[definition],
            executor_output=executor_output,
        )
        judge_provider, judge_model = resolve_model("judge", config)
        judge_out = run_quality_judge(
            judge_input,
            provider=judge_provider,
            model=judge_model,
            db_path=db_path,
        )

        evaluations = judge_out.checkpoint_evaluations
        ev = evaluations[0] if evaluations else None
        verdict: Verdict = ev.verdict if ev else "escalate"
        reasoning = ev.reasoning if ev else "No evaluation produced."
        evidence = (executor_output.console_output[:500] if executor_output else "")

        from alfred.schemas.checkpoint import CheckpointResult
        cp.result = CheckpointResult(
            verdict=verdict,
            evidence_provided=evidence,
            reasoning=reasoning,
        )

        effective_db = db_path or config.database.path
        if effective_db:
            try:
                import hashlib
                ev_hash = hashlib.sha256(evidence.encode()).hexdigest()[:16]
                record_checkpoint(
                    effective_db,
                    handover_id=handover.id,
                    checkpoint_id=cp.id,
                    verdict=verdict,
                    evidence_hash=ev_hash,
                )
            except Exception:
                pass

        _route_on_verdict(verdict, task, cp, handover)


def _route_on_verdict(
    verdict: Verdict,
    task: HandoverTask,
    checkpoint: Checkpoint,
    handover: HandoverDocument,
) -> None:
    """Apply the control-flow consequence of a verdict."""
    if verdict == "proceed":
        return

    if verdict == "pivot":
        if task.result is not None:
            task.result.pivot_taken = f"Pivoted at {checkpoint.id}"
        return

    if verdict == "stop":
        if handover.post_mortem is None:
            handover.post_mortem = PostMortem(
                summary=f"STOP verdict at {checkpoint.id} in task {task.id}.",
                root_causes=[checkpoint.result.reasoning if checkpoint.result else "Unknown"],
                what_failed=[f"Task {task.id}: {task.title}"],
            )
        raise CheckpointHalt(
            f"STOP at {checkpoint.id} (task {task.id}): "
            + (checkpoint.result.reasoning if checkpoint.result else "")
        )

    if verdict == "escalate":
        raise HumanEscalation(
            f"ESCALATE at {checkpoint.id} (task {task.id}): human decision required. "
            + (checkpoint.result.reasoning if checkpoint.result else "")
        )


# ---------------------------------------------------------------------------
# Critique loop — planner–judge revision cycle (methodology property 3:
# orchestrator mediates; planner and judge never call each other directly)
# ---------------------------------------------------------------------------


def _run_critique_loop(
    draft_markdown: str,
    handover: HandoverDocument,
    config: AlfredConfig,
    db_path: Optional[str],
    *,
    repo_facts_summary: Optional[list[str]] = None,
    generation_date: Optional[str] = None,
    expected_handover_id: Optional[str] = None,
    expected_previous_handover: Optional[str] = None,
) -> str:
    """Run planner–judge iterations. Returns the best draft markdown.

    The orchestrator calls each agent in turn and writes intermediate results
    to handover.critique_history. The planner never calls the judge; the
    judge never calls the planner.
    """
    import datetime

    from alfred.agents.planner import load_canonical_template, run_planner
    from alfred.agents.quality_judge import run_quality_judge
    from alfred.tools.git_log import read_git_log
    from alfred.tools.llm import resolve_model

    planner_cfg = config.agents.planner
    max_iters: int = planner_cfg.max_critique_iterations
    threshold: float = planner_cfg.critique_quality_threshold
    warnings_visible: bool = planner_cfg.realism_warnings_visible

    if max_iters <= 0:
        return draft_markdown

    # Revisions must preserve Alfred house style, not drift back to a generic
    # shape. Load the scaffold and git history once; reuse across iterations.
    canonical_template = load_canonical_template(config.handover.template_path)
    git_history = read_git_log()

    current_draft = draft_markdown
    best_draft = draft_markdown
    best_score: float = -1.0

    for iteration in range(max_iters):
        # Quality judge evaluates the current draft using the expensive generator tier.
        judge_input = QualityJudgeInput(
            handover_document_markdown=current_draft,
            checkpoint_definitions=[],
        )
        critique_provider, critique_model = resolve_model("critique", config)
        judge_out = run_quality_judge(
            judge_input,
            provider=critique_provider,
            model=critique_model,
            db_path=db_path,
            task_type="critique",
        )

        score: float = judge_out.overall_quality_score or 0.0
        issues: list[str] = [v.description for v in judge_out.validation_issues]

        # Deterministic validators — strict factual gate plus realism gate.
        # Findings are formatted to strings so they survive prompt rendering.
        det_findings, det_blocking = _run_deterministic_validators(
            current_draft, warnings_visible=warnings_visible
        )

        if score > best_score:
            best_score = score
            best_draft = current_draft

        # Stop early when both feedback channels are clean. Judge issues alone
        # being empty is no longer sufficient — deterministic ERROR findings
        # must also be absent before the draft can be considered finished.
        if (not issues or score >= threshold) and not det_blocking:
            break

        # Only revise when there is another iteration to run
        if iteration + 1 < max_iters:
            entry = CritiqueEntry(
                iteration=iteration,
                quality_score=score,
                validation_issues=issues,
                deterministic_findings=det_findings,
                revised_at=datetime.datetime.utcnow().isoformat(),
            )
            handover.critique_history.append(entry)

            board = _get_board_state(config)
            velocity = _get_velocity_history(config, db_path)
            chunks = _retrieve_rag(current_draft[:200], config)
            plan_provider, plan_model = resolve_model("plan", config)
            planner_out = run_planner(
                PlannerInput(
                    board_state=board,
                    velocity_history=velocity,
                    prior_handover_summaries=chunks,
                    prior_critique=handover.critique_history,
                    canonical_template=canonical_template,
                    git_history_summary=git_history,
                    repo_facts_summary=repo_facts_summary or [],
                    generation_date=generation_date,
                    expected_handover_id=expected_handover_id,
                    expected_previous_handover=expected_previous_handover,
                    deterministic_findings=det_findings,
                ),
                provider=plan_provider,
                model=plan_model,
                db_path=db_path,
            )
            current_draft = planner_out.draft_handover_markdown

    return best_draft


def _run_deterministic_validators(
    draft_markdown: str,
    *,
    warnings_visible: bool,
) -> tuple[list["FormattedFinding"], bool]:
    """Run factual + realism validators against the draft.

    Returns ``(visible_findings, has_blocking_errors)``. ``visible_findings`` is
    the list of typed findings to forward into the next planner iteration; when
    ``warnings_visible`` is False only ERROR-severity findings are included.
    ``has_blocking_errors`` is True when any ERROR finding is present, used by
    the early-exit condition.
    """
    try:
        from scripts.validate_alfred_planning_facts import (
            validate_current_state_facts,
            validate_future_task_realism,
        )
    except Exception:
        return [], False

    findings = list(validate_current_state_facts(draft_markdown)) + list(
        validate_future_task_realism(draft_markdown)
    )
    has_errors = any(f.severity == "error" for f in findings)
    if warnings_visible:
        visible = findings
    else:
        visible = [f for f in findings if f.severity == "error"]
    return visible, has_errors


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def orchestrate(
    handover: HandoverDocument,
    config: AlfredConfig,
    *,
    db_path: Optional[str] = None,
) -> HandoverDocument:
    """Execute a handover document.

    Iterates tasks in order. For each task:
      1. If result is not yet set: dispatches to the registered agent runner.
      2. Evaluates any unevaluated checkpoints via the Quality Judge.
      3. Routes control flow on verdict.

    Returns the updated HandoverDocument. Re-runnable: tasks with results
    already set are not re-dispatched (statelessness — property 5).
    Raises CheckpointHalt on STOP; raises HumanEscalation on ESCALATE.
    """
    for task in handover.tasks:
        if task.result is None:
            _dispatch_task(task, handover, config, db_path)

        if task.checkpoints:
            _evaluate_task_checkpoints(task, handover, config, db_path)

    return handover
