"""Backfill GitHub draft-issue bodies for an already-written kickoff demo board."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_kickoff_demo as rk  # noqa: E402

from alfred.tools.github_api import update_story_body  # noqa: E402
from alfred.tools.persistence import list_story_proposals, list_write_receipts  # noqa: E402
from alfred.tools.story_markdown import render_story_proposal_body  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill draft-issue bodies for the kickoff demo board."
    )
    parser.add_argument(
        "--workspace",
        required=True,
        type=Path,
        help="Path to the demo workspace root.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN is required to backfill draft issue bodies.", file=sys.stderr)
        return 1

    db_path = str(rk.workspace_db_path(args.workspace))
    proposals = {
        record.proposed_story_id: record
        for record in list_story_proposals(
            db_path,
            handover_id=rk.KICKOFF_HANDOVER_ID,
            task_id=rk.KICKOFF_TASK_ID,
        )
    }
    receipts = list_write_receipts(
        db_path,
        handover_id=rk.KICKOFF_HANDOVER_ID,
        task_id=rk.KICKOFF_TASK_ID,
    )
    if not receipts:
        print("No GitHub write receipts found for the kickoff demo.", file=sys.stderr)
        return 1

    updated = 0
    for receipt in receipts:
        proposed_story_id = str(receipt["proposed_story_id"])
        record = proposals.get(proposed_story_id)
        if record is None:
            print(
                f"Missing persisted proposal for receipt {proposed_story_id}.",
                file=sys.stderr,
            )
            return 1
        update_story_body(
            str(receipt["github_item_id"]),
            render_story_proposal_body(record),
            token,
        )
        updated += 1

    print(f"Backfilled {updated} GitHub draft issue bod{'y' if updated == 1 else 'ies'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
