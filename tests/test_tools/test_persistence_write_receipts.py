"""Phase 4 Task 2 — write-receipt persistence tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from alfred.schemas.story_proposal import StoryProposal, StoryProposalRecord
from alfred.tools import persistence

HANDOVER_ID = "ALFRED_HANDOVER_11"
TASK_ID = "TASK-SEED-BOARD-001"


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "alfred.db")


def _seed_record(db_path: str, *, title: str = "Story 1") -> StoryProposalRecord:
    record = StoryProposalRecord.from_proposal(
        StoryProposal(
            title=title,
            description=f"{title} — description.",
            acceptance_criteria=["a", "b"],
            story_points=3,
        ),
        handover_id=HANDOVER_ID,
        task_id=TASK_ID,
    )
    persistence.insert_story_proposals(db_path, [record])
    return record


def _approve(db_path: str, proposed_story_id: str, approval_id: str) -> None:
    persistence.update_story_proposal_status(
        db_path,
        proposed_story_id,
        "approved",
        approval_decision_id=approval_id,
    )


def test_get_write_receipt_returns_none_when_absent(db_path: str) -> None:
    record = _seed_record(db_path)
    assert persistence.get_write_receipt(db_path, record.proposed_story_id) is None


def test_record_proposal_write_creates_receipt_and_marks_written(db_path: str) -> None:
    record = _seed_record(db_path)
    _approve(db_path, record.proposed_story_id, "approval-1")

    persistence.record_proposal_write(
        db_path,
        proposed_story_id=record.proposed_story_id,
        github_item_id="PVTI_xyz",
        github_title=record.title,
        approval_decision_id="approval-1",
    )

    receipt = persistence.get_write_receipt(db_path, record.proposed_story_id)
    assert receipt is not None
    assert receipt["github_item_id"] == "PVTI_xyz"
    assert receipt["github_title"] == record.title
    assert receipt["approval_decision_id"] == "approval-1"
    assert receipt["written_at"]

    [updated] = persistence.list_story_proposals(db_path)
    assert updated.approval_status == "written"
    assert updated.written_at is not None


def test_record_proposal_write_refuses_when_status_pending(db_path: str) -> None:
    record = _seed_record(db_path)

    with pytest.raises(ValueError, match="from status"):
        persistence.record_proposal_write(
            db_path,
            proposed_story_id=record.proposed_story_id,
            github_item_id="PVTI_xyz",
            github_title=record.title,
            approval_decision_id="approval-1",
        )

    assert persistence.get_write_receipt(db_path, record.proposed_story_id) is None
    [unchanged] = persistence.list_story_proposals(db_path)
    assert unchanged.approval_status == "pending"


def test_record_proposal_write_refuses_unknown_proposal(db_path: str) -> None:
    with pytest.raises(ValueError, match="not found"):
        persistence.record_proposal_write(
            db_path,
            proposed_story_id="does-not-exist",
            github_item_id="PVTI_xyz",
            github_title="x",
            approval_decision_id="approval-1",
        )


def test_record_proposal_write_refuses_duplicate(db_path: str) -> None:
    record = _seed_record(db_path)
    _approve(db_path, record.proposed_story_id, "approval-1")
    persistence.record_proposal_write(
        db_path,
        proposed_story_id=record.proposed_story_id,
        github_item_id="PVTI_xyz",
        github_title=record.title,
        approval_decision_id="approval-1",
    )

    # second call: status is now 'written' so it must refuse rather than dup
    with pytest.raises(ValueError):
        persistence.record_proposal_write(
            db_path,
            proposed_story_id=record.proposed_story_id,
            github_item_id="PVTI_other",
            github_title=record.title,
            approval_decision_id="approval-1",
        )

    receipt = persistence.get_write_receipt(db_path, record.proposed_story_id)
    assert receipt is not None
    assert receipt["github_item_id"] == "PVTI_xyz"


def test_list_write_receipts_filters_by_linkage(db_path: str) -> None:
    r1 = _seed_record(db_path, title="A")
    r2 = StoryProposalRecord.from_proposal(
        StoryProposal(
            title="B", description="b", acceptance_criteria=["x", "y"], story_points=2
        ),
        handover_id="ALFRED_HANDOVER_OTHER",
        task_id=TASK_ID,
    )
    persistence.insert_story_proposals(db_path, [r2])
    _approve(db_path, r1.proposed_story_id, "approval-1")
    _approve(db_path, r2.proposed_story_id, "approval-2")

    persistence.record_proposal_write(
        db_path,
        proposed_story_id=r1.proposed_story_id,
        github_item_id="PVTI_a",
        github_title="A",
        approval_decision_id="approval-1",
    )
    persistence.record_proposal_write(
        db_path,
        proposed_story_id=r2.proposed_story_id,
        github_item_id="PVTI_b",
        github_title="B",
        approval_decision_id="approval-2",
    )

    only_first = persistence.list_write_receipts(db_path, handover_id=HANDOVER_ID)
    assert [r["github_item_id"] for r in only_first] == ["PVTI_a"]

    all_receipts = persistence.list_write_receipts(db_path, task_id=TASK_ID)
    assert {r["github_item_id"] for r in all_receipts} == {"PVTI_a", "PVTI_b"}


def test_atomicity_failure_leaves_no_receipt(db_path: str) -> None:
    """If the precondition check fails, no receipt row is left behind."""
    record = _seed_record(db_path)
    # status = pending; record_proposal_write must raise *and* roll back.
    with pytest.raises(ValueError):
        persistence.record_proposal_write(
            db_path,
            proposed_story_id=record.proposed_story_id,
            github_item_id="PVTI_xyz",
            github_title=record.title,
            approval_decision_id="approval-1",
        )

    assert persistence.list_write_receipts(db_path) == []
