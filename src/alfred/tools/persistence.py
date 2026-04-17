"""
SQLite operational bookkeeping.

Stores sprint metadata, velocity history, agent invocation traces, and
checkpoint evaluation history. NOT the source of truth — the handover
document on the filesystem is. This table is for operational observability
and retrospective analysis only.

Connections are ephemeral per call. The schema bootstraps on first use and
is idempotent; every public function is safe to call against a fresh
db_path.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from alfred.schemas.agent import VelocityRecord
from alfred.schemas.checkpoint import Verdict

_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS velocity (
        sprint_number INTEGER PRIMARY KEY,
        points_committed INTEGER NOT NULL,
        points_completed INTEGER NOT NULL,
        completion_rate REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_invocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        input_hash TEXT NOT NULL,
        output_hash TEXT,
        tokens_used INTEGER,
        latency_ms INTEGER,
        error TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS checkpoint_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        handover_id TEXT NOT NULL,
        checkpoint_id TEXT NOT NULL,
        verdict TEXT NOT NULL,
        evidence_hash TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pending_approvals (
        id TEXT PRIMARY KEY,
        handover_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        item_id TEXT NOT NULL,
        requested_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        decided_at TEXT,
        decision TEXT
    )
    """,
]


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    with closing(conn.cursor()) as cur:
        for stmt in _SCHEMA:
            cur.execute(stmt)
    conn.commit()
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _approval_row_to_dict(row: sqlite3.Row) -> dict[str, Optional[str]]:
    return {
        "id": row["id"],
        "handover_id": row["handover_id"],
        "action_type": row["action_type"],
        "item_id": row["item_id"],
        "requested_at": row["requested_at"],
        "expires_at": row["expires_at"],
        "decided_at": row["decided_at"],
        "decision": row["decision"],
    }


def record_velocity(db_path: str, record: VelocityRecord) -> None:
    """Insert or update a velocity record. Idempotent per sprint_number."""
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            INSERT INTO velocity (sprint_number, points_committed, points_completed, completion_rate)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(sprint_number) DO UPDATE SET
                points_committed = excluded.points_committed,
                points_completed = excluded.points_completed,
                completion_rate = excluded.completion_rate
            """,
            (
                record.sprint_number,
                record.points_committed,
                record.points_completed,
                record.completion_rate,
            ),
        )
        conn.commit()


def get_velocity_history(db_path: str, sprint_count: int) -> list[VelocityRecord]:
    """Return the most recent `sprint_count` velocity records, newest first."""
    if sprint_count <= 0:
        return []
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        rows = cur.execute(
            """
            SELECT sprint_number, points_committed, points_completed, completion_rate
            FROM velocity
            ORDER BY sprint_number DESC
            LIMIT ?
            """,
            (sprint_count,),
        ).fetchall()
    return [
        VelocityRecord(
            sprint_number=r["sprint_number"],
            points_committed=r["points_committed"],
            points_completed=r["points_completed"],
            completion_rate=r["completion_rate"],
        )
        for r in rows
    ]


def record_agent_invocation(
    db_path: str,
    agent_name: str,
    input_hash: str,
    output_hash: Optional[str] = None,
    tokens_used: Optional[int] = None,
    latency_ms: Optional[int] = None,
    error: Optional[str] = None,
) -> int:
    """Append an agent invocation trace. Returns the row id."""
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            INSERT INTO agent_invocations
                (timestamp, agent_name, input_hash, output_hash, tokens_used, latency_ms, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (_now_iso(), agent_name, input_hash, output_hash, tokens_used, latency_ms, error),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def record_checkpoint(
    db_path: str,
    handover_id: str,
    checkpoint_id: str,
    verdict: Verdict,
    evidence_hash: Optional[str] = None,
) -> int:
    """Append a checkpoint evaluation outcome. Returns the row id."""
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            INSERT INTO checkpoint_history
                (timestamp, handover_id, checkpoint_id, verdict, evidence_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (_now_iso(), handover_id, checkpoint_id, str(verdict), evidence_hash),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def create_pending_approval(
    db_path: str,
    approval_id: str,
    handover_id: str,
    action_type: str,
    item_id: str,
    timeout_seconds: int,
) -> None:
    """Create a pending approval record with an expiry deadline."""
    requested_at = datetime.now(timezone.utc)
    expires_at = requested_at + timedelta(seconds=timeout_seconds)
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            INSERT INTO pending_approvals
                (id, handover_id, action_type, item_id, requested_at, expires_at, decided_at, decision)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (
                approval_id,
                handover_id,
                action_type,
                item_id,
                requested_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        conn.commit()


def get_approval(db_path: str, approval_id: str) -> Optional[dict[str, Optional[str]]]:
    """Return a single approval record by id, or None if not found."""
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        row = cur.execute(
            """
            SELECT id, handover_id, action_type, item_id, requested_at, expires_at, decided_at, decision
            FROM pending_approvals
            WHERE id = ?
            """,
            (approval_id,),
        ).fetchone()
    return _approval_row_to_dict(row) if row is not None else None


def get_pending_approvals(db_path: str) -> list[dict[str, Optional[str]]]:
    """Return all open approvals ordered by request time."""
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        rows = cur.execute(
            """
            SELECT id, handover_id, action_type, item_id, requested_at, expires_at, decided_at, decision
            FROM pending_approvals
            WHERE decision IS NULL
            ORDER BY requested_at ASC
            """
        ).fetchall()
    return [_approval_row_to_dict(row) for row in rows]


def count_pending_approvals(db_path: str) -> int:
    """Return the number of currently open approvals."""
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        row = cur.execute(
            "SELECT COUNT(*) AS count FROM pending_approvals WHERE decision IS NULL"
        ).fetchone()
    return int(row["count"]) if row is not None else 0


def get_expired_approvals(db_path: str) -> list[dict[str, Optional[str]]]:
    """Return pending approvals that have passed their expiry time."""
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        rows = cur.execute(
            """
            SELECT id, handover_id, action_type, item_id, requested_at, expires_at, decided_at, decision
            FROM pending_approvals
            WHERE decision IS NULL AND expires_at <= ?
            ORDER BY expires_at ASC
            """,
            (_now_iso(),),
        ).fetchall()
    return [_approval_row_to_dict(row) for row in rows]


def record_approval_decision(db_path: str, approval_id: str, decision: str) -> None:
    """Record a final decision on a pending approval."""
    if decision not in {"approved", "rejected", "expired"}:
        raise ValueError(f"Invalid approval decision: {decision!r}")

    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            UPDATE pending_approvals
            SET decided_at = ?, decision = ?
            WHERE id = ? AND decision IS NULL
            """,
            (_now_iso(), decision, approval_id),
        )

        if cur.rowcount == 0:
            row = cur.execute(
                "SELECT decision FROM pending_approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Approval not found: {approval_id}")
            raise ValueError(
                f"Approval '{approval_id}' already decided as {row['decision']}"
            )

        conn.commit()
