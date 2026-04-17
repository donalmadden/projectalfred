"""Tests for the SQLite persistence tool."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from alfred.schemas.agent import VelocityRecord
from alfred.tools import persistence


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "alfred.db")


def _record(sprint: int, committed: int = 10, completed: int = 8) -> VelocityRecord:
    return VelocityRecord(
        sprint_number=sprint,
        points_committed=committed,
        points_completed=completed,
        completion_rate=completed / committed,
    )


def test_bootstrap_is_idempotent(db_path: str) -> None:
    persistence.record_velocity(db_path, _record(1))
    persistence.record_velocity(db_path, _record(2))
    with sqlite3.connect(db_path) as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {
        "velocity",
        "agent_invocations",
        "checkpoint_history",
        "pending_approvals",
    } <= tables


def test_record_velocity_roundtrip(db_path: str) -> None:
    persistence.record_velocity(db_path, _record(1))
    history = persistence.get_velocity_history(db_path, sprint_count=10)
    assert len(history) == 1
    assert history[0].sprint_number == 1
    assert history[0].points_committed == 10
    assert history[0].completion_rate == pytest.approx(0.8)


def test_record_velocity_upsert(db_path: str) -> None:
    persistence.record_velocity(db_path, _record(1, committed=10, completed=5))
    persistence.record_velocity(db_path, _record(1, committed=10, completed=9))
    history = persistence.get_velocity_history(db_path, sprint_count=10)
    assert len(history) == 1
    assert history[0].points_completed == 9


def test_get_velocity_history_ordering_and_limit(db_path: str) -> None:
    for sprint in [1, 2, 3, 4, 5]:
        persistence.record_velocity(db_path, _record(sprint))
    history = persistence.get_velocity_history(db_path, sprint_count=3)
    assert [record.sprint_number for record in history] == [5, 4, 3]


def test_get_velocity_history_zero_returns_empty(db_path: str) -> None:
    persistence.record_velocity(db_path, _record(1))
    assert persistence.get_velocity_history(db_path, sprint_count=0) == []


def test_record_agent_invocation(db_path: str) -> None:
    row_id = persistence.record_agent_invocation(
        db_path,
        agent_name="planner",
        input_hash="abc123",
        output_hash="def456",
        tokens_used=1234,
        latency_ms=500,
    )
    assert row_id > 0
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT agent_name, input_hash, output_hash, tokens_used, latency_ms "
            "FROM agent_invocations WHERE id=?",
            (row_id,),
        ).fetchone()
    assert row["agent_name"] == "planner"
    assert row["input_hash"] == "abc123"
    assert row["output_hash"] == "def456"
    assert row["tokens_used"] == 1234
    assert row["latency_ms"] == 500


def test_record_checkpoint(db_path: str) -> None:
    row_id = persistence.record_checkpoint(
        db_path,
        handover_id="ALFRED_HANDOVER_3",
        checkpoint_id="CHECKPOINT-1",
        verdict="proceed",
        evidence_hash="evid-xyz",
    )
    assert row_id > 0
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT handover_id, checkpoint_id, verdict, evidence_hash "
            "FROM checkpoint_history WHERE id=?",
            (row_id,),
        ).fetchone()
    assert row["handover_id"] == "ALFRED_HANDOVER_3"
    assert row["checkpoint_id"] == "CHECKPOINT-1"
    assert row["verdict"] == "proceed"
    assert row["evidence_hash"] == "evid-xyz"


def test_create_and_retrieve_pending_approval(db_path: str) -> None:
    persistence.create_pending_approval(
        db_path,
        approval_id="approval-1",
        handover_id="ALFRED_HANDOVER_4",
        action_type="story_creation",
        item_id="PVTI_123",
        timeout_seconds=3600,
    )

    approvals = persistence.get_pending_approvals(db_path)
    assert len(approvals) == 1
    assert approvals[0]["id"] == "approval-1"
    assert approvals[0]["handover_id"] == "ALFRED_HANDOVER_4"
    assert approvals[0]["action_type"] == "story_creation"
    assert approvals[0]["item_id"] == "PVTI_123"
    assert approvals[0]["decision"] is None
    assert approvals[0]["decided_at"] is None


def test_expired_approvals_returned_correctly(db_path: str) -> None:
    persistence.create_pending_approval(
        db_path,
        approval_id="approval-expired",
        handover_id="ALFRED_HANDOVER_4",
        action_type="story_creation",
        item_id="PVTI_expired",
        timeout_seconds=0,
    )

    expired = persistence.get_expired_approvals(db_path)
    assert len(expired) == 1
    assert expired[0]["id"] == "approval-expired"


def test_record_approval_decision_updates_row(db_path: str) -> None:
    persistence.create_pending_approval(
        db_path,
        approval_id="approval-2",
        handover_id="ALFRED_HANDOVER_4",
        action_type="story_creation",
        item_id="PVTI_456",
        timeout_seconds=3600,
    )
    persistence.record_approval_decision(db_path, "approval-2", "approved")

    row = persistence.get_approval(db_path, "approval-2")
    assert row is not None
    assert row["decision"] == "approved"
    assert row["decided_at"] is not None


def test_parent_directory_is_created(tmp_path: Path) -> None:
    db = tmp_path / "nested" / "sub" / "alfred.db"
    persistence.record_velocity(str(db), _record(1))
    assert db.exists()
