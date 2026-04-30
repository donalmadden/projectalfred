"""Phase 4 Task 3 — orchestrated, approval-gated GitHub board write.

Covers the contract from Task 5 of the handover plan:

  - "no approval, no write" — runner refuses; no GitHub calls made
  - "approved, writes exactly persisted proposals" — one create_story
    call per persisted record, in deterministic batch order
  - idempotency — re-running after a partial failure only writes the tail
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from alfred import orchestrator
from alfred.orchestrator import orchestrate
from alfred.schemas.config import AlfredConfig
from alfred.schemas.handover import HandoverContext, HandoverDocument, HandoverTask
from alfred.schemas.story_proposal import StoryProposal, StoryProposalRecord
from alfred.tools import github_api, persistence
from alfred.tools.board_write_contract import BOARD_WRITE_ACTION

HANDOVER_ID = "ALFRED_HANDOVER_11"
TASK_ID = "TASK-SEED-BOARD-001"
GH_TOKEN_ENV = "GITHUB_TOKEN"


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
    """Minimal GitHub client: returns a fixed project id, then sequential item ids."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._next_item = 0

    def post(self, url: str, json: dict[str, Any]) -> _FakeResponse:
        self.calls.append(json)
        query = json.get("query", "")
        if "projectV2(number" in query and "items" not in query:
            return _FakeResponse(
                {"data": {"organization": {"projectV2": {"id": "PROJECT_ABC"}}}}
            )
        if "addProjectV2DraftIssue" in query:
            self._next_item += 1
            return _FakeResponse(
                {
                    "data": {
                        "addProjectV2DraftIssue": {
                            "projectItem": {"id": f"PVTI_{self._next_item:03d}"}
                        }
                    }
                }
            )
        raise AssertionError(f"Unexpected GraphQL call: {query!r}")

    def create_calls(self) -> list[str]:
        """Titles passed to addProjectV2DraftIssue mutations, in order."""
        return [
            c["variables"]["title"]
            for c in self.calls
            if "addProjectV2DraftIssue" in c.get("query", "")
        ]

    def create_bodies(self) -> list[str]:
        """Bodies passed to addProjectV2DraftIssue mutations, in order."""
        return [
            c["variables"]["body"]
            for c in self.calls
            if "addProjectV2DraftIssue" in c.get("query", "")
        ]


@pytest.fixture(autouse=True)
def _restore_runners_and_client():
    original_runners = dict(orchestrator._AGENT_RUNNERS)
    original_client = github_api._client_factory
    yield
    orchestrator._AGENT_RUNNERS.clear()
    orchestrator._AGENT_RUNNERS.update(original_runners)
    github_api.set_client_factory(original_client)


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "alfred.db")


@pytest.fixture
def github_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(GH_TOKEN_ENV, "fake-token")
    return "fake-token"


@pytest.fixture
def fake_client() -> _FakeGitHubClient:
    client = _FakeGitHubClient()
    github_api.set_client_factory(lambda token: client)
    return client


def _config(db: str, *, with_github: bool = True) -> AlfredConfig:
    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = db
    if with_github:
        cfg.github.org = "myorg"
        cfg.github.project_number = 42
        cfg.github.token_env_var = GH_TOKEN_ENV
    cfg.rag.index_path = ""
    return cfg


def _board_writer_task() -> HandoverTask:
    return HandoverTask(
        id=TASK_ID,
        title="Write seeded backlog to GitHub Project V2",
        goal="Project the approved persisted proposals onto the blank board.",
        agent_type="board_writer",
    )


def _handover(task: HandoverTask) -> HandoverDocument:
    return HandoverDocument(
        id=HANDOVER_ID,
        title="Kickoff",
        date=date(2026, 4, 30),
        author="Alfred",
        context=HandoverContext(narrative="Test."),
        tasks=[task],
    )


def _seed_proposals(db: str, n: int = 6) -> list[StoryProposalRecord]:
    records = [
        StoryProposalRecord.from_proposal(
            StoryProposal(
                title=f"Story {i+1}",
                description=f"Description {i+1}",
                acceptance_criteria=["AC1", "AC2"],
                story_points=3,
            ),
            handover_id=HANDOVER_ID,
            task_id=TASK_ID,
        )
        for i in range(n)
    ]
    persistence.insert_story_proposals(db, records)
    return records


def _create_approval(db: str, *, decision: str = "approved") -> str:
    approval_id = "approval-board-1"
    persistence.create_pending_approval(
        db,
        approval_id=approval_id,
        handover_id=HANDOVER_ID,
        action_type=BOARD_WRITE_ACTION,
        item_id=TASK_ID,
        timeout_seconds=3600,
    )
    persistence.record_approval_decision(db, approval_id, decision)
    return approval_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_approval_no_write(db_path: str, github_token: str, fake_client: _FakeGitHubClient) -> None:
    _seed_proposals(db_path, n=6)
    # No approval row created.

    handover = _handover(_board_writer_task())
    result = orchestrate(handover, _config(db_path), db_path=db_path).tasks[0].result

    assert result is not None
    assert result.completed is False
    assert "refused" in result.output_summary.lower()
    assert fake_client.calls == []
    # Status untouched.
    rows = persistence.list_story_proposals(db_path)
    assert all(r.approval_status == "pending" for r in rows)


