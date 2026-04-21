"""
FastAPI app — HTTP interface for Alfred.

Routes cover planning, evaluation, retrospective analysis, compilation, and a
multi-step HITL approval workflow. Config is loaded at startup and injectable
for tests via set_config(). All secrets are read from environment variables at
call time, never from config.
"""
from __future__ import annotations

import math
import os
from typing import Any, Literal, Optional

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from alfred.schemas.agent import (
    BoardState,
    CheckpointEvaluation,
    ExecutorOutput,
    PlannerInput,
    QualityJudgeInput,
    RAGChunk,
    RetroAnalystInput,
    RetroAnalystOutput,
    VelocityRecord,
)
from alfred.schemas.config import AlfredConfig
from alfred.tools.git_log import read_git_log

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


class ApprovalRequestCreate(BaseModel):
    handover_id: str
    action_type: str  # e.g. "story_creation"
    item_id: str


class ApprovalRecord(BaseModel):
    id: str
    handover_id: str
    action_type: str
    item_id: str
    requested_at: str
    expires_at: str
    decided_at: Optional[str] = None
    decision: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    approval_id: str
    expires_at: str


class ApproveRequest(BaseModel):
    approval_id: str
    decision: Literal["approved", "rejected"]


class RetrospectiveRequest(BaseModel):
    analysis_focus: Optional[str] = None
    sprint_count: int = 5


class DashboardResponse(BaseModel):
    board_state: BoardState
    velocity_history: list[VelocityRecord]
    recent_checkpoints: list[dict[str, Any]]
    pending_approvals_count: int = 0


class CompileRequest(BaseModel):
    draft_handover_markdown: str
    handover_id: str
    author: str


class CompileResponse(BaseModel):
    handover_id: str
    tasks_compiled: int
    warnings: list[str]


class ExpireApprovalsResponse(BaseModel):
    expired_count: int


# ---------------------------------------------------------------------------
# Endpoint helpers
# ---------------------------------------------------------------------------


