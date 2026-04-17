"""
FastAPI app — HTTP interface for Alfred.

Five endpoints mirror the orchestrator's control surface:
  POST /generate      — plan sprint: board state → draft handover
  POST /evaluate      — quality gate: executor output + checkpoint → verdict
  POST /approve       — HITL gate: approve or reject a pending action
  POST /retrospective — retro analysis: corpus + velocity → pattern report
  GET  /dashboard     — read-only: sprint state, velocity, recent checkpoint outcomes

Config is loaded at startup and injectable for tests via set_config().
All secrets are read from environment variables at call time, never from config.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from alfred.schemas.agent import (
    BoardState,
    CheckpointEvaluation,
    ExecutorOutput,
    PlannerInput,
    QualityJudgeInput,
    QualityRubric,
    RAGChunk,
    RetroAnalystInput,
    RetroAnalystOutput,
    StoryGeneratorInput,
    VelocityRecord,
)
from alfred.schemas.config import AlfredConfig

app = FastAPI(title="Alfred")


# ---------------------------------------------------------------------------
# Config — injectable for tests
# ---------------------------------------------------------------------------

_config: Optional[AlfredConfig] = None


def _load_default_config() -> AlfredConfig:
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "default.yaml")
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return AlfredConfig.model_validate(data or {})
    except Exception:
        return AlfredConfig()


def get_config() -> AlfredConfig:
    global _config
    if _config is None:
        _config = _load_default_config()
    return _config


def set_config(config: AlfredConfig) -> None:
    """Replace the active config. Tests use this to inject a fake."""
    global _config
    _config = config


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    sprint_goal: Optional[str] = None
    prior_handover_id: Optional[str] = None


class GenerateResponse(BaseModel):
    draft_handover_markdown: str
    task_decomposition: list[str]
    open_questions: list[str]


class EvaluateRequest(BaseModel):
    handover_document_markdown: str
    checkpoint_definition: str  # JSON-encoded decision table
    executor_output: Optional[ExecutorOutput] = None


class EvaluateResponse(BaseModel):
    checkpoint_id: str
    verdict: str
    reasoning: str
    evidence_summary: str
    hitl_required: bool


class ApproveRequest(BaseModel):
    handover_id: str
    action_type: str  # e.g. "story_creation"
    item_id: str
    approved: bool
    reason: Optional[str] = None


class ApproveResponse(BaseModel):
    status: str  # "approved" | "rejected"
    item_id: str


class RetrospectiveRequest(BaseModel):
    analysis_focus: Optional[str] = None
    sprint_count: int = 5


class DashboardResponse(BaseModel):
    board_state: BoardState
    velocity_history: list[VelocityRecord]
    recent_checkpoints: list[dict[str, Any]]


class CompileRequest(BaseModel):
    draft_handover_markdown: str
    handover_id: str
    author: str


class CompileResponse(BaseModel):
    handover_id: str
    tasks_compiled: int
    warnings: list[str]


# ---------------------------------------------------------------------------
# Endpoint helpers
# ---------------------------------------------------------------------------


def _get_board(config: AlfredConfig) -> BoardState:
    if not config.github.org or not config.github.project_number:
        return BoardState()
    token = os.environ.get(config.github.token_env_var, "")
    if not token:
        return BoardState()
    from alfred.tools.github_api import get_board_state
    return get_board_state(config.github.org, config.github.project_number, token)


def _get_velocity(config: AlfredConfig) -> list[VelocityRecord]:
    db = config.database.path
    if not db:
        return []
    from alfred.tools.persistence import get_velocity_history
    return get_velocity_history(db, sprint_count=10)


def _get_rag_chunks(query: str, config: AlfredConfig) -> list[RAGChunk]:
    if not config.rag.index_path or not query:
        return []
    try:
        from alfred.tools.rag import retrieve
        return retrieve(query, config.rag.index_path, top_k=5)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    """Plan sprint: board state + corpus context → draft handover."""
    import datetime

    from alfred.agents.planner import run_planner
    from alfred.orchestrator import _run_critique_loop
    from alfred.schemas.handover import HandoverContext, HandoverDocument

    config = get_config()
    board = _get_board(config)
    velocity = _get_velocity(config)
    chunks = _get_rag_chunks(request.sprint_goal or "sprint planning", config)
    db_path = config.database.path or None

    planner_out = run_planner(
        PlannerInput(
            board_state=board,
            velocity_history=velocity,
            prior_handover_summaries=chunks,
            sprint_goal=request.sprint_goal,
        ),
        provider=config.llm.provider,
        model=config.llm.model,
        db_path=db_path,
    )

    # Critique loop refines the draft before returning it to the caller.
    # A temporary HandoverDocument stores the critique_history for the loop.
    temp_handover = HandoverDocument(
        id=f"generate-{request.prior_handover_id or 'draft'}",
        title="Draft",
        date=datetime.date.today(),
        author="system",
        context=HandoverContext(narrative=""),
    )
    best_draft = _run_critique_loop(
        planner_out.draft_handover_markdown,
        temp_handover,
        config,
        db_path,
    )

    return GenerateResponse(
        draft_handover_markdown=best_draft,
        task_decomposition=planner_out.task_decomposition,
        open_questions=planner_out.open_questions,
    )


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """Quality gate: executor output + checkpoint definition → verdict."""
    from alfred.agents.quality_judge import run_quality_judge

    config = get_config()
    judge_input = QualityJudgeInput(
        handover_document_markdown=request.handover_document_markdown,
        checkpoint_definitions=[request.checkpoint_definition],
        executor_output=request.executor_output,
    )
    out = run_quality_judge(
        judge_input,
        provider=config.llm.provider,
        model=config.llm.model,
        db_path=config.database.path or None,
    )

    if not out.checkpoint_evaluations:
        raise HTTPException(status_code=500, detail="Quality judge produced no evaluations")

    ev: CheckpointEvaluation = out.checkpoint_evaluations[0]
    return EvaluateResponse(
        checkpoint_id=ev.checkpoint_id,
        verdict=ev.verdict,
        reasoning=ev.reasoning,
        evidence_summary=ev.evidence_summary,
        hitl_required=ev.human_review_required,
    )


@app.post("/approve", response_model=ApproveResponse)
def approve(request: ApproveRequest) -> ApproveResponse:
    """HITL gate: approve or reject a pending action; persists decision."""
    from alfred.tools.persistence import record_agent_invocation
    import hashlib

    config = get_config()
    db = config.database.path or None

    if db:
        record_agent_invocation(
            db,
            agent_name=f"hitl:{request.action_type}",
            input_hash=hashlib.sha256(
                f"{request.handover_id}:{request.item_id}".encode()
            ).hexdigest()[:16],
            output_hash=hashlib.sha256(
                f"{request.approved}:{request.reason or ''}".encode()
            ).hexdigest()[:16],
            error=None if request.approved else f"rejected:{request.reason or 'no reason'}",
        )

    return ApproveResponse(
        status="approved" if request.approved else "rejected",
        item_id=request.item_id,
    )


@app.post("/retrospective", response_model=RetroAnalystOutput)
def retrospective(request: RetrospectiveRequest) -> RetroAnalystOutput:
    """Retro analysis: corpus + velocity → pattern report."""
    from alfred.agents.retro_analyst import run_retro_analyst

    config = get_config()
    velocity = _get_velocity(config)
    chunks = _get_rag_chunks(request.analysis_focus or "retrospective patterns", config)

    return run_retro_analyst(
        RetroAnalystInput(
            handover_corpus_chunks=chunks,
            velocity_data=velocity,
            analysis_focus=request.analysis_focus,
        ),
        provider=config.llm.provider,
        model=config.llm.model,
        db_path=config.database.path or None,
    )


@app.post("/compile", response_model=CompileResponse)
def compile_handover(request: CompileRequest) -> CompileResponse:
    """Compile an approved prose draft into a structured HandoverDocument.

    This endpoint is intentionally separate from POST /generate.
    It must only be called after a human has reviewed and approved the prose draft.
    """
    import json
    import os

    from alfred.agents.compiler import run_compiler
    from alfred.schemas.agent import CompilerInput

    config = get_config()
    compiler_input = CompilerInput(
        draft_handover_markdown=request.draft_handover_markdown,
        handover_id=request.handover_id,
        author=request.author,
    )

    try:
        result = run_compiler(
            compiler_input,
            provider=config.llm.provider,
            model=config.llm.model,
            db_path=config.database.path or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    output_dir = os.path.join("data", "handovers")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{request.handover_id}.json")
    with open(output_path, "w") as f:
        f.write(result.handover.model_dump_json(indent=2))

    return CompileResponse(
        handover_id=request.handover_id,
        tasks_compiled=len(result.handover.tasks),
        warnings=result.compilation_warnings,
    )


@app.get("/dashboard", response_model=DashboardResponse)
def dashboard() -> DashboardResponse:
    """Read-only: sprint state, velocity history, recent checkpoint outcomes."""
    import sqlite3

    config = get_config()
    board = _get_board(config)
    velocity = _get_velocity(config)

    recent_checkpoints: list[dict[str, Any]] = []
    db = config.database.path
    if db:
        try:
            with sqlite3.connect(db) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT handover_id, checkpoint_id, verdict, created_at "
                    "FROM checkpoint_history ORDER BY id DESC LIMIT 10"
                ).fetchall()
                recent_checkpoints = [dict(r) for r in rows]
        except Exception:
            pass

    return DashboardResponse(
        board_state=board,
        velocity_history=velocity,
        recent_checkpoints=recent_checkpoints,
    )
