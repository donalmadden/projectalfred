"""Tests for ``scripts/init_demo_workspace.py``."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import init_demo_workspace as iw  # noqa: E402


def test_extract_readme_text_returns_unwrapped_paragraph() -> None:
    text = iw.extract_readme_text()
    assert text.startswith("Customer Onboarding Portal is a greenfield product workspace")
    assert text.endswith("\n")
    assert "`" not in text
    assert "## " not in text


def test_init_creates_frozen_layout(tmp_path: Path) -> None:
    workspace = tmp_path / "cop_demo"
    message = iw.init_workspace(workspace)

    assert message.startswith("Workspace initialised")
    assert (workspace / "README.md").is_file()
    assert (workspace / "docs" / "CHARTER.md").is_file()
    handovers = workspace / "docs" / "handovers"
    assert handovers.is_dir()
    assert list(handovers.iterdir()) == []


def test_charter_is_byte_identical(tmp_path: Path) -> None:
    workspace = tmp_path / "cop_demo"
    iw.init_workspace(workspace)
    assert (workspace / "docs" / "CHARTER.md").read_bytes() == iw.CHARTER_SRC.read_bytes()


def test_readme_matches_layout_spec(tmp_path: Path) -> None:
    workspace = tmp_path / "cop_demo"
    iw.init_workspace(workspace)
    assert (workspace / "README.md").read_text(encoding="utf-8") == iw.extract_readme_text()


def test_idempotent_rerun_reports_no_changes(tmp_path: Path) -> None:
    workspace = tmp_path / "cop_demo"
    iw.init_workspace(workspace)
    second = iw.init_workspace(workspace)
    assert second == "Workspace already initialised — no changes made."


def test_refuses_non_empty_dir_without_force(tmp_path: Path) -> None:
    workspace = tmp_path / "cop_demo"
    workspace.mkdir()
    (workspace / "stray.txt").write_text("not part of spec", encoding="utf-8")
    with pytest.raises(FileExistsError):
        iw.init_workspace(workspace)


def test_force_overwrites_non_empty_dir(tmp_path: Path) -> None:
    workspace = tmp_path / "cop_demo"
    workspace.mkdir()
    (workspace / "stray.txt").write_text("not part of spec", encoding="utf-8")
    iw.init_workspace(workspace, force=True)
    assert (workspace / "README.md").is_file()
    assert (workspace / "docs" / "CHARTER.md").is_file()
    assert (workspace / "docs" / "handovers").is_dir()


def test_no_gitkeep_in_handovers(tmp_path: Path) -> None:
    workspace = tmp_path / "cop_demo"
    iw.init_workspace(workspace)
    handovers = workspace / "docs" / "handovers"
    assert not (handovers / ".gitkeep").exists()


def test_main_cli_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workspace = tmp_path / "cop_demo"
    rc = iw.main(["--workspace", str(workspace)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Workspace initialised" in out


def test_main_cli_idempotent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workspace = tmp_path / "cop_demo"
    iw.main(["--workspace", str(workspace)])
    capsys.readouterr()
    rc = iw.main(["--workspace", str(workspace)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "already initialised" in out


def test_main_cli_errors_on_nonempty_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = tmp_path / "cop_demo"
    workspace.mkdir()
    (workspace / "stray.txt").write_text("x", encoding="utf-8")
    rc = iw.main(["--workspace", str(workspace)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "exists and is not empty" in err
