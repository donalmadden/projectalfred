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

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from alfred.schemas.agent import VelocityRecord
from alfred.schemas.checkpoint import Verdict
from alfred.schemas.story_proposal import ApprovalStatus, StoryProposalRecord

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
    """
    CREATE TABLE IF NOT EXISTS story_proposals (
        proposed_story_id TEXT PRIMARY KEY,
        handover_id TEXT NOT NULL,
        task_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        acceptance_criteria_json TEXT NOT NULL,
        story_points INTEGER NOT NULL,
        approval_status TEXT NOT NULL DEFAULT 'pending',
        approval_decision_id TEXT,
        created_at TEXT NOT NULL,
        approved_at TEXT,
        written_at TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_story_proposals_handover_task
        ON story_proposals (handover_id, task_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS proposal_write_receipts (
        proposed_story_id TEXT PRIMARY KEY,
        github_item_id TEXT NOT NULL,
        github_title TEXT NOT NULL,
        approval_decision_id TEXT NOT NULL,
        written_at TEXT NOT NULL,
        FOREIGN KEY (proposed_story_id) REFERENCES story_proposals (proposed_story_id)
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


# ---------------------------------------------------------------------------
# Story proposals (Phase 3 — proposed-story persistence)
# ---------------------------------------------------------------------------
#
# Idempotency policy (open decision surfaced at CHECKPOINT-2):
#
#   The functions below are pure-insert / pure-update. ``proposed_story_id``
#   is the PK; inserting a record whose id already exists raises a
#   ``sqlite3.IntegrityError``. Repeated harness runs that re-invoke the
#   story generator therefore *append* a new batch of rows by default
#   (Option A), preserving regeneration history.
#
#   If an Option B "replace by (handover_id, task_id) batch" semantic is
#   needed later, the orchestrator (Phase 3 Task 3) can call
#   ``delete_story_proposals(db_path, handover_id, task_id)`` before
#   inserting. That helper is intentionally NOT provided here yet; surface
#   the policy choice in Task 3 once the orchestrator wiring makes the
#   right call obvious.


def _record_to_row(record: StoryProposalRecord) -> tuple:
    return (
        record.proposed_story_id,
        record.handover_id,
        record.task_id,
        record.title,
        record.description,
        json.dumps(record.acceptance_criteria),
        int(record.story_points),
        record.approval_status,
        record.approval_decision_id,
        record.created_at.isoformat(),
        record.approved_at.isoformat() if record.approved_at is not None else None,
        record.written_at.isoformat() if record.written_at is not None else None,
    )


def _row_to_record(row: sqlite3.Row) -> StoryProposalRecord:
    return StoryProposalRecord(
        proposed_story_id=row["proposed_story_id"],
        handover_id=row["handover_id"],
        task_id=row["task_id"],
        title=row["title"],
        description=row["description"],
        acceptance_criteria=json.loads(row["acceptance_criteria_json"]),
        story_points=int(row["story_points"]),  # type: ignore[arg-type]
        approval_status=row["approval_status"],
        approval_decision_id=row["approval_decision_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        approved_at=(
            datetime.fromisoformat(row["approved_at"])
            if row["approved_at"] is not None
            else None
        ),
        written_at=(
            datetime.fromisoformat(row["written_at"])
            if row["written_at"] is not None
            else None
        ),
    )


def insert_story_proposals(
    db_path: str,
    records: list[StoryProposalRecord],
) -> None:
    """Persist a batch of story proposal records.

    Pure insert — duplicate ``proposed_story_id`` raises. Callers that
    need replace-by-batch semantics should delete the matching rows
    first (no helper provided yet; see module-level idempotency note).
    """
    if not records:
        return
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.executemany(
            """
            INSERT INTO story_proposals
                (proposed_story_id, handover_id, task_id, title, description,
                 acceptance_criteria_json, story_points, approval_status,
                 approval_decision_id, created_at, approved_at, written_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [_record_to_row(r) for r in records],
        )
        conn.commit()


