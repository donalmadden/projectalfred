"""Phase 4 Task 1 — approval->write contract tests.

Establishes the gating preconditions and lifecycle invariants the Phase 4
write step must obey. No GitHub calls; no orchestrator wiring.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from alfred.schemas.story_proposal import StoryProposal, StoryProposalRecord
from alfred.tools import persistence
from alfred.tools.board_write_contract import (
    BOARD_WRITE_ACTION,
    ApprovalRequiredError,
    InvalidLifecycleTransitionError,
    find_matching_approval_id,
    gate_board_write,
    mark_proposal_approved,
    mark_proposal_written,
    select_writeable_proposals,
)

HANDOVER_ID = "ALFRED_HANDOVER_11"
TASK_ID = "TASK-SEED-BOARD-001"


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "alfred.db")


def _proposal(title: str) -> StoryProposal:
    return StoryProposal(
        title=title,
        description=f"{title} — description.",
        acceptance_criteria=["bullet a", "bullet b"],
        story_points=3,
    )


def _seed_proposals(db_path: str, n: int = 6) -> list[StoryProposalRecord]:
    records = [
        StoryProposalRecord.from_proposal(
            _proposal(f"Story {i}"),
            handover_id=HANDOVER_ID,
            task_id=TASK_ID,
        )
        for i in range(n)
    ]
    persistence.insert_story_proposals(db_path, records)
    return records


def _create_approval(
    db_path: str,
    *,
    approval_id: str = "approval-1",
    handover_id: str = HANDOVER_ID,
    item_id: str = TASK_ID,
    action_type: str = BOARD_WRITE_ACTION,
    decision: str | None = "approved",
) -> str:
    persistence.create_pending_approval(
        db_path,
        approval_id=approval_id,
        handover_id=handover_id,
        action_type=action_type,
        item_id=item_id,
        timeout_seconds=3600,
    )
    if decision is not None:
        persistence.record_approval_decision(db_path, approval_id, decision)
    return approval_id


# ---------------------------------------------------------------------------
# Linkage / gating
# ---------------------------------------------------------------------------


def test_gate_refuses_when_no_approval_record(db_path: str) -> None:
    _seed_proposals(db_path)
    with pytest.raises(ApprovalRequiredError):
        gate_board_write(db_path, handover_id=HANDOVER_ID, task_id=TASK_ID)


def test_gate_refuses_when_approval_pending(db_path: str) -> None:
    _seed_proposals(db_path)
    _create_approval(db_path, decision=None)
    with pytest.raises(ApprovalRequiredError):
        gate_board_write(db_path, handover_id=HANDOVER_ID, task_id=TASK_ID)


def test_gate_refuses_when_approval_rejected(db_path: str) -> None:
    _seed_proposals(db_path)
    _create_approval(db_path, decision="rejected")
    with pytest.raises(ApprovalRequiredError):
        gate_board_write(db_path, handover_id=HANDOVER_ID, task_id=TASK_ID)


def test_gate_refuses_when_action_type_mismatches(db_path: str) -> None:
    """An approval for a different action does not unlock board writes."""
    _seed_proposals(db_path)
    _create_approval(db_path, action_type="story_creation")
    with pytest.raises(ApprovalRequiredError):
        gate_board_write(db_path, handover_id=HANDOVER_ID, task_id=TASK_ID)


def test_gate_refuses_when_handover_mismatches(db_path: str) -> None:
    _seed_proposals(db_path)
    _create_approval(db_path, handover_id="ALFRED_HANDOVER_OTHER")
    with pytest.raises(ApprovalRequiredError):
        gate_board_write(db_path, handover_id=HANDOVER_ID, task_id=TASK_ID)


def test_gate_returns_batch_when_approved(db_path: str) -> None:
    seeded = _seed_proposals(db_path, n=7)
    approval_id = _create_approval(db_path)

    returned_id, batch = gate_board_write(
        db_path, handover_id=HANDOVER_ID, task_id=TASK_ID
    )

    assert returned_id == approval_id
    assert [r.proposed_story_id for r in batch] == [
        r.proposed_story_id for r in seeded
    ]
    assert all(r.approval_status == "pending" for r in batch)


def test_find_matching_approval_id_returns_none_without_match(db_path: str) -> None:
    assert (
        find_matching_approval_id(db_path, handover_id=HANDOVER_ID, task_id=TASK_ID)
        is None
    )


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def test_mark_approved_sets_status_and_approval_id(db_path: str) -> None:
    [record] = _seed_proposals(db_path, n=1)
    approval_id = _create_approval(db_path)

    mark_proposal_approved(
        db_path, proposed_story_id=record.proposed_story_id, approval_id=approval_id
    )

    [updated] = persistence.list_story_proposals(
        db_path, handover_id=HANDOVER_ID, task_id=TASK_ID
    )
    assert updated.approval_status == "approved"
    assert updated.approval_decision_id == approval_id
    assert updated.approved_at is not None
    assert updated.written_at is None


def test_mark_approved_rejects_non_pending_status(db_path: str) -> None:
    [record] = _seed_proposals(db_path, n=1)
    approval_id = _create_approval(db_path)
    mark_proposal_approved(
        db_path, proposed_story_id=record.proposed_story_id, approval_id=approval_id
    )

    with pytest.raises(InvalidLifecycleTransitionError):
        mark_proposal_approved(
            db_path,
            proposed_story_id=record.proposed_story_id,
            approval_id=approval_id,
        )


def test_mark_written_requires_approved_status(db_path: str) -> None:
    [record] = _seed_proposals(db_path, n=1)

    # pending -> written is forbidden
    with pytest.raises(InvalidLifecycleTransitionError):
        mark_proposal_written(db_path, proposed_story_id=record.proposed_story_id)


def test_mark_written_transitions_from_approved(db_path: str) -> None:
    [record] = _seed_proposals(db_path, n=1)
    approval_id = _create_approval(db_path)
    mark_proposal_approved(
        db_path, proposed_story_id=record.proposed_story_id, approval_id=approval_id
    )

    mark_proposal_written(db_path, proposed_story_id=record.proposed_story_id)

    [updated] = persistence.list_story_proposals(db_path)
    assert updated.approval_status == "written"
    assert updated.written_at is not None


def test_mark_written_rejects_double_write(db_path: str) -> None:
    [record] = _seed_proposals(db_path, n=1)
    approval_id = _create_approval(db_path)
    mark_proposal_approved(
        db_path, proposed_story_id=record.proposed_story_id, approval_id=approval_id
    )
    mark_proposal_written(db_path, proposed_story_id=record.proposed_story_id)

    with pytest.raises(InvalidLifecycleTransitionError):
        mark_proposal_written(db_path, proposed_story_id=record.proposed_story_id)


# ---------------------------------------------------------------------------
# Story content immutability
# ---------------------------------------------------------------------------


def test_transitions_do_not_mutate_story_content(db_path: str) -> None:
    seeded = _seed_proposals(db_path, n=3)
    approval_id = _create_approval(db_path)
    for rec in seeded:
        mark_proposal_approved(
            db_path, proposed_story_id=rec.proposed_story_id, approval_id=approval_id
        )
    for rec in seeded:
        mark_proposal_written(db_path, proposed_story_id=rec.proposed_story_id)

    after = {
        r.proposed_story_id: r
        for r in persistence.list_story_proposals(db_path)
    }
    for original in seeded:
        post = after[original.proposed_story_id]
        assert post.title == original.title
        assert post.description == original.description
        assert post.acceptance_criteria == original.acceptance_criteria
        assert post.story_points == original.story_points


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_select_writeable_excludes_already_written(db_path: str) -> None:
    seeded = _seed_proposals(db_path, n=3)
    approval_id = _create_approval(db_path)
    for rec in seeded:
        mark_proposal_approved(
            db_path, proposed_story_id=rec.proposed_story_id, approval_id=approval_id
        )
    # Simulate partial-failure: only first two get written.
    mark_proposal_written(db_path, proposed_story_id=seeded[0].proposed_story_id)
    mark_proposal_written(db_path, proposed_story_id=seeded[1].proposed_story_id)

    pending = select_writeable_proposals(
        db_path, handover_id=HANDOVER_ID, task_id=TASK_ID
    )
    assert [r.proposed_story_id for r in pending] == [seeded[2].proposed_story_id]


def test_gate_returns_only_unwritten_after_partial_run(db_path: str) -> None:
    seeded = _seed_proposals(db_path, n=2)
    approval_id = _create_approval(db_path)
    for rec in seeded:
        mark_proposal_approved(
            db_path, proposed_story_id=rec.proposed_story_id, approval_id=approval_id
        )
    mark_proposal_written(db_path, proposed_story_id=seeded[0].proposed_story_id)

    returned_id, batch = gate_board_write(
        db_path, handover_id=HANDOVER_ID, task_id=TASK_ID
    )

    assert returned_id == approval_id
    assert [r.proposed_story_id for r in batch] == [seeded[1].proposed_story_id]
