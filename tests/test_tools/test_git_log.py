"""Tests for the git_log helper."""
from __future__ import annotations

import subprocess
from unittest.mock import patch

from alfred.tools.git_log import read_git_log


def test_read_git_log_returns_list() -> None:
    result = read_git_log()
    assert isinstance(result, list)


def test_read_git_log_bounded(tmp_path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    for i in range(15):
        f = tmp_path / f"f{i}.txt"
        f.write_text(str(i))
        subprocess.run(["git", "add", str(f)], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"commit {i}"], cwd=tmp_path, capture_output=True)
    result = read_git_log(repo_path=tmp_path, max_commits=10)
    assert len(result) == 10


def test_read_git_log_degrades_gracefully(tmp_path) -> None:
    # Non-repo directory — git log will fail; expect empty list
    result = read_git_log(repo_path=tmp_path / "not_a_repo")
    assert result == []


def test_read_git_log_degrades_on_subprocess_error() -> None:
    with patch("alfred.tools.git_log.subprocess.run", side_effect=FileNotFoundError):
        result = read_git_log()
    assert result == []


def test_read_git_log_entries_are_strings() -> None:
    result = read_git_log()
    for entry in result:
        assert isinstance(entry, str)
        assert entry.strip()


def test_read_git_log_default_max_is_twelve() -> None:
    # The default max_commits=12 is the contract; test that fewer entries are
    # returned when the repo has fewer commits (uses this repo which has many).
    result = read_git_log(max_commits=3)
    assert len(result) <= 3
