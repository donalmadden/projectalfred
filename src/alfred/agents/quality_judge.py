"""
Quality Judge — evaluates checkpoints and emits verdicts; never modifies artifacts.

Decision-table architecture (methodology property 2 — checkpoint-gated execution):
  Each checkpoint definition is a JSON-encoded decision table with rows of the form
  {"observation": <description>, "verdict": "proceed|pivot|stop|escalate"}.
  The LLM classifies which observation row best matches the executor output.
  The verdict is then looked up from the matched row — the LLM never decides the verdict.
  Falls through to "escalate" when no row matches.

Checkpoint definition JSON schema:
  {
    "checkpoint_id": "CHECKPOINT-1",
    "rows": [
      {"observation": "<natural-language description>", "verdict": "proceed"},
      ...
    ]
  }
"""
from __future__ import annotations

import json
from typing import Literal, Optional

from pydantic import BaseModel

from alfred.schemas.agent import (
    CheckpointEvaluation,
    QualityJudgeInput,
    QualityJudgeOutput,
    ValidationIssue,
)
from alfred.tools import llm

Verdict = Literal["proceed", "pivot", "stop", "escalate"]

# ---------------------------------------------------------------------------
# Internal schemas for LLM classification step
# ---------------------------------------------------------------------------


class _ObservationMatch(BaseModel):
    """LLM output: which observation row best matches the executor output."""

    matched_index: int  # 0-based index into the decision table rows; -1 = no match
    reasoning: str


class _DecisionRow(BaseModel):
    observation: str
    verdict: Verdict


class _DecisionTable(BaseModel):
    checkpoint_id: str
    rows: list[_DecisionRow]


# ---------------------------------------------------------------------------
# Decision table parsing
# ---------------------------------------------------------------------------


def _parse_decision_table(definition: str) -> Optional[_DecisionTable]:
    """Parse a checkpoint definition string into a decision table.

    Accepts JSON-encoded _DecisionTable. Returns None if unparseable.
    """
    try:
        data = json.loads(definition)
        return _DecisionTable.model_validate(data)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Single-checkpoint evaluation
# ---------------------------------------------------------------------------


def _evaluate_checkpoint(
    table: _DecisionTable,
    executor_output_text: str,
    provider: str,
    model: str,
    db_path: Optional[str],
) -> CheckpointEvaluation:
    if not table.rows:
        return CheckpointEvaluation(
            checkpoint_id=table.checkpoint_id,
            verdict="escalate",
            evidence_summary=executor_output_text[:500],
            reasoning="Decision table has no rows; cannot evaluate.",
            human_review_required=True,
        )

    observations_block = "\n".join(
        f"{i}. {row.observation}" for i, row in enumerate(table.rows)
    )
    prompt = (
        f"You are classifying executor output against a decision table.\n\n"
        f"EXECUTOR OUTPUT:\n{executor_output_text}\n\n"
        f"OBSERVATIONS (pick the best match by index, or -1 if none fit):\n"
        f"{observations_block}\n\n"
        f"Return the index of the best-matching observation and a one-sentence reasoning."
    )

    match = llm.complete(
        prompt,
        _ObservationMatch,
        provider=provider,
        model=model,
        db_path=db_path,
    )

    idx = match.matched_index
    if 0 <= idx < len(table.rows):
        verdict: Verdict = table.rows[idx].verdict
        observation_text = table.rows[idx].observation
    else:
        verdict = "escalate"
        observation_text = "(no matching observation)"

    return CheckpointEvaluation(
        checkpoint_id=table.checkpoint_id,
        verdict=verdict,
        evidence_summary=executor_output_text[:500],
        reasoning=f"Matched observation [{idx}]: {observation_text}. {match.reasoning}",
        human_review_required=(verdict in ("stop", "escalate")),
    )


# ---------------------------------------------------------------------------
# Methodology compliance heuristics (deterministic — no LLM)
# ---------------------------------------------------------------------------

