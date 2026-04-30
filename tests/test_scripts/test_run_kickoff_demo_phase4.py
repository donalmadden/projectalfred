"""Phase 4 Task 4 — harness arc evidence.

``run_phase4_arc`` reads persisted proposals, demonstrates a refused write,
records an approval, runs the orchestrator's board_writer, and prints
``proposal_id -> github_item_id`` receipts. The output transcript is the
demo evidence a senior reviewer reads.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_kickoff_demo as rk  # noqa: E402

from alfred import orchestrator  # noqa: E402
from alfred.schemas.config import AlfredConfig  # noqa: E402
from alfred.schemas.story_proposal import (  # noqa: E402
    StoryProposal,
    StoryProposalRecord,
)
from alfred.tools import github_api, persistence  # noqa: E402

GH_TOKEN_ENV = "ALFRED_PHASE4_GH"


# ---------------------------------------------------------------------------
# Fakes / fixtures
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self.status_code = 200
        self._body = body
        self.text = ""

    def json(self) -> dict[str, Any]:
        return self._body


class _FakeGitHubClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._n = 0

    def post(self, url: str, json: dict[str, Any]) -> _FakeResponse:
        self.calls.append(json)
        query = json.get("query", "")
        if "projectV2(number" in query and "items" not in query:
            return _FakeResponse(
                {"data": {"organization": {"projectV2": {"id": "PROJ_X"}}}}
            )
        if "addProjectV2DraftIssue" in query:
            self._n += 1
            return _FakeResponse(
                {
                    "data": {
                        "addProjectV2DraftIssue": {
                            "projectItem": {"id": f"PVTI_{self._n:03d}"}
                        }
                    }
                }
            )
        raise AssertionError(f"Unexpected GraphQL: {query!r}")


@pytest.fixture(autouse=True)
def _reset_runners_and_client():
    original_runners = dict(orchestrator._AGENT_RUNNERS)
    original_factory = github_api._client_factory
    yield
    orchestrator._AGENT_RUNNERS.clear()
    orchestrator._AGENT_RUNNERS.update(original_runners)
    github_api.set_client_factory(original_factory)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "cop_demo"
    (ws / ".alfred").mkdir(parents=True)
    return ws


@pytest.fixture
def db_path(workspace: Path) -> str:
    return str(rk.workspace_db_path(workspace))


@pytest.fixture
def fake_client() -> _FakeGitHubClient:
    client = _FakeGitHubClient()
    github_api.set_client_factory(lambda token: client)
    return client


@pytest.fixture
def gh_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GH_TOKEN_ENV, "fake-token")


def _config(workspace: Path) -> AlfredConfig:
    cfg = rk.default_demo_config(workspace)
    cfg.github.org = "myorg"
    cfg.github.project_number = 99
    cfg.github.token_env_var = GH_TOKEN_ENV
    return cfg


def _seed_proposals(db_path: str, n: int = 6) -> list[StoryProposalRecord]:
    records = [
        StoryProposalRecord.from_proposal(
            StoryProposal(
                title=f"Story {i+1}",
                description=f"Desc {i+1}",
                acceptance_criteria=["a", "b"],
                story_points=3,
            ),
            handover_id=rk.KICKOFF_HANDOVER_ID,
            task_id=rk.KICKOFF_TASK_ID,
        )
        for i in range(n)
    ]
    persistence.insert_story_proposals(db_path, records)
    return records


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_phase4_arc_requires_persisted_proposals(workspace: Path, gh_env: None) -> None:
    with pytest.raises(rk.HarnessError, match="No persisted proposals"):
        rk.run_phase4_arc(workspace, config=_config(workspace))


def test_phase4_arc_requires_db_path(workspace: Path, gh_env: None) -> None:
    cfg = _config(workspace)
    cfg.database.path = ""
    with pytest.raises(rk.HarnessError, match="database path"):
        rk.run_phase4_arc(workspace, config=cfg)


def test_phase4_arc_prints_full_evidence_transcript(
    workspace: Path,
    db_path: str,
    fake_client: _FakeGitHubClient,
    gh_env: None,
) -> None:
    seeded = _seed_proposals(db_path, n=6)
    buf = io.StringIO()

    rc = rk.run_phase4_arc(workspace, config=_config(workspace), out_stream=buf)

    assert rc == 0
    transcript = buf.getvalue()

    # 1. Pre-approval state shows all pending.
    assert "[PRE] proposal status counts: pending=6 approved=0 written=0" in transcript

    # 2. Refusal evidence appears before approval is recorded.
    refusal_idx = transcript.index("[PHASE4] Refused:")
    approval_idx = transcript.index("[PHASE4] Approval recorded:")
    assert refusal_idx < approval_idx

    # 3. Approval recorded with the right action_type.
    assert "WRITE_GITHUB_PROJECT_V2" in transcript
    assert rk.KICKOFF_TASK_ID in transcript

    # 4. Successful write summary.
    assert "Wrote 6 proposal(s)" in transcript

    # 5. Post-write state shows everything written.
    assert "[POST] proposal status counts: pending=0 approved=0 written=6" in transcript

    # 6. Receipt mapping line per proposal, all titles match.
    for record in seeded:
        assert record.proposed_story_id in transcript
    assert transcript.count("[OK]") == 6
    assert "MISMATCH" not in transcript

    # GitHub side effects: one project_id lookup + one mutation per proposal.
    mutations = [
        c for c in fake_client.calls if "addProjectV2DraftIssue" in c.get("query", "")
    ]
    assert len(mutations) == 6


def test_phase4_arc_is_idempotent_on_rerun(
    workspace: Path,
    db_path: str,
    fake_client: _FakeGitHubClient,
    gh_env: None,
) -> None:
    _seed_proposals(db_path, n=3)
    cfg = _config(workspace)

    rk.run_phase4_arc(workspace, config=cfg, out_stream=io.StringIO())
    calls_after_first = list(fake_client.calls)

    # Second run uses a different approval id so create_pending_approval doesn't collide.
    buf = io.StringIO()
    rk.run_phase4_arc(
        workspace,
        config=cfg,
        out_stream=buf,
        approval_id="approval-kickoff-board-2",
    )

    transcript = buf.getvalue()
    # Second run finds everything already written and short-circuits.
    assert "already written" in transcript.lower()
    # No new mutations.
    new_mutations = [
        c
        for c in fake_client.calls[len(calls_after_first):]
        if "addProjectV2DraftIssue" in c.get("query", "")
    ]
    assert new_mutations == []
