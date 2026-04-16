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

from alfred.schemas.checkpoint import Checkpoint, Verdict
from alfred.schemas.config import AlfredConfig
from alfred.schemas.handover import HandoverDocument, HandoverTask


class CheckpointHalt(Exception):
    """Raised when a checkpoint returns a STOP verdict."""


class HumanEscalation(Exception):
    """Raised when a checkpoint returns an ESCALATE verdict requiring human decision."""


def orchestrate(handover: HandoverDocument, config: AlfredConfig) -> HandoverDocument:
    """
    Execute a handover document.

    Iterates through tasks in order. For each task:
      1. Constructs agent input from HandoverDocument + tools
      2. Calls the appropriate agent (Planner / Story Generator / Retro Analyst)
      3. Validates output against the agent's output schema (Pydantic enforces this)
      4. If the task has checkpoints: calls Quality Judge
      5. Routes based on verdict (proceed / pivot / stop / escalate)
      6. Writes results back to the HandoverDocument before proceeding

    Returns the updated HandoverDocument with results filled in.
    Raises CheckpointHalt on STOP verdict.
    Raises HumanEscalation on ESCALATE verdict.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Control-flow primitives — skeleton helpers that Phase 4 will implement.
# They exist here so the shape of checkpoint-gated execution is visible
# structurally, not just as prose in a docstring.
# ---------------------------------------------------------------------------


def _dispatch_task(task: HandoverTask, handover: HandoverDocument, config: AlfredConfig) -> None:
    """Route a task to the correct agent based on its role.

    Phase 4 will resolve the agent from task metadata and invoke it with a
    Pydantic-validated input constructed from the handover document plus tool
    reads (board state, RAG retrieval, velocity history).
    """
    raise NotImplementedError


def _evaluate_checkpoints(task: HandoverTask, handover: HandoverDocument, config: AlfredConfig) -> Verdict:
    """Run Quality Judge over a task's checkpoints and return the aggregate verdict.

    A task with no checkpoints implicitly proceeds. A task with multiple
    checkpoints aggregates verdicts using the most restrictive rule
    (stop > escalate > pivot > proceed).
    """
    raise NotImplementedError


def _route_on_verdict(verdict: Verdict, checkpoint: Checkpoint, handover: HandoverDocument) -> None:
    """Apply the control-flow consequence of a verdict.

    proceed  — return to the caller; the next task runs
    pivot    — record the pivot on the handover and continue with the revised plan
    stop     — write the failure to handover.post_mortem and raise CheckpointHalt
    escalate — mark the handover for human review and raise HumanEscalation
    """
    raise NotImplementedError