_METHODOLOGY_SIGNALS = {
    "1": ["handover", "document", "protocol"],
    "2": ["checkpoint", "verdict", "gate"],
    "3": ["executor", "reviewer", "isolation"],
    "4": ["post-mortem", "forward plan", "failure analysis"],
    "5": ["cold-start", "stateless", "session"],
}


def _check_methodology_compliance(markdown: str) -> dict[str, bool]:
    # scan `markdown` only — never executor output
    lower = markdown.lower()
    return {
        prop: any(kw in lower for kw in keywords)
        for prop, keywords in _METHODOLOGY_SIGNALS.items()
    }


# ---------------------------------------------------------------------------
# Validation issues (deterministic scan)
# ---------------------------------------------------------------------------


def _find_validation_issues(
    markdown: str, evaluations: list[CheckpointEvaluation]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if "## checkpoint" not in markdown.lower():
        issues.append(
            ValidationIssue(
                severity="warning",
                property_violated="2",
                section="PREAMBLE",
                description="No checkpoint sections found in handover document.",
            )
        )

    for ev in evaluations:
        if ev.verdict == "stop":
            issues.append(
                ValidationIssue(
                    severity="error",
                    property_violated=None,
                    section=ev.checkpoint_id,
                    description=f"STOP verdict at {ev.checkpoint_id}: {ev.reasoning[:200]}",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_quality_judge(
    input: QualityJudgeInput,
    *,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
    db_path: Optional[str] = None,
    task_type: str = "judge",
    config: Optional[object] = None,
) -> QualityJudgeOutput:
    """Evaluate checkpoints and produce verdicts. Never modifies any artifact.

    task_type controls model-tier routing when config is supplied:
      "judge"    → classifier (cheap) tier — default for checkpoint evaluation
      "critique" → generator (expensive) tier — used in the critique loop
    """
    from alfred.tools.llm import resolve_model as _resolve_model

    if config is not None:
        provider, model = _resolve_model(task_type, config)

    executor_text = ""
    if input.executor_output is not None:
        eo = input.executor_output
        executor_text = (
            f"Task: {eo.task_id}\n"
            f"Output:\n{eo.console_output}\n"
            f"Files modified: {', '.join(eo.files_modified) or 'none'}\n"
            f"Metrics: {json.dumps(eo.metrics)}"
        )

    evaluations: list[CheckpointEvaluation] = []
    for definition in input.checkpoint_definitions:
        table = _parse_decision_table(definition)
        if table is None:
            evaluations.append(
                CheckpointEvaluation(
                    checkpoint_id="UNKNOWN",
                    verdict="escalate",
                    evidence_summary="",
                    reasoning="Could not parse checkpoint definition as a decision table.",
                    human_review_required=True,
                )
            )
            continue
        evaluations.append(
            _evaluate_checkpoint(table, executor_text, provider, model, db_path)
        )

    validation_issues = _find_validation_issues(
        input.handover_document_markdown, evaluations
    )
    methodology_compliance = _check_methodology_compliance(
        input.handover_document_markdown
    )

    verdicts = [ev.verdict for ev in evaluations]
    hitl_required = any(v in ("stop", "escalate") for v in verdicts)
    hitl_reason: Optional[str] = None
    if hitl_required:
        blocking = [ev for ev in evaluations if ev.verdict in ("stop", "escalate")]
        hitl_reason = "; ".join(
            f"{ev.checkpoint_id}={ev.verdict}" for ev in blocking
        )

    score: Optional[float] = None
    if evaluations:
        weights = {"proceed": 1.0, "pivot": 0.5, "escalate": 0.25, "stop": 0.0}
        score = sum(weights.get(v, 0.0) for v in verdicts) / len(verdicts)

    return QualityJudgeOutput(
        checkpoint_evaluations=evaluations,
        validation_issues=validation_issues,
        overall_quality_score=score,
        hitl_escalation_required=hitl_required,
        hitl_escalation_reason=hitl_reason,
        methodology_compliance=methodology_compliance,
    )
