"""Story proposal schemas — agent output + durable persistence row.

Phase 3 deliverable per ``docs/canonical/ALFRED_HANDOVER_10.md`` Task 1.

Two models live here, kept deliberately distinct so the agent-output
boundary stays narrow while the persistence layer carries the
traceability and approval-lifecycle slots Phase 4 will write into:

  - ``StoryProposal`` — the four kickoff-task contract fields (title,
    description, acceptance_criteria, story_points). Equivalent to what
    the story generator emits at the gate.
  - ``StoryProposalRecord`` — a persisted row: a ``StoryProposal`` plus
    a stable id, source ``handover_id`` and ``task_id``, timestamps, and
    an approval-status slot (``pending`` → ``approved`` → ``written``).

The approval-lifecycle fields exist as schema-level placeholders only.
Phase 3 writes records with ``approval_status="pending"``; Phase 4 owns
the transition to ``approved`` / ``written`` and the GitHub board write.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from alfred.schemas.agent import StoryPoint

ApprovalStatus = Literal["pending", "approved", "written"]


class StoryProposal(BaseModel):
    """Agent-output shape for a single proposed story.

    Mirrors the kickoff task contract in
    ``docs/active/KICKOFF_HANDOVER_OUTLINE.md``: every proposal carries a
    title, a one-line description, 2–3 acceptance-criteria bullets, and a
    story-point estimate. No ids, no approval state — that's the
    persistence layer's job.
    """

    title: str
    description: str
    acceptance_criteria: list[str]
    story_points: StoryPoint


def _new_proposed_story_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.utcnow()


class StoryProposalRecord(BaseModel):
    """Persisted-row shape for a proposed story.

    Adds a stable id, source linkage, timestamps, and approval-lifecycle
    slots to a ``StoryProposal``. The persistence layer (Phase 3 Task 2)
    stores instances of this model; the gate-review surface (Phase 3
    Task 4) reads them back without re-invoking the story generator.
    """

    proposed_story_id: str = Field(default_factory=_new_proposed_story_id)
    handover_id: str
    task_id: str

    title: str
    description: str
    acceptance_criteria: list[str]
    story_points: StoryPoint

    approval_status: ApprovalStatus = "pending"
    approval_decision_id: Optional[str] = None

    created_at: datetime = Field(default_factory=_utcnow)
    approved_at: Optional[datetime] = None
    written_at: Optional[datetime] = None

    @classmethod
    def from_proposal(
        cls,
        proposal: StoryProposal,
        *,
        handover_id: str,
        task_id: str,
        proposed_story_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> "StoryProposalRecord":
        """Build a persistence record from an agent proposal + linkage.

        ``proposed_story_id`` and ``created_at`` are auto-generated when
        omitted so callers can stay terse; tests pass explicit values to
        get deterministic output.
        """
        return cls(
            proposed_story_id=proposed_story_id or _new_proposed_story_id(),
            handover_id=handover_id,
            task_id=task_id,
            title=proposal.title,
            description=proposal.description,
            acceptance_criteria=list(proposal.acceptance_criteria),
            story_points=proposal.story_points,
            created_at=created_at or _utcnow(),
        )
