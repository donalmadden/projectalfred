"""Tests for the Alfred CLI entrypoint."""
from __future__ import annotations

import json
from importlib import metadata

import pytest

from alfred import cli


@pytest.mark.parametrize("argv", [
    ["--help"],
    ["plan", "--help"],
    ["evaluate", "--help"],
    ["serve", "--help"],
    ["validate", "--help"],
    ["version", "--help"],
])
def test_help_exits_zero(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 0
    assert capsys.readouterr().out


def test_version_prints_distribution_version(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli.metadata, "version", lambda name: "9.9.9")
    exit_code = cli.main(["version"])
    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "9.9.9"


def test_version_returns_error_when_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_missing(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(cli.metadata, "version", raise_missing)
    exit_code = cli.main(["version"])
    assert exit_code == 1
    assert "metadata" in capsys.readouterr().err


def test_plan_dry_run_prints_request_payload(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["plan", "--dry-run", "--sprint-goal", "Ship Task 4"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "plan"
    assert payload["dry_run"] is True
    assert payload["request"]["sprint_goal"] == "Ship Task 4"


def test_evaluate_dry_run_prints_request_payload(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["evaluate", "--dry-run"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "evaluate"
    assert payload["dry_run"] is True
    assert "invoke quality judge" in payload["steps"]
