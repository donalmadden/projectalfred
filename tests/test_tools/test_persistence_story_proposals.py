"""Tests for story proposal persistence in ``alfred.tools.persistence``."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from alfred.schemas.story_proposal import StoryProposal, StoryProposalRecord
from alfred.tools import persistence


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "alfred.db")


def _proposal(title: str = "Define onboarding journey") -> StoryProposal:
    return StoryProposal(
        title=title,
        description="End-to-end onboarding flow.",
        acceptance_criteria=["bullet a", "bullet b"],
        story_points=5,
    )


def _record(
    title: str = "x",
    *,
    handover_id: str = "ALFRED_HANDOVER_1",
    task_id: str = "TASK-SEED-BOARD-001",
    proposed_story_id: str | None = None,
    created_at: datetime | None = None,
) -> StoryProposalRecord:
    return StoryProposalRecord.from_proposal(
        _proposal(title),
        handover_id=handover_id,
        task_id=task_id,
        proposed_story_id=proposed_story_id,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------


def test_connect_creates_story_proposals_table(db_path: str) -> None:
    persistence.list_story_proposals(db_path)  # triggers _connect
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='story_proposals'"
        ).fetchone()
    assert row is not None


# ---------------------------------------------------------------------------
# Insert + list
# ---------------------------------------------------------------------------


def test_insert_then_list_returns_same_records(db_path: str) -> None:
    records = [
        _record("first", proposed_story_id="aaa", created_at=datetime(2026, 4, 30, 9)),
        _record("second", proposed_story_id="bbb", created_at=datetime(2026, 4, 30, 10)),
    ]
    persistence.insert_story_proposals(db_path, records)

    listed = persistence.list_story_proposals(db_path)
    assert [r.proposed_story_id for r in listed] == ["aaa", "bbb"]
    assert [r.title for r in listed] == ["first", "second"]
    assert all(r.acceptance_criteria == ["bullet a", "bullet b"] for r in listed)
    assert all(r.story_points == 5 for r in listed)
    assert all(r.approval_status == "pending" for r in listed)


def test_list_filters_by_handover_and_task(db_path: str) -> None:
    persistence.insert_story_proposals(
        db_path,
        [
            _record("h1-t1", handover_id="H1", task_id="T1", proposed_story_id="1"),
            _record("h1-t2", handover_id="H1", task_id="T2", proposed_story_id="2"),
            _record("h2-t1", handover_id="H2", task_id="T1", proposed_story_id="3"),
        ],
    )
    h1 = persistence.list_story_proposals(db_path, handover_id="H1")
    assert {r.proposed_story_id for r in h1} == {"1", "2"}

    h1_t1 = persistence.list_story_proposals(db_path, handover_id="H1", task_id="T1")
    assert [r.proposed_story_id for r in h1_t1] == ["1"]

    none = persistence.list_story_proposals(db_path, handover_id="missing")
    assert none == []


def test_list_persists_across_connections(db_path: str) -> None:
    """The "no regeneration across gate" requirement: a second invocation
    against the same DB path must return the previously inserted rows
    without any agent call."""
    persistence.insert_story_proposals(
        db_path, [_record("first", proposed_story_id="aaa")]
    )

    # Simulate a separate process: nothing in memory, just reopen.
    listed = persistence.list_story_proposals(db_path)
    assert [r.proposed_story_id for r in listed] == ["aaa"]


def test_insert_empty_list_is_noop(db_path: str) -> None:
    persistence.insert_story_proposals(db_path, [])
    assert persistence.list_story_proposals(db_path) == []


def test_insert_duplicate_id_raises(db_path: str) -> None:
    record = _record("first", proposed_story_id="dup")
    persistence.insert_story_proposals(db_path, [record])
    with pytest.raises(sqlite3.IntegrityError):
        persistence.insert_story_proposals(db_path, [record])


def test_insert_round_trips_acceptance_criteria_and_points(db_path: str) -> None:
    record = StoryProposalRecord(
        proposed_story_id="abc",
        handover_id="H",
        task_id="T",
        title="x",
        description="y",
        acceptance_criteria=["α", "β with comma, here", "γ"],
        story_points=13,
    )
    persistence.insert_story_proposals(db_path, [record])
    listed = persistence.list_story_proposals(db_path)
    assert listed[0].acceptance_criteria == ["α", "β with comma, here", "γ"]
    assert listed[0].story_points == 13


# ---------------------------------------------------------------------------
# Status updates
# ---------------------------------------------------------------------------


def test_update_status_to_approved_sets_approved_at(db_path: str) -> None:
    persistence.insert_story_proposals(db_path, [_record(proposed_story_id="aaa")])

    persistence.update_story_proposal_status(
        db_path, "aaa", "approved", approval_decision_id="decision-7"
    )

    listed = persistence.list_story_proposals(db_path)
    assert listed[0].approval_status == "approved"
    assert listed[0].approval_decision_id == "decision-7"
    assert listed[0].approved_at is not None
    assert listed[0].written_at is None


def test_update_status_to_written_sets_written_at(db_path: str) -> None:
    persistence.insert_story_proposals(db_path, [_record(proposed_story_id="aaa")])
    persistence.update_story_proposal_status(db_path, "aaa", "written")
    listed = persistence.list_story_proposals(db_path)
    assert listed[0].approval_status == "written"
    assert listed[0].written_at is not None


def test_update_status_unknown_status_raises(db_path: str) -> None:
    persistence.insert_story_proposals(db_path, [_record(proposed_story_id="aaa")])
    with pytest.raises(ValueError, match="Invalid story proposal status"):
        persistence.update_story_proposal_status(db_path, "aaa", "rejected")  # type: ignore[arg-type]


def test_update_status_missing_id_raises(db_path: str) -> None:
    with pytest.raises(ValueError, match="not found"):
        persistence.update_story_proposal_status(db_path, "missing", "approved")


# ---------------------------------------------------------------------------
# Idempotency policy (Option A — append) verified
# ---------------------------------------------------------------------------


def test_appending_a_second_batch_with_new_ids_preserves_history(db_path: str) -> None:
    """Per module-level idempotency note: insert is append-only by id.
    A second batch with fresh ``proposed_story_id`` values lives
    alongside the first."""
    first = _record("first", proposed_story_id="aaa")
    persistence.insert_story_proposals(db_path, [first])

    second = _record("second", proposed_story_id="bbb")
    persistence.insert_story_proposals(db_path, [second])

    listed = persistence.list_story_proposals(db_path)
    assert {r.proposed_story_id for r in listed} == {"aaa", "bbb"}
