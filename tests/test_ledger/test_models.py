"""Tests for ``alfred.ledger.models``."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from alfred.ledger.models import Brief, Phase, PhaseLedger, TaskSeed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ratified(**overrides) -> dict:
    return {"id": 1, "title": "Project framing", "status": "ratified", "handover_id": "ALFRED_HANDOVER_1", **overrides}


def _planning(**overrides) -> dict:
    return {"id": 2, "title": "Architecture", "status": "planning", **overrides}


def _brief(**overrides) -> dict:
    return {
        "title": "Slice 2",
        "goal": "Add the phase ledger scaffold.",
        "hard_rules": ["Additive only"],
        "tasks": [{"id": "t1", "title": "Models", "intent": "Typed schema"}],
        "out_of_scope": ["renderer changes"],
        "definition_of_done": ["tests pass"],
        "follow_ups": [],
        **overrides,
    }


def _ledger(*phases: dict) -> dict:
    return {"project": "projectalfred", "phases": list(phases)}


# ---------------------------------------------------------------------------
# Brief
# ---------------------------------------------------------------------------


def test_brief_round_trips() -> None:
    b = Brief.model_validate(_brief())
    assert b.title == "Slice 2"
    assert b.tasks[0].id == "t1"


def test_brief_defaults_empty_lists() -> None:
    b = Brief.model_validate({"title": "x", "goal": "y"})
    assert b.hard_rules == []
    assert b.tasks == []
    assert b.out_of_scope == []
    assert b.definition_of_done == []
    assert b.follow_ups == []


def test_brief_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        Brief.model_validate({"title": "x"})  # missing goal


# ---------------------------------------------------------------------------
# Phase — valid cases
# ---------------------------------------------------------------------------


def test_ratified_phase_validates() -> None:
    p = Phase.model_validate(_ratified())
    assert p.status == "ratified"
    assert p.handover_id == "ALFRED_HANDOVER_1"


def test_planning_phase_with_brief_validates() -> None:
    p = Phase.model_validate(_planning(brief=_brief()))
    assert p.brief is not None
    assert p.brief.goal == "Add the phase ledger scaffold."


def test_planning_phase_without_brief_validates() -> None:
    p = Phase.model_validate(_planning())
    assert p.brief is None


# ---------------------------------------------------------------------------
# Phase — rejection rules
# ---------------------------------------------------------------------------


def test_ratified_without_handover_id_rejects() -> None:
    with pytest.raises(ValidationError, match="handover_id"):
        Phase.model_validate({"id": 1, "title": "x", "status": "ratified"})


def test_brief_on_ratified_phase_rejects() -> None:
    with pytest.raises(ValidationError, match="brief"):
        Phase.model_validate(_ratified(brief=_brief()))


def test_phase_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        Phase.model_validate({"id": 1, "title": "x", "status": "done", "handover_id": "H1"})


def test_phase_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        Phase.model_validate({"id": 1, "status": "planning"})  # missing title


# ---------------------------------------------------------------------------
# PhaseLedger
# ---------------------------------------------------------------------------


def test_ledger_round_trips() -> None:
    ledger = PhaseLedger.model_validate(_ledger(_ratified(), _planning()))
    assert ledger.project == "projectalfred"
    assert len(ledger.phases) == 2


def test_ledger_rejects_duplicate_phase_ids() -> None:
    with pytest.raises(ValidationError, match="Duplicate phase id"):
        PhaseLedger.model_validate(_ledger(_ratified(), _ratified()))


def test_ledger_rejects_missing_project() -> None:
    with pytest.raises(ValidationError):
        PhaseLedger.model_validate({"phases": []})
