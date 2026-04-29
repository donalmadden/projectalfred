"""Tests for ``alfred.schemas.story_proposal``."""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from alfred.schemas.story_proposal import (
    ApprovalStatus,
    StoryProposal,
    StoryProposalRecord,
)


def _proposal(**overrides) -> StoryProposal:
    return StoryProposal.model_validate(
        {
            "title": "Define onboarding journey",
            "description": "End-to-end onboarding flow.",
            "acceptance_criteria": ["bullet a", "bullet b"],
            "story_points": 5,
            **overrides,
        }
    )


# ---------------------------------------------------------------------------
# StoryProposal — agent-output boundary
# ---------------------------------------------------------------------------


def test_story_proposal_round_trips() -> None:
    proposal = _proposal()
    payload = proposal.model_dump()
    assert payload["title"] == "Define onboarding journey"
    assert payload["acceptance_criteria"] == ["bullet a", "bullet b"]
    rebuilt = StoryProposal.model_validate(payload)
    assert rebuilt == proposal


def test_story_proposal_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        StoryProposal.model_validate(
            {"title": "x", "description": "y", "acceptance_criteria": ["a"]}
        )


def test_story_proposal_rejects_non_list_acceptance_criteria() -> None:
    with pytest.raises(ValidationError):
        _proposal(acceptance_criteria="single string not list")


def test_story_proposal_constrains_story_points_to_fibonacci() -> None:
    with pytest.raises(ValidationError):
        _proposal(story_points=4)
    with pytest.raises(ValidationError):
        _proposal(story_points=0)
    for valid in (1, 2, 3, 5, 8, 13):
        _proposal(story_points=valid)


# ---------------------------------------------------------------------------
# StoryProposalRecord — persistence row
# ---------------------------------------------------------------------------


def test_record_defaults_status_to_pending_and_generates_id() -> None:
    record = StoryProposalRecord(
        handover_id="ALFRED_HANDOVER_1",
        task_id="TASK-SEED-BOARD-001",
        title="x",
        description="y",
        acceptance_criteria=["a", "b"],
        story_points=3,
    )
    assert record.approval_status == "pending"
    assert record.approval_decision_id is None
    assert record.approved_at is None
    assert record.written_at is None
    assert isinstance(record.proposed_story_id, str)
    assert len(record.proposed_story_id) == 32  # uuid4 hex
    assert isinstance(record.created_at, datetime)


def test_record_unique_ids_across_instances() -> None:
    a = StoryProposalRecord(
        handover_id="H1",
        task_id="T",
        title="x",
        description="y",
        acceptance_criteria=["a", "b"],
        story_points=1,
    )
    b = StoryProposalRecord(
        handover_id="H1",
        task_id="T",
        title="x",
        description="y",
        acceptance_criteria=["a", "b"],
        story_points=1,
    )
    assert a.proposed_story_id != b.proposed_story_id


def test_record_accepts_explicit_approval_status_transitions() -> None:
    for status in ("pending", "approved", "written"):
        record = StoryProposalRecord(
            handover_id="H",
            task_id="T",
            title="x",
            description="y",
            acceptance_criteria=["a", "b"],
            story_points=1,
            approval_status=status,  # type: ignore[arg-type]
        )
        assert record.approval_status == status


def test_record_rejects_unknown_approval_status() -> None:
    with pytest.raises(ValidationError):
        StoryProposalRecord(
            handover_id="H",
            task_id="T",
            title="x",
            description="y",
            acceptance_criteria=["a", "b"],
            story_points=1,
            approval_status="rejected",  # type: ignore[arg-type]
        )


def test_record_round_trips_with_lifecycle_fields_set() -> None:
    now = datetime(2026, 4, 30, 12, 0, 0)
    record = StoryProposalRecord(
        proposed_story_id="aaaa",
        handover_id="ALFRED_HANDOVER_1",
        task_id="TASK-SEED-BOARD-001",
        title="x",
        description="y",
        acceptance_criteria=["a", "b"],
        story_points=8,
        approval_status="approved",
        approval_decision_id="decision-7",
        created_at=now,
        approved_at=now,
    )
    payload = record.model_dump()
    rebuilt = StoryProposalRecord.model_validate(payload)
    assert rebuilt == record


# ---------------------------------------------------------------------------
# from_proposal helper
# ---------------------------------------------------------------------------


def test_from_proposal_carries_fields_and_adds_linkage() -> None:
    proposal = _proposal()
    record = StoryProposalRecord.from_proposal(
        proposal,
        handover_id="ALFRED_HANDOVER_1",
        task_id="TASK-SEED-BOARD-001",
    )
    assert record.title == proposal.title
    assert record.description == proposal.description
    assert record.acceptance_criteria == proposal.acceptance_criteria
    assert record.story_points == proposal.story_points
    assert record.handover_id == "ALFRED_HANDOVER_1"
    assert record.task_id == "TASK-SEED-BOARD-001"
    assert record.approval_status == "pending"


def test_from_proposal_uses_explicit_id_and_timestamp_when_supplied() -> None:
    proposal = _proposal()
    when = datetime(2026, 4, 30, 9, 0, 0)
    record = StoryProposalRecord.from_proposal(
        proposal,
        handover_id="H",
        task_id="T",
        proposed_story_id="fixed-id",
        created_at=when,
    )
    assert record.proposed_story_id == "fixed-id"
    assert record.created_at == when


def test_from_proposal_copies_acceptance_criteria_list() -> None:
    """The record should not alias the proposal's list — mutating one
    must not mutate the other."""
    proposal = _proposal(acceptance_criteria=["a", "b"])
    record = StoryProposalRecord.from_proposal(
        proposal, handover_id="H", task_id="T"
    )
    proposal.acceptance_criteria.append("c")
    assert record.acceptance_criteria == ["a", "b"]


def test_approval_status_literal_matches_module_alias() -> None:
    """Sanity check the Literal members the persistence layer will rely on."""
    record = StoryProposalRecord(
        handover_id="H",
        task_id="T",
        title="x",
        description="y",
        acceptance_criteria=["a", "b"],
        story_points=1,
    )
    valid_states: tuple[ApprovalStatus, ...] = ("pending", "approved", "written")
    assert record.approval_status in valid_states
