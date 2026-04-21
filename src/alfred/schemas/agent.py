"""
Agent boundary schemas — the input/output contracts for each of the four agents.

Methodology property 3 (reasoning/execution isolation) is enforced structurally:
each agent can only produce what its output schema allows.
The schema makes it structurally impossible for an agent to exceed its contract.

Agent roles:
  Planner          — reasoning side, produces drafts
  Story Generator  — reasoning side, produces validated stories
  Quality Judge    — checkpoint gate, never modifies artifacts
  Retro Analyst    — read-only pattern extraction, no write operations
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared value types
# ---------------------------------------------------------------------------

StoryPoint = Literal[1, 2, 3, 5, 8, 13]

AgentName = Literal["planner", "story_generator", "quality_judge", "retro_analyst"]


# ---------------------------------------------------------------------------
# Shared read-only inputs (agents receive these, never write them)
# ---------------------------------------------------------------------------


class BoardStory(BaseModel):
    """A story as it exists on the GitHub Projects board."""

    id: str
    title: str
    status: str
    story_points: Optional[int] = None
    assignee: Optional[str] = None
    labels: list[str] = Field(default_factory=list)


class BoardState(BaseModel):
    """Read-only snapshot of the GitHub Projects board."""

    sprint_number: Optional[int] = None
    sprint_start: Optional[date] = None
    sprint_end: Optional[date] = None
    stories: list[BoardStory] = Field(default_factory=list)
    velocity_last_sprint: Optional[float] = None
    fetched_at: Optional[str] = None


class RAGChunk(BaseModel):
    """A retrieved chunk from the handover corpus."""

    document_id: str
    section_header: str
    content: str
    relevance_score: float


class VelocityRecord(BaseModel):
    """Historical velocity for a single sprint."""

    sprint_number: int
    points_committed: int
    points_completed: int
    completion_rate: float


# ---------------------------------------------------------------------------
# Planner — produces draft handovers and sprint plans
# ---------------------------------------------------------------------------


class PlannerInput(BaseModel):
    """Everything the Planner is allowed to see.

    The Planner reads context and produces drafts.
    It never executes tasks, never modifies the board, never writes code.
    """

    board_state: BoardState
    velocity_history: list[VelocityRecord] = Field(default_factory=list)
    prior_handover_summaries: list[RAGChunk] = Field(default_factory=list)
    current_handover_context: Optional[str] = None
    sprint_goal: Optional[str] = None
    prior_critique: Optional[list["CritiqueEntry"]] = None
    # When supplied, the planner prompt injects this scaffold verbatim and
    # instructs the model to preserve every `##` / `###` heading. Empty for
    # generic/legacy generation paths; set for Alfred canonical generation.
    canonical_template: Optional[str] = None
    # Real git commits supplied by the caller. When present the planner renders
    # them verbatim under ### Git History and is forbidden from inventing extras.
    # Optional so non-repo and test contexts still work.
    git_history_summary: list[str] = Field(default_factory=list)
    # Authoritative current-state facts about the repo (agent roster, tool
    # modules, API surface, packaging state, type checker). Injected verbatim
    # into the prompt and treated as non-negotiable truth by the planner.
    repo_facts_summary: list[str] = Field(default_factory=list)
    # Generation metadata: today's date and the expected handover identifiers.
    # The planner must use these verbatim in the draft metadata block instead
    # of inferring values from RAG context. All optional so legacy paths work.
    generation_date: Optional[str] = None
    expected_handover_id: Optional[str] = None
    expected_previous_handover: Optional[str] = None
    # Formatted findings from the deterministic validators (factual + realism).
    # Each string is a Finding.format() result. The planner prompt renders these
    # as non-negotiable failures that must be addressed before the draft can be
    # promoted. Uses list[str] (not raw Finding objects) to keep the schema
    # serialisable and prompt rendering trivial.
    deterministic_findings: list[str] = Field(default_factory=list)


class SprintPlan(BaseModel):
    """A proposed sprint plan produced by the Planner."""

    sprint_number: int
    proposed_capacity_points: int
    committed_story_ids: list[str]
    rationale: str


class PlannerOutput(BaseModel):
    """What the Planner is allowed to produce — and nothing else.

    The Planner produces DRAFTS. A human must approve before any draft
    becomes protocol (methodology property: Alfred drafts, humans approve).
    """

    draft_handover_markdown: str
    sprint_plan: Optional[SprintPlan] = None
    task_decomposition: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    # The Planner is forbidden from producing any of the following.
    # These fields do not exist in this schema by design.
    # No: board_writes, code_changes, schema_modifications, checkpoint_verdicts


# ---------------------------------------------------------------------------
# Story Generator — produces validated draft stories
# ---------------------------------------------------------------------------


class QualityRubric(BaseModel):
    """The quality rubric the Story Generator validates against."""

    criteria: list[str]
    minimum_acceptance_criteria_count: int = 2
    require_story_points: bool = True


class Story(BaseModel):
    """A draft story produced by the Story Generator."""

    title: str
    description: str
    acceptance_criteria: list[str]
    story_points: Optional[StoryPoint] = None
    labels: list[str] = Field(default_factory=list)
    quality_score: Optional[float] = None
    quality_notes: Optional[str] = None


class StoryGeneratorInput(BaseModel):
    """Everything the Story Generator is allowed to see."""

    handover_corpus_chunks: list[RAGChunk] = Field(default_factory=list)
    quality_rubric: QualityRubric
    board_state: BoardState
    generation_prompt: Optional[str] = None


class StoryGeneratorOutput(BaseModel):
    """What the Story Generator is allowed to produce.

    Stories must pass quality rubric validation before this output is produced.
    The Story Generator cannot write stories to the board — that requires a
    HITL approval gate (methodology property 2: checkpoint-gated execution).
    """

    stories: list[Story] = Field(default_factory=list)
    rubric_applied: str
    stories_failing_rubric: list[str] = Field(default_factory=list)

    # Forbidden: board_writes, direct_story_creation, schema_modifications


# ---------------------------------------------------------------------------
# Quality Judge — evaluates checkpoints, never modifies artifacts
# ---------------------------------------------------------------------------


class ExecutorOutput(BaseModel):
    """The raw output provided by the executor for checkpoint evaluation."""

    task_id: str
    console_output: str
    files_modified: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    """A single issue found during handover validation."""

    severity: Literal["error", "warning", "info"]
    property_violated: Optional[Literal["1", "2", "3", "4", "5"]] = None
    section: str
    description: str


class CheckpointEvaluation(BaseModel):
    """The Quality Judge's evaluation of a single checkpoint."""

    checkpoint_id: str
    verdict: Literal["proceed", "pivot", "stop", "escalate"]
    evidence_summary: str
    reasoning: str
    human_review_required: bool = False


