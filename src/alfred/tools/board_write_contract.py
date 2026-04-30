"""Phase 4 — approval-gated GitHub Project V2 write contract.

This module is the narrow, testable contract that ties an approval record
to a persisted batch of story proposals and gates the board-write step.
No GitHub calls live here; no new tables are introduced. The existing
``pending_approvals`` and ``story_proposals`` tables are sufficient when
the linkage keys below are used consistently.

Linkage keys (Phase 4 Task 1):

  - ``handover_id``
  - ``task_id`` (must equal ``TASK-SEED-BOARD-001`` for the kickoff slice)
  - ``action_type`` (constant ``BOARD_WRITE_ACTION``)
  - ``pending_approvals.item_id`` is set to ``task_id`` so an approval row
    is uniquely identified by ``(handover_id, action_type, item_id)``.

Lifecycle invariants enforced here:

  - ``pending -> approved`` requires a ``pending_approvals`` row with
    matching linkage keys and ``decision='approved'``. The approval id
    is stamped into ``story_proposals.approval_decision_id``.
  - ``approved -> written`` requires the row's current
    ``approval_status == 'approved'`` (no pending->written skip).
  - Story content fields (title, description, acceptance_criteria,
    story_points) are never written by transition helpers.
  - Idempotency: rows already at ``written`` are skipped by
    ``select_writeable_proposals`` so re-running the write step after a
    partial failure cannot create duplicates.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Optional

from alfred.schemas.story_proposal import StoryProposalRecord
from alfred.tools.persistence import (
    _connect,
    list_story_proposals,
    update_story_proposal_status,
)

BOARD_WRITE_ACTION = "WRITE_GITHUB_PROJECT_V2"


class ApprovalRequiredError(RuntimeError):
    """Raised when a board write is attempted without a matching approval."""


class InvalidLifecycleTransitionError(RuntimeError):
    """Raised when a proposal lifecycle transition violates the contract."""


def find_matching_approval_id(
    db_path: str,
    *,
    handover_id: str,
    task_id: str,
) -> Optional[str]:
    """Return the approval id whose decision is ``approved`` for this batch.

    Matches on ``(handover_id, action_type=BOARD_WRITE_ACTION, item_id=task_id)``.
    Returns ``None`` when no such row exists, or when the row exists but has
    not been decided / was rejected / expired. If multiple rows match, the
    most recently decided one wins.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        row = cur.execute(
            """
            SELECT id
            FROM pending_approvals
            WHERE handover_id = ?
              AND action_type = ?
              AND item_id = ?
              AND decision = 'approved'
            ORDER BY decided_at DESC
            LIMIT 1
            """,
            (handover_id, BOARD_WRITE_ACTION, task_id),
        ).fetchone()
    return row["id"] if row is not None else None


def select_writeable_proposals(
    db_path: str,
    *,
    handover_id: str,
    task_id: str,
) -> list[StoryProposalRecord]:
    """Return proposals in this batch that still need to be written.

    Filters out rows already at ``written``. Order matches
    ``list_story_proposals`` (deterministic by created_at then id) so the
    write step is reproducible across pause/resume.
    """
    rows = list_story_proposals(db_path, handover_id=handover_id, task_id=task_id)
    return [r for r in rows if r.approval_status != "written"]


def gate_board_write(
    db_path: str,
    *,
    handover_id: str,
    task_id: str,
) -> tuple[str, list[StoryProposalRecord]]:
    """Refuse-or-allow the board write step. Returns (approval_id, batch).

    Raises ``ApprovalRequiredError`` if no matching approved approval row
    exists. The returned batch excludes already-written rows so the caller
    can iterate and write idempotently.
    """
    approval_id = find_matching_approval_id(
        db_path, handover_id=handover_id, task_id=task_id
    )
    if approval_id is None:
        raise ApprovalRequiredError(
            f"No approved approval for handover_id={handover_id!r} "
            f"task_id={task_id!r} action={BOARD_WRITE_ACTION!r}"
        )
    batch = select_writeable_proposals(
        db_path, handover_id=handover_id, task_id=task_id
    )
    return approval_id, batch


def _get_proposal_status(db_path: str, proposed_story_id: str) -> str:
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        row = cur.execute(
            "SELECT approval_status FROM story_proposals WHERE proposed_story_id = ?",
            (proposed_story_id,),
        ).fetchone()
    if row is None:
        raise InvalidLifecycleTransitionError(
            f"Story proposal not found: {proposed_story_id}"
        )
    return str(row["approval_status"])


def mark_proposal_approved(
    db_path: str,
    *,
    proposed_story_id: str,
    approval_id: str,
) -> None:
    """Transition pending -> approved, stamping the approval id.

    Raises ``InvalidLifecycleTransitionError`` if the current status is
    not ``pending``.
    """
    current = _get_proposal_status(db_path, proposed_story_id)
    if current != "pending":
        raise InvalidLifecycleTransitionError(
            f"Cannot approve proposal {proposed_story_id!r} from status {current!r}"
        )
    update_story_proposal_status(
        db_path,
        proposed_story_id,
        "approved",
        approval_decision_id=approval_id,
    )


def mark_proposal_written(db_path: str, *, proposed_story_id: str) -> None:
    """Transition approved -> written.

    Raises ``InvalidLifecycleTransitionError`` if the current status is
    not ``approved`` (in particular, pending->written is forbidden, and
    written->written is rejected so callers must filter via
    ``select_writeable_proposals`` first).
    """
    current = _get_proposal_status(db_path, proposed_story_id)
    if current != "approved":
        raise InvalidLifecycleTransitionError(
            f"Cannot mark proposal {proposed_story_id!r} written from status {current!r}"
        )
    update_story_proposal_status(db_path, proposed_story_id, "written")
