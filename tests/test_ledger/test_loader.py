"""Tests for ``alfred.ledger.loader``."""
from __future__ import annotations

from pathlib import Path

import pytest

from alfred.ledger.loader import LedgerLoadError, load_ledger
from alfred.ledger.models import PhaseLedger


REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = REPO_ROOT / "docs" / "active" / "PHASE_LEDGER.yaml"


# ---------------------------------------------------------------------------
# Seed-file integration
# ---------------------------------------------------------------------------


def test_seed_ledger_loads_and_round_trips() -> None:
    ledger = load_ledger(SEED_PATH)
    assert isinstance(ledger, PhaseLedger)
    assert ledger.project == "blank_project_kickoff_demo"

    phase_ids = [p.id for p in ledger.phases]
    assert phase_ids == [0, 1, 2, 3, 4, 5]

    for phase in ledger.phases:
        assert phase.status == "ratified"
        assert phase.handover_id is not None
        assert phase.brief is None


def test_seed_ledger_scope_source_paths_exist_on_disk() -> None:
    ledger = load_ledger(SEED_PATH)
    for phase in ledger.phases:
        for source in phase.scope_sources:
            assert (REPO_ROOT / source).exists(), (
                f"phase {phase.id} scope_source missing: {source}"
            )


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_load_ledger_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(LedgerLoadError, match="file not found"):
        load_ledger(tmp_path / "does_not_exist.yaml")


def test_load_ledger_invalid_yaml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("project: x\nphases: [\n", encoding="utf-8")
    with pytest.raises(LedgerLoadError, match="invalid YAML"):
        load_ledger(bad)


def test_load_ledger_non_mapping_root_raises(tmp_path: Path) -> None:
    bad = tmp_path / "list.yaml"
    bad.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(LedgerLoadError, match="must be a mapping"):
        load_ledger(bad)


def test_load_ledger_validation_error_surfaces_with_path(tmp_path: Path) -> None:
    bad = tmp_path / "bad_schema.yaml"
    bad.write_text(
        "project: demo\n"
        "phases:\n"
        "  - id: 1\n"
        "    title: x\n"
        "    status: ratified\n",  # missing handover_id
        encoding="utf-8",
    )
    with pytest.raises(LedgerLoadError) as exc_info:
        load_ledger(bad)
    assert str(bad) in str(exc_info.value)
    assert "handover_id" in str(exc_info.value)


def test_load_ledger_rejects_brief_on_ratified(tmp_path: Path) -> None:
    bad = tmp_path / "brief_on_ratified.yaml"
    bad.write_text(
        "project: demo\n"
        "phases:\n"
        "  - id: 1\n"
        "    title: x\n"
        "    status: ratified\n"
        "    handover_id: H1\n"
        "    brief:\n"
        "      title: t\n"
        "      goal: g\n",
        encoding="utf-8",
    )
    with pytest.raises(LedgerLoadError, match="brief"):
        load_ledger(bad)


def test_load_ledger_accepts_planning_phase_with_brief(tmp_path: Path) -> None:
    good = tmp_path / "planning.yaml"
    good.write_text(
        "project: demo\n"
        "phases:\n"
        "  - id: 1\n"
        "    title: x\n"
        "    status: planning\n"
        "    brief:\n"
        "      title: Slice X\n"
        "      goal: do the thing\n"
        "      hard_rules:\n"
        "        - keep it small\n"
        "      tasks:\n"
        "        - id: t1\n"
        "          title: First task\n"
        "          intent: try it\n",
        encoding="utf-8",
    )
    ledger = load_ledger(good)
    assert ledger.phases[0].brief is not None
    assert ledger.phases[0].brief.tasks[0].id == "t1"
