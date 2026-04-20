"""
Deterministic git-history reader for the planner generation path.

Canonical Alfred handover documents require a ### Git History section grounded
in real repository state. This helper reads a bounded window of recent commits
so the planner never needs to invent history.

Degrades gracefully: returns an empty list when git is unavailable or the
working directory is not a repository. The planner prompt and promotion
validator enforce the presence requirement — this helper's job is only to
supply the data.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def read_git_log(
    repo_path: str | Path = ".",
    max_commits: int = 12,
    fmt: str = "%h  %s",
) -> list[str]:
    """Return up to ``max_commits`` recent commit lines from the git log.

    Each entry is formatted with ``fmt`` (a git pretty-format string).
    Returns an empty list if git is unavailable or the path is not a repo.
    """
    try:
        result = subprocess.run(
            ["git", "log", f"--pretty=format:{fmt}", f"-{max_commits}"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        return lines
    except Exception:
        return []