class QualityJudgeInput(BaseModel):
    """Everything the Quality Judge is allowed to see.

    The Quality Judge reads outputs and documents. It evaluates.
    It does not write, modify, or execute.
    """

    handover_document_markdown: str
    checkpoint_definitions: list[str] = Field(default_factory=list)
    executor_output: Optional[ExecutorOutput] = None


class QualityJudgeOutput(BaseModel):
    """What the Quality Judge is allowed to produce.

    The Quality Judge produces verdicts and reports.
    It is structurally forbidden from modifying any artifact.
    """

    checkpoint_evaluations: list[CheckpointEvaluation] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    overall_quality_score: Optional[float] = None
    hitl_escalation_required: bool = False
    hitl_escalation_reason: Optional[str] = None
    methodology_compliance: dict[str, bool] = Field(
        default_factory=lambda: {"1": True, "2": True, "3": True, "4": True, "5": True}
    )

    # Forbidden: handover_modifications, code_execution, board_writes,
    # overriding human decisions, producing new handover content


# ---------------------------------------------------------------------------
# Compiler — extracts structured HandoverDocument from prose draft
# ---------------------------------------------------------------------------


class CompilerInput(BaseModel):
    draft_handover_markdown: str
    handover_id: str
    author: str


class CompilerOutput(BaseModel):
    handover: "HandoverDocument"
    compilation_warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Retro Analyst — read-only pattern extraction across handover corpus
# ---------------------------------------------------------------------------


class MetricsHistory(BaseModel):
    """Historical performance metrics for trend analysis."""

    metric_name: str
    values: list[tuple[str, float]]  # (sprint_label, value)
    unit: Optional[str] = None


class RetroAnalystInput(BaseModel):
    """Everything the Retro Analyst is allowed to see.

    The Retro Analyst is read-only across the entire handover corpus.
    It never writes, never modifies, never escalates — it only analyses.
    """

    handover_corpus_chunks: list[RAGChunk] = Field(default_factory=list)
    metrics_history: list[MetricsHistory] = Field(default_factory=list)
    velocity_data: list[VelocityRecord] = Field(default_factory=list)
    analysis_focus: Optional[str] = None


class VelocityTrend(BaseModel):
    """Velocity trend analysis output."""

    average_completion_rate: float
    trend_direction: Literal["improving", "stable", "declining", "insufficient_data"]
    sprints_analysed: int
    notes: Optional[str] = None


class RecurringPattern(BaseModel):
    """A pattern identified across multiple handover documents."""

    pattern_type: Literal["failure", "success", "anti_pattern", "risk"]
    description: str
    frequency: int
    example_handover_ids: list[str]
    recommendation: Optional[str] = None


class RetroAnalystOutput(BaseModel):
    """What the Retro Analyst is allowed to produce.

    Pure read — no writes of any kind to any system.
    All output is analysis and observation for human review.
    """

    pattern_report: list[RecurringPattern] = Field(default_factory=list)
    velocity_trend: Optional[VelocityTrend] = None
    retrospective_summary: str = ""
    handovers_analysed: int = 0
    top_risks: list[str] = Field(default_factory=list)
    top_successes: list[str] = Field(default_factory=list)

    # Forbidden: any write operation, document modification, board writes,
    # escalation, checkpoint evaluation — this agent is read-only


# ---------------------------------------------------------------------------
# Deferred import — resolve HandoverDocument forward reference in CompilerOutput
# ---------------------------------------------------------------------------

from alfred.schemas.handover import CritiqueEntry, HandoverDocument  # noqa: E402

PlannerInput.model_rebuild()
CompilerOutput.model_rebuild()