def _make_json_safe(value: Any) -> Any:
    """Recursively replace NaN/Infinity values with JSON-safe strings."""
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "nan"
        if value > 0:
            return "inf"
        return "-inf"
    if isinstance(value, dict):
        return {key: _make_json_safe(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(inner) for inner in value]
    if isinstance(value, tuple):
        return [_make_json_safe(inner) for inner in value]
    return value


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return FastAPI-style 422 responses even when validation data contains Infinity/NaN."""
    return JSONResponse(
        status_code=422,
        content={"detail": _make_json_safe(exc.errors())},
    )


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
async def generate(request: GenerateRequest) -> GenerateResponse:
    """Plan sprint: board state + corpus context → draft handover."""
    import datetime

    from alfred.agents.planner import load_canonical_template, run_planner
    from alfred.orchestrator import _run_critique_loop
    from alfred.schemas.handover import HandoverContext, HandoverDocument

    config = get_config()
    board = _get_board(config)
    velocity = _get_velocity(config)
    chunks = _get_rag_chunks(request.sprint_goal or "sprint planning", config)
    db_path = config.database.path or None
    canonical_template = load_canonical_template(config.handover.template_path)
    git_history = read_git_log()

    from alfred.tools.llm import resolve_model

    plan_provider, plan_model = resolve_model("plan", config)
    planner_out = run_planner(
        PlannerInput(
            board_state=board,
            velocity_history=velocity,
            prior_handover_summaries=chunks,
            sprint_goal=request.sprint_goal,
            canonical_template=canonical_template,
            git_history_summary=git_history,
        ),
        provider=plan_provider,
        model=plan_model,
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
async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """Quality gate: executor output + checkpoint definition → verdict."""
    from alfred.agents.quality_judge import run_quality_judge
    from alfred.tools.llm import resolve_model

    config = get_config()
    judge_input = QualityJudgeInput(
        handover_document_markdown=request.handover_document_markdown,
        checkpoint_definitions=[request.checkpoint_definition],
        executor_output=request.executor_output,
    )
    judge_provider, judge_model = resolve_model("judge", config)
    out = run_quality_judge(
        judge_input,
        provider=judge_provider,
        model=judge_model,
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


@app.post("/approvals/request", response_model=ApprovalRequestResponse)
async def request_approval(request: ApprovalRequestCreate) -> ApprovalRequestResponse:
    """Register a new pending approval with an expiry deadline."""
    import uuid

    from alfred.tools.persistence import create_pending_approval, get_approval

    config = get_config()
    db = config.database.path or None
    if not db:
        raise HTTPException(status_code=500, detail="Database path not configured")

    approval_id = uuid.uuid4().hex
    create_pending_approval(
        db,
        approval_id=approval_id,
        handover_id=request.handover_id,
        action_type=request.action_type,
        item_id=request.item_id,
        timeout_seconds=config.hitl.timeout_seconds,
    )

    created = get_approval(db, approval_id)
    if created is None:
        raise HTTPException(status_code=500, detail="Approval record was not persisted")

    return ApprovalRequestResponse(
        approval_id=approval_id,
        expires_at=created["expires_at"] or "",
    )


@app.post("/approve", response_model=ApprovalRecord)
async def approve(request: ApproveRequest) -> ApprovalRecord:
    """Record a human decision on an existing pending approval."""
    from alfred.tools.persistence import get_approval, record_approval_decision

    config = get_config()
    db = config.database.path or None
    if not db:
        raise HTTPException(status_code=500, detail="Database path not configured")

    try:
        record_approval_decision(db, request.approval_id, request.decision)
    except ValueError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail.lower() else 409
        raise HTTPException(status_code=status, detail=detail)

    updated = get_approval(db, request.approval_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Approval record disappeared after update")
    return ApprovalRecord.model_validate(updated)


@app.get("/approvals/pending", response_model=list[ApprovalRecord])
async def list_pending_approvals() -> list[ApprovalRecord]:
    """Return all currently open approvals."""
    from alfred.tools.persistence import get_pending_approvals

    config = get_config()
    db = config.database.path or None
    if not db:
        return []

    return [ApprovalRecord.model_validate(row) for row in get_pending_approvals(db)]


@app.post("/approvals/expire", response_model=ExpireApprovalsResponse)
async def expire_approvals() -> ExpireApprovalsResponse:
    """Sweep expired approvals and mark them as expired."""
    from alfred.tools.persistence import get_expired_approvals, record_approval_decision

    config = get_config()
    db = config.database.path or None
    if not db:
        raise HTTPException(status_code=500, detail="Database path not configured")

    expired_count = 0
    for approval in get_expired_approvals(db):
        try:
            record_approval_decision(db, approval["id"] or "", "expired")
            expired_count += 1
        except ValueError:
            continue

    return ExpireApprovalsResponse(expired_count=expired_count)


@app.post("/retrospective", response_model=RetroAnalystOutput)
async def retrospective(request: RetrospectiveRequest) -> RetroAnalystOutput:
    """Retro analysis: corpus + velocity → pattern report."""
    from alfred.agents.retro_analyst import run_retro_analyst
    from alfred.tools.llm import resolve_model

    config = get_config()
    velocity = _get_velocity(config)
    chunks = _get_rag_chunks(request.analysis_focus or "retrospective patterns", config)
    retro_provider, retro_model = resolve_model("retro", config)

    return run_retro_analyst(
        RetroAnalystInput(
            handover_corpus_chunks=chunks,
            velocity_data=velocity,
            analysis_focus=request.analysis_focus,
        ),
        provider=retro_provider,
        model=retro_model,
        db_path=config.database.path or None,
    )


@app.post("/compile", response_model=CompileResponse)
async def compile_handover(request: CompileRequest) -> CompileResponse:
    """Compile an approved prose draft into a structured HandoverDocument.

    This endpoint is intentionally separate from POST /generate.
    It must only be called after a human has reviewed and approved the prose draft.
    """
    import os

    from alfred.agents.compiler import run_compiler
    from alfred.schemas.agent import CompilerInput
    from alfred.tools.llm import resolve_model

    config = get_config()
    compiler_input = CompilerInput(
        draft_handover_markdown=request.draft_handover_markdown,
        handover_id=request.handover_id,
        author=request.author,
    )
    compile_provider, compile_model = resolve_model("compile", config)

    try:
        result = run_compiler(
            compiler_input,
            provider=compile_provider,
            model=compile_model,
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
async def dashboard() -> DashboardResponse:
    """Read-only: sprint state, velocity history, recent checkpoint outcomes."""
    import sqlite3

    from alfred.tools.persistence import count_pending_approvals

    config = get_config()
    board = _get_board(config)
    velocity = _get_velocity(config)

    recent_checkpoints: list[dict[str, Any]] = []
    pending_approvals_count = 0
    db = config.database.path
    if db:
        try:
            with sqlite3.connect(db) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT handover_id, checkpoint_id, verdict, timestamp AS created_at "
                    "FROM checkpoint_history ORDER BY id DESC LIMIT 10"
                ).fetchall()
                recent_checkpoints = [dict(r) for r in rows]
        except Exception:
            pass
        try:
            pending_approvals_count = count_pending_approvals(db)
        except Exception:
            pending_approvals_count = 0

    return DashboardResponse(
        board_state=board,
        velocity_history=velocity,
        recent_checkpoints=recent_checkpoints,
        pending_approvals_count=pending_approvals_count,
    )
