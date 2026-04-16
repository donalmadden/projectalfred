"""
Checkpoint and decision table schemas.

Checkpoints are first-class objects that enforce methodology property 2:
checkpoint-gated execution with deterministic decision tables.

The `escalate` verdict is property 2 in action: it means "a human must decide."
Alfred surfaces the evidence and the decision table; the human decides.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Verdict — the four possible outcomes of a checkpoint evaluation
# ---------------------------------------------------------------------------

Verdict = Literal["proceed", "pivot", "stop", "escalate"]

# ---------------------------------------------------------------------------
# Decision table
# ---------------------------------------------------------------------------


class DecisionRule(BaseModel):
    """One row in a checkpoint decision table.

    Maps an observed condition to a recommended verdict.
    Conditions are human-readable, not code — they describe what the executor
    should look for in the evidence (e.g., "balanced accuracy > 63%").
    """

    condition: str
    likely_verdict: Verdict


class DecisionTable(BaseModel):
    """An explicit, deterministic decision table for a checkpoint.

    No fuzzy evaluation — the checkpoint either passes or it doesn't.
    The `escalate` verdict means the evidence is ambiguous and a human must decide.
    """

    rules: list[DecisionRule] = Field(default_factory=list)
    default_verdict: Verdict = "stop"

    def evaluate(self, condition_label: str) -> Verdict:
        """Look up a verdict by exact condition label match.

        For structured evaluation in tests. Real evaluation happens via
        the Quality Judge agent reading the evidence and matching conditions.
        """
        for rule in self.rules:
            if rule.condition.lower() == condition_label.lower():
                return rule.likely_verdict
        return self.default_verdict


# ---------------------------------------------------------------------------
# Checkpoint result — populated after evaluation (post-execution)
# ---------------------------------------------------------------------------


class CheckpointResult(BaseModel):
    """The evaluated outcome of a checkpoint gate.

    Populated by the Quality Judge agent after reviewing executor output.
    The executor MUST paste evidence verbatim; the judge evaluates it.
    """

    verdict: Verdict
    evidence_provided: str
    reasoning: str


# ---------------------------------------------------------------------------
# Checkpoint — the gate itself
# ---------------------------------------------------------------------------


class Checkpoint(BaseModel):
    """An explicit decision gate within a task.

    Each checkpoint decides a single question. The executor stops, pastes
    evidence, and waits. The Quality Judge (or human) evaluates the evidence
    against the decision table and returns a verdict.

    The checkpoint is the unit of methodology property 2:
    deterministic, explicit, non-emergent.
    """

    id: str  # e.g. "CHECKPOINT-1", "CHECKPOINT-3"
    question: str  # one sentence: what this checkpoint decides
    evidence_required: str  # what the executor must provide
    decision_table: DecisionTable = Field(default_factory=DecisionTable)

    # Populated after evaluation
    result: Optional[CheckpointResult] = None

    @property
    def is_evaluated(self) -> bool:
        return self.result is not None

    @property
    def verdict(self) -> Optional[Verdict]:
        return self.result.verdict if self.result else None


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def create_checkpoint(
    checkpoint_id: str,
    question: str,
    evidence_required: str,
    rules: list[tuple[str, Verdict]],
    default_verdict: Verdict = "stop",
) -> Checkpoint:
    """Convenience factory for constructing a checkpoint with inline rules.

    Args:
        checkpoint_id: e.g. "CHECKPOINT-1"
        question: single-sentence description of what this gate decides
        evidence_required: what the executor must paste verbatim
        rules: list of (condition_text, verdict) pairs
        default_verdict: verdict when no rule matches

    Example::

        cp = create_checkpoint(
            "CHECKPOINT-1",
            "Whether the dataset reverted to pos115 only",
            "Paste output of the verification script",
            [
                ("Positions == ['115']", "proceed"),
                ("pos235 still present", "stop"),
            ],
        )
    """
    decision_rules = [DecisionRule(condition=c, likely_verdict=v) for c, v in rules]
    table = DecisionTable(rules=decision_rules, default_verdict=default_verdict)
    return Checkpoint(
        id=checkpoint_id,
        question=question,
        evidence_required=evidence_required,
        decision_table=table,
    )