def test_rejected_approval_blocks_write(
    db_path: str, github_token: str, fake_client: _FakeGitHubClient
) -> None:
    _seed_proposals(db_path, n=6)
    _create_approval(db_path, decision="rejected")

    handover = _handover(_board_writer_task())
    result = orchestrate(handover, _config(db_path), db_path=db_path).tasks[0].result

    assert result is not None
    assert result.completed is False
    assert fake_client.calls == []


def test_approved_writes_exactly_persisted_proposals(
    db_path: str, github_token: str, fake_client: _FakeGitHubClient
) -> None:
    seeded = _seed_proposals(db_path, n=7)
    approval_id = _create_approval(db_path)

    handover = _handover(_board_writer_task())
    result = orchestrate(handover, _config(db_path), db_path=db_path).tasks[0].result

    assert result is not None
    assert result.completed is True
    # One create_story per proposal, in the same order list_story_proposals returns.
    assert fake_client.create_calls() == [r.title for r in seeded]
    # All rows are now 'written' with receipts referencing the approval id.
    rows = persistence.list_story_proposals(db_path)
    assert len(rows) == 7
    assert all(r.approval_status == "written" for r in rows)
    assert all(r.approval_decision_id == approval_id for r in rows)
    receipts = persistence.list_write_receipts(
        db_path, handover_id=HANDOVER_ID, task_id=TASK_ID
    )
    assert len(receipts) == 7
    assert {r["github_title"] for r in receipts} == {s.title for s in seeded}
    assert fake_client.create_bodies()[0] == (
        "Description 1\n\nAcceptance Criteria\n- AC1\n- AC2\n\nStory Points: 3"
    )


def test_runner_refuses_when_github_config_missing(
    db_path: str, fake_client: _FakeGitHubClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(GH_TOKEN_ENV, raising=False)
    _seed_proposals(db_path, n=6)
    _create_approval(db_path)

    handover = _handover(_board_writer_task())
    result = orchestrate(handover, _config(db_path), db_path=db_path).tasks[0].result

    assert result is not None
    assert result.completed is False
    assert fake_client.calls == []
    # Status untouched: with no token there's no work the runner can
    # finish, so it returns before mutating any proposal rows. A later
    # run with a token will replay the gate and stamp them then.
    rows = persistence.list_story_proposals(db_path)
    assert all(r.approval_status == "pending" for r in rows)


def test_idempotent_resume_writes_only_unwritten(
    db_path: str, github_token: str, fake_client: _FakeGitHubClient
) -> None:
    seeded = _seed_proposals(db_path, n=3)
    approval_id = _create_approval(db_path)

    # Simulate a prior partial run: proposal 0 already written.
    persistence.update_story_proposal_status(
        db_path,
        seeded[0].proposed_story_id,
        "approved",
        approval_decision_id=approval_id,
    )
    persistence.record_proposal_write(
        db_path,
        proposed_story_id=seeded[0].proposed_story_id,
        github_item_id="PVTI_PRIOR",
        github_title=seeded[0].title,
        approval_decision_id=approval_id,
    )

    handover = _handover(_board_writer_task())
    result = orchestrate(handover, _config(db_path), db_path=db_path).tasks[0].result

    assert result is not None
    assert result.completed is True
    # Only the two unwritten proposals should hit the GitHub adapter.
    assert fake_client.create_calls() == [seeded[1].title, seeded[2].title]
    receipts = {
        r["proposed_story_id"]: r for r in persistence.list_write_receipts(db_path)
    }
    assert receipts[seeded[0].proposed_story_id]["github_item_id"] == "PVTI_PRIOR"
    assert receipts[seeded[1].proposed_story_id]["github_item_id"] != "PVTI_PRIOR"


def test_rerun_after_full_completion_is_noop(
    db_path: str, github_token: str, fake_client: _FakeGitHubClient
) -> None:
    _seed_proposals(db_path, n=2)
    _create_approval(db_path)

    handover1 = _handover(_board_writer_task())
    orchestrate(handover1, _config(db_path), db_path=db_path)
    calls_after_first = list(fake_client.calls)

    handover2 = _handover(_board_writer_task())
    result = orchestrate(handover2, _config(db_path), db_path=db_path).tasks[0].result

    assert result is not None
    assert result.completed is True
    assert "no work to do" in result.output_summary.lower()
    # Second run made no further GraphQL calls.
    assert fake_client.calls == calls_after_first


def test_story_content_unchanged_after_write(
    db_path: str, github_token: str, fake_client: _FakeGitHubClient
) -> None:
    seeded = _seed_proposals(db_path, n=2)

    _create_approval(db_path)
    handover = _handover(_board_writer_task())
    orchestrate(handover, _config(db_path), db_path=db_path)

    after = {r.proposed_story_id: r for r in persistence.list_story_proposals(db_path)}
    for original in seeded:
        post = after[original.proposed_story_id]
        assert post.title == original.title
        assert post.description == original.description
        assert post.acceptance_criteria == original.acceptance_criteria
        assert post.story_points == original.story_points
