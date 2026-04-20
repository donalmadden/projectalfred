"""Tests for the FastAPI endpoints."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from alfred.api import app, set_config
from alfred.schemas.agent import (
    BoardState,
    PlannerOutput,
    QualityJudgeOutput,
    CheckpointEvaluation,
    RetroAnalystOutput,
    VelocityRecord,
)
from alfred.schemas.config import AlfredConfig
from alfred.tools import llm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_providers():
    original = dict(llm._PROVIDERS)
    yield
    llm._PROVIDERS.clear()
    llm._PROVIDERS.update(original)


@pytest.fixture(autouse=True)
def _inject_config():
    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = ""
    cfg.github.org = ""
    cfg.rag.index_path = ""
    set_config(cfg)
    yield
    set_config(None)  # type: ignore[arg-type]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_client(tmp_path: Path) -> TestClient:
    """Client with a real database configured — required for approval endpoints."""
    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = str(tmp_path / "alfred.db")
    cfg.github.org = ""
    cfg.rag.index_path = ""
    cfg.hitl.timeout_seconds = 3600
    set_config(cfg)
    return TestClient(app)


def _install_llm_fake(response: dict[str, Any]) -> None:
    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        return response, 10
    llm._PROVIDERS["fake"] = fake


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------

_PLANNER_RESPONSE = {
    "draft_handover_markdown": "# Draft\n\n## Checkpoint\n\nPlan.",
    "sprint_plan": None,
    "task_decomposition": ["Task A", "Task B"],
    "open_questions": ["Should we defer X?"],
}


def test_generate_returns_200(client: TestClient) -> None:
    _install_llm_fake(_PLANNER_RESPONSE)
    resp = client.post("/generate", json={"sprint_goal": "Ship auth refactor"})
    assert resp.status_code == 200


def test_generate_response_shape(client: TestClient) -> None:
    _install_llm_fake(_PLANNER_RESPONSE)
    resp = client.post("/generate", json={})
    body = resp.json()
    assert "draft_handover_markdown" in body
    assert "task_decomposition" in body
    assert "open_questions" in body


def test_generate_returns_draft_content(client: TestClient) -> None:
    _install_llm_fake(_PLANNER_RESPONSE)
    resp = client.post("/generate", json={"sprint_goal": "Auth"})
    assert "Draft" in resp.json()["draft_handover_markdown"]
    assert resp.json()["task_decomposition"] == ["Task A", "Task B"]


def test_generate_injects_canonical_scaffold_into_planner_prompt(tmp_path: Path) -> None:
    """The /generate path must read handover.template_path and pass the
    scaffold content into the planner prompt, not silently ignore it.
    """
    scaffold = (
        "## CONTEXT — READ THIS FIRST\n\n"
        "## WHAT EXISTS TODAY\n\n"
        "### Git History\n\n"
        "## HARD RULES\n\n"
        "## TASK OVERVIEW\n\n"
        "## WHAT NOT TO DO\n\n"
        "## POST-MORTEM\n"
        "ALFRED_SCAFFOLD_MARKER_XYZ\n"
    )
    scaffold_path = tmp_path / "alfred_scaffold.md"
    scaffold_path.write_text(scaffold, encoding="utf-8")

    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = ""
    cfg.github.org = ""
    cfg.rag.index_path = ""
    cfg.handover.template_path = str(scaffold_path)
    # Critique loop re-invokes the planner; disable it here so the captured
    # prompt list always contains the initial generation call deterministically.
    cfg.agents.planner.max_critique_iterations = 0
    set_config(cfg)

    captured: list[str] = []

    def fake(prompt: str, output_schema: Any, model: str) -> tuple[dict[str, Any], int]:
        captured.append(prompt)
        return _PLANNER_RESPONSE, 0

    llm._PROVIDERS["fake"] = fake

    client = TestClient(app)
    resp = client.post("/generate", json={"sprint_goal": "Phase 6"})

    assert resp.status_code == 200
    assert captured, "planner was not invoked"
    assert "ALFRED_SCAFFOLD_MARKER_XYZ" in captured[0]
    assert "SCAFFOLD BEGIN" in captured[0]


# ---------------------------------------------------------------------------
# POST /evaluate
# ---------------------------------------------------------------------------

_JUDGE_RESPONSE = {
    "checkpoint_evaluations": [
        {
            "checkpoint_id": "CHECKPOINT-1",
            "verdict": "proceed",
            "evidence_summary": "3 passed",
            "reasoning": "All tests pass.",
            "human_review_required": False,
        }
    ],
    "validation_issues": [],
    "overall_quality_score": 1.0,
    "hitl_escalation_required": False,
    "hitl_escalation_reason": None,
    "methodology_compliance": {"1": True, "2": True, "3": True, "4": True, "5": True},
}

_CHECKPOINT_DEF = json.dumps({
    "checkpoint_id": "CHECKPOINT-1",
    "rows": [
        {"observation": "All tests pass", "verdict": "proceed"},
        {"observation": "Tests fail", "verdict": "stop"},
    ],
})


def test_evaluate_returns_200(client: TestClient) -> None:
    _install_llm_fake({"matched_index": 0, "reasoning": "pass"})
    resp = client.post("/evaluate", json={
        "handover_document_markdown": "# Handover\n\n## Checkpoint\n\ngate",
        "checkpoint_definition": _CHECKPOINT_DEF,
        "executor_output": {"task_id": "t1", "console_output": "3 passed"},
    })
    assert resp.status_code == 200


def test_evaluate_response_shape(client: TestClient) -> None:
    _install_llm_fake({"matched_index": 0, "reasoning": "pass"})
    resp = client.post("/evaluate", json={
        "handover_document_markdown": "# H\n\n## Checkpoint\n\ngate",
        "checkpoint_definition": _CHECKPOINT_DEF,
    })
    body = resp.json()
    assert "verdict" in body
    assert "checkpoint_id" in body
    assert "reasoning" in body
    assert "hitl_required" in body


def test_evaluate_proceed_verdict(client: TestClient) -> None:
    _install_llm_fake({"matched_index": 0, "reasoning": "all pass"})
    resp = client.post("/evaluate", json={
        "handover_document_markdown": "# H\n\n## Checkpoint\n\ngate",
        "checkpoint_definition": _CHECKPOINT_DEF,
        "executor_output": {"task_id": "t1", "console_output": "3 passed"},
    })
    assert resp.json()["verdict"] == "proceed"
    assert resp.json()["hitl_required"] is False


def test_evaluate_stop_verdict(client: TestClient) -> None:
    _install_llm_fake({"matched_index": 1, "reasoning": "fail"})
    resp = client.post("/evaluate", json={
        "handover_document_markdown": "# H\n\n## Checkpoint\n\ngate",
        "checkpoint_definition": _CHECKPOINT_DEF,
        "executor_output": {"task_id": "t1", "console_output": "2 failed"},
    })
    assert resp.json()["verdict"] == "stop"
    assert resp.json()["hitl_required"] is True


# ---------------------------------------------------------------------------
# HITL approval endpoints
# ---------------------------------------------------------------------------


def test_request_approval_endpoint_creates_pending_record(
    db_client: TestClient, tmp_path: Path
) -> None:
    resp = db_client.post("/approvals/request", json={
        "handover_id": "ALFRED_HANDOVER_4",
        "action_type": "story_creation",
        "item_id": "PVTI_abc",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "approval_id" in body
    assert "expires_at" in body
    assert body["expires_at"]

    # Verify the record is visible in the pending list
    pending = db_client.get("/approvals/pending").json()
    assert len(pending) == 1
    assert pending[0]["item_id"] == "PVTI_abc"
    assert pending[0]["decision"] is None


def test_approve_endpoint_records_decision(db_client: TestClient) -> None:
    create_resp = db_client.post("/approvals/request", json={
        "handover_id": "ALFRED_HANDOVER_4",
        "action_type": "story_creation",
        "item_id": "PVTI_xyz",
    })
    approval_id = create_resp.json()["approval_id"]

    resp = db_client.post("/approve", json={
        "approval_id": approval_id,
        "decision": "approved",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "approved"
    assert body["decided_at"] is not None

    # Approval is no longer pending
    pending = db_client.get("/approvals/pending").json()
    assert len(pending) == 0


def test_expire_endpoint_marks_expired(db_client: TestClient) -> None:
    from alfred.api import get_config
    cfg = get_config()
    cfg.hitl.timeout_seconds = 0  # expire immediately

    create_resp = db_client.post("/approvals/request", json={
        "handover_id": "ALFRED_HANDOVER_4",
        "action_type": "story_creation",
        "item_id": "PVTI_expired",
    })
    assert create_resp.status_code == 200

    resp = db_client.post("/approvals/expire")
    assert resp.status_code == 200
    assert resp.json()["expired_count"] == 1

    pending = db_client.get("/approvals/pending").json()
    assert len(pending) == 0


def test_approve_not_found_returns_404(db_client: TestClient) -> None:
    resp = db_client.post("/approve", json={
        "approval_id": "does-not-exist",
        "decision": "approved",
    })
    assert resp.status_code == 404


def test_approve_already_decided_returns_409(db_client: TestClient) -> None:
    create_resp = db_client.post("/approvals/request", json={
        "handover_id": "ALFRED_HANDOVER_4",
        "action_type": "story_creation",
        "item_id": "PVTI_dup",
    })
    approval_id = create_resp.json()["approval_id"]

    db_client.post("/approve", json={"approval_id": approval_id, "decision": "approved"})
    resp = db_client.post("/approve", json={"approval_id": approval_id, "decision": "rejected"})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /retrospective
# ---------------------------------------------------------------------------

_RETRO_RESPONSE = {
    "pattern_report": [],
    "velocity_trend": {
        "average_completion_rate": 0.85,
        "trend_direction": "stable",
        "sprints_analysed": 3,
    },
    "retrospective_summary": "Sprint was stable with no major blockers.",
    "handovers_analysed": 5,
    "top_risks": ["Late integration"],
    "top_successes": ["Clean deployments"],
}


def test_retrospective_returns_200(client: TestClient) -> None:
    _install_llm_fake(_RETRO_RESPONSE)
    resp = client.post("/retrospective", json={"analysis_focus": "deployment"})
    assert resp.status_code == 200


def test_retrospective_response_shape(client: TestClient) -> None:
    _install_llm_fake(_RETRO_RESPONSE)
    resp = client.post("/retrospective", json={})
    body = resp.json()
    assert "retrospective_summary" in body
    assert "top_risks" in body
    assert "velocity_trend" in body


def test_retrospective_summary_populated(client: TestClient) -> None:
    _install_llm_fake(_RETRO_RESPONSE)
    resp = client.post("/retrospective", json={})
    assert "stable" in resp.json()["retrospective_summary"]


# ---------------------------------------------------------------------------
# GET /dashboard
# ---------------------------------------------------------------------------


def test_dashboard_returns_200(client: TestClient) -> None:
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_dashboard_response_shape(client: TestClient) -> None:
    resp = client.get("/dashboard")
    body = resp.json()
    assert "board_state" in body
    assert "velocity_history" in body
    assert "recent_checkpoints" in body


def test_dashboard_empty_when_no_data(client: TestClient) -> None:
    resp = client.get("/dashboard")
    body = resp.json()
    assert body["velocity_history"] == []
    assert body["recent_checkpoints"] == []


def test_dashboard_includes_pending_count(db_client: TestClient) -> None:
    body = db_client.get("/dashboard").json()
    assert "pending_approvals_count" in body
    assert body["pending_approvals_count"] == 0
