"""Resume the approved Phase 4 GitHub write step for the kickoff demo.

This is a small operator helper for cases where approval has already been
recorded and the board-writer step needs to be retried after fixing a GitHub
configuration issue.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_kickoff_demo as rk  # noqa: E402

from alfred.orchestrator import orchestrate  # noqa: E402
from alfred.tools.persistence import list_write_receipts  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resume the approved Phase 4 GitHub write for the kickoff demo."
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

    workspace = args.workspace
    db_path = str(rk.workspace_db_path(workspace))

    cfg = rk.default_demo_config(workspace)
    cfg.github.org = os.environ["ALFRED_DEMO_GITHUB_ORG"]
    cfg.github.project_number = int(os.environ["ALFRED_DEMO_GITHUB_PROJECT_NUMBER"])
    cfg.github.token_env_var = "GITHUB_TOKEN"

    handover = rk._board_writer_handover(rk.KICKOFF_HANDOVER_ID, rk.KICKOFF_TASK_ID)
    orchestrate(handover, cfg, db_path=db_path)

    result = handover.tasks[0].result
    if result is None:
        print("No board-writer result was produced.", file=sys.stderr)
        return 1

    print(result.output_summary)
    print(
        json.dumps(
            list_write_receipts(
                db_path,
                handover_id=rk.KICKOFF_HANDOVER_ID,
                task_id=rk.KICKOFF_TASK_ID,
            ),
            indent=2,
        )
    )
    return 0 if result.completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