def list_story_proposals(
    db_path: str,
    *,
    handover_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> list[StoryProposalRecord]:
    """Return persisted story proposals, optionally filtered by linkage.

    With no filter, returns every row (oldest first by ``created_at``).
    Supplying ``handover_id`` / ``task_id`` narrows the query via the
    composite index. Order is stable and deterministic so gate review
    output is reproducible across pause/resume.
    """
    clauses: list[str] = []
    params: list[str] = []
    if handover_id is not None:
        clauses.append("handover_id = ?")
        params.append(handover_id)
    if task_id is not None:
        clauses.append("task_id = ?")
        params.append(task_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT proposed_story_id, handover_id, task_id, title, description,
               acceptance_criteria_json, story_points, approval_status,
               approval_decision_id, created_at, approved_at, written_at
        FROM story_proposals
        {where}
        ORDER BY created_at ASC, proposed_story_id ASC
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        rows = cur.execute(sql, params).fetchall()
    return [_row_to_record(r) for r in rows]


def update_story_proposal_status(
    db_path: str,
    proposed_story_id: str,
    status: ApprovalStatus,
    *,
    approval_decision_id: Optional[str] = None,
) -> None:
    """Transition a single proposal's approval status.

    Sets ``approved_at`` when status becomes ``approved`` and
    ``written_at`` when it becomes ``written`` (both via UTC now).
    Raises ``ValueError`` if no row matches ``proposed_story_id``.
    """
    if status not in ("pending", "approved", "written"):
        raise ValueError(f"Invalid story proposal status: {status!r}")

    now = _now_iso()
    set_clauses = ["approval_status = ?"]
    params: list[Optional[str]] = [status]
    if approval_decision_id is not None:
        set_clauses.append("approval_decision_id = ?")
        params.append(approval_decision_id)
    if status == "approved":
        set_clauses.append("approved_at = ?")
        params.append(now)
    elif status == "written":
        set_clauses.append("written_at = ?")
        params.append(now)
    params.append(proposed_story_id)

    sql = f"UPDATE story_proposals SET {', '.join(set_clauses)} WHERE proposed_story_id = ?"
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(sql, params)
        if cur.rowcount == 0:
            raise ValueError(f"Story proposal not found: {proposed_story_id}")
        conn.commit()


# ---------------------------------------------------------------------------
# Write receipts (Phase 4 — board-write traceability)
# ---------------------------------------------------------------------------
#
# A write receipt ties a persisted proposal row to the GitHub Project V2
# draft item it produced. One receipt per ``proposed_story_id`` (PK), so
# re-running the write step after a partial failure cannot create
# duplicates: ``record_proposal_write`` is the atomic
# (insert-receipt + mark-written) primitive used by Phase 4 Task 3.


def _receipt_row_to_dict(row: sqlite3.Row) -> dict[str, str]:
    return {
        "proposed_story_id": row["proposed_story_id"],
        "github_item_id": row["github_item_id"],
        "github_title": row["github_title"],
        "approval_decision_id": row["approval_decision_id"],
        "written_at": row["written_at"],
    }


def get_write_receipt(
    db_path: str, proposed_story_id: str
) -> Optional[dict[str, str]]:
    """Return the write receipt for a proposal, or ``None`` if absent."""
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        row = cur.execute(
            """
            SELECT proposed_story_id, github_item_id, github_title,
                   approval_decision_id, written_at
            FROM proposal_write_receipts
            WHERE proposed_story_id = ?
            """,
            (proposed_story_id,),
        ).fetchone()
    return _receipt_row_to_dict(row) if row is not None else None


def list_write_receipts(
    db_path: str,
    *,
    handover_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> list[dict[str, str]]:
    """Return write receipts, optionally filtered by proposal linkage.

    Joins ``proposal_write_receipts`` to ``story_proposals`` so the
    handover/task filters mirror ``list_story_proposals``. Order is
    deterministic by ``written_at`` (oldest first) for reproducible
    evidence output.
    """
    clauses: list[str] = []
    params: list[str] = []
    if handover_id is not None:
        clauses.append("sp.handover_id = ?")
        params.append(handover_id)
    if task_id is not None:
        clauses.append("sp.task_id = ?")
        params.append(task_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT r.proposed_story_id, r.github_item_id, r.github_title,
               r.approval_decision_id, r.written_at
        FROM proposal_write_receipts r
        JOIN story_proposals sp ON sp.proposed_story_id = r.proposed_story_id
        {where}
        ORDER BY r.written_at ASC, r.proposed_story_id ASC
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        rows = cur.execute(sql, params).fetchall()
    return [_receipt_row_to_dict(r) for r in rows]


def record_proposal_write(
    db_path: str,
    *,
    proposed_story_id: str,
    github_item_id: str,
    github_title: str,
    approval_decision_id: str,
) -> None:
    """Atomically record a write receipt and transition status to ``written``.

    Performs both writes in a single SQLite transaction so a partial
    failure cannot leave a receipt without a status update (or vice
    versa). Preconditions:

      - the proposal row exists,
      - its current ``approval_status`` is ``'approved'``,
      - no receipt already exists for this ``proposed_story_id``.

    Violations raise ``ValueError`` and the transaction is rolled back.
    """
    now = _now_iso()
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        try:
            row = cur.execute(
                "SELECT approval_status FROM story_proposals WHERE proposed_story_id = ?",
                (proposed_story_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Story proposal not found: {proposed_story_id}")
            if row["approval_status"] != "approved":
                raise ValueError(
                    f"Cannot write proposal {proposed_story_id!r} from status "
                    f"{row['approval_status']!r}"
                )
            existing = cur.execute(
                "SELECT 1 FROM proposal_write_receipts WHERE proposed_story_id = ?",
                (proposed_story_id,),
            ).fetchone()
            if existing is not None:
                raise ValueError(
                    f"Write receipt already exists for {proposed_story_id!r}"
                )

            cur.execute(
                """
                INSERT INTO proposal_write_receipts
                    (proposed_story_id, github_item_id, github_title,
                     approval_decision_id, written_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    proposed_story_id,
                    github_item_id,
                    github_title,
                    approval_decision_id,
                    now,
                ),
            )
            cur.execute(
                """
                UPDATE story_proposals
                SET approval_status = 'written', written_at = ?
                WHERE proposed_story_id = ?
                """,
                (now, proposed_story_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
