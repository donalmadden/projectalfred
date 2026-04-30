"""Phase 3 Task 4 — gate review reads persisted proposals (no regeneration).

These tests assert two complementary properties:

1. After ``run_demo`` completes, the approval-gate listing comes from the
   ``story_proposals`` SQLite table — not from the in-memory generator
   output. The persisted rows survive the process boundary.

2. A subsequent ``review_only_demo`` invocation lists those same
   proposals and prints the verbatim approval prompt without invoking
   the story generator. The story-runner stub is asserted to have been
   called exactly once across both invocations.
"""
from __future__ import annotations

import io
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import init_demo_workspace as iw  # noqa: E402
import run_kickoff_demo as rk  # noqa: E402

from alfred import orchestrator  # noqa: E402
from alfred.schemas.agent import (  # noqa: E402
    Story,
    StoryGeneratorInput,
    StoryGeneratorOutput,
)
from alfred.schemas.handover import (  # noqa: E402
    HandoverContext,
    HandoverDocument,
    HandoverTask,
)
from alfred.tools.persistence import list_story_proposals  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_runners():
    original = dict(orchestrator._AGENT_RUNNERS)
    yield
    orchestrator._AGENT_RUNNERS.clear()
    orchestrator._AGENT_RUNNERS.update(original)


def _initialised_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "cop_demo"
    iw.init_workspace(workspace)
    return workspace


def _kickoff_handover() -> HandoverDocument:
    return HandoverDocument(
        id=rk.KICKOFF_HANDOVER_ID,
        title="Customer Onboarding Portal Kickoff",
        date=date(2026, 4, 29),
        author="Alfred",
        context=HandoverContext(narrative="Kickoff."),
        tasks=[
            HandoverTask(
                id=rk.KICKOFF_TASK_ID,
                title="Generate Kickoff Backlog",
                goal="Produce 6–8 StoryProposal items.",
                agent_type="story_generator",
            )
        ],
    )


def _stub_compile_fn(handover: HandoverDocument):
    def fn(_markdown: str) -> HandoverDocument:
        return handover
    return fn


def _counting_story_runner():
    """Return ``(runner, calls)`` so tests can assert generator invocations."""
    calls: list[StoryGeneratorInput] = []

    def runner(inp: StoryGeneratorInput) -> StoryGeneratorOutput:
        calls.append(inp)
        return StoryGeneratorOutput(
            stories=[
                Story(
                    title=f"Story {i+1}",
                    description=f"Desc {i+1}",
                    acceptance_criteria=["AC1", "AC2"],
                    story_points=3,
                )
                for i in range(7)
            ],
            rubric_applied="r",
            stories_failing_rubric=[],
        )

    return runner, calls


# ---------------------------------------------------------------------------
# Property 1 — gate listing is sourced from SQLite
# ---------------------------------------------------------------------------


def test_run_demo_persists_proposals_to_sqlite(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover()
    runner, calls = _counting_story_runner()

    rc = rk.run_demo(
        workspace,
        compile_fn=_stub_compile_fn(handover),
        inner_story_runner=runner,
        out_stream=io.StringIO(),
    )
    assert rc == 0
    assert len(calls) == 1

    db_path = str(rk.workspace_db_path(workspace))
    records = list_story_proposals(
        db_path, handover_id=rk.KICKOFF_HANDOVER_ID, task_id=rk.KICKOFF_TASK_ID
    )
    assert len(records) == 7
    assert all(r.approval_status == "pending" for r in records)
    assert {r.title for r in records} == {f"Story {i+1}" for i in range(7)}


def test_run_demo_gate_listing_renders_from_persistence(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover()
    runner, _ = _counting_story_runner()
    buf = io.StringIO()

    rk.run_demo(
        workspace,
        compile_fn=_stub_compile_fn(handover),
        inner_story_runner=runner,
        out_stream=buf,
    )

    output = buf.getvalue()
    assert "7 proposals persisted" in output
    assert "Alfred has proposed 7 draft backlog items" in output


# ---------------------------------------------------------------------------
# Property 2 — review-only path does not regenerate
# ---------------------------------------------------------------------------


def test_review_only_lists_persisted_proposals_without_regenerating(
    tmp_path: Path,
) -> None:
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover()
    runner, calls = _counting_story_runner()

    rk.run_demo(
        workspace,
        compile_fn=_stub_compile_fn(handover),
        inner_story_runner=runner,
        out_stream=io.StringIO(),
    )
    assert len(calls) == 1

    # Simulate a second process: clear runner registry and call
    # review_only_demo. It must not invoke the story runner.
    orchestrator._AGENT_RUNNERS.clear()
    buf = io.StringIO()
    rc = rk.review_only_demo(workspace, out_stream=buf)
    assert rc == 0
    assert len(calls) == 1, "story generator must not be re-invoked"

    output = buf.getvalue()
    assert "[REVIEW]" in output
    assert "7 proposals persisted" in output
    assert "APPROVAL GATE" in output
    assert (
        "Alfred has proposed 7 draft backlog items for the Customer Onboarding Portal."
        in output
    )


def test_review_only_errors_when_no_proposals_persisted(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    with pytest.raises(rk.HarnessError, match="No persisted proposals"):
        rk.review_only_demo(workspace, out_stream=io.StringIO())


def test_review_only_does_not_import_story_generator(tmp_path: Path) -> None:
    """The review-only path must not load or call the story_generator agent.

    We seed persistence by a direct insert (no harness run) and assert the
    review path completes cleanly while the ``story_generator`` runner
    registry stays empty.
    """
    from alfred.schemas.story_proposal import StoryProposal, StoryProposalRecord
    from alfred.tools.persistence import insert_story_proposals

    workspace = _initialised_workspace(tmp_path)
    db_path = str(rk.workspace_db_path(workspace))
    records = [
        StoryProposalRecord.from_proposal(
            StoryProposal(
                title=f"Persisted {i}",
                description="d",
                acceptance_criteria=["a", "b"],
                story_points=3,
            ),
            handover_id=rk.KICKOFF_HANDOVER_ID,
            task_id=rk.KICKOFF_TASK_ID,
        )
        for i in range(6)
    ]
    insert_story_proposals(db_path, records)

    orchestrator._AGENT_RUNNERS.clear()
    buf = io.StringIO()
    rc = rk.review_only_demo(workspace, out_stream=buf)
    assert rc == 0
    assert "story_generator" not in orchestrator._AGENT_RUNNERS
    assert "6 proposals persisted" in buf.getvalue()


# ---------------------------------------------------------------------------
# CLI flag wiring
# ---------------------------------------------------------------------------


def test_main_review_only_flag_routes_to_review_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = tmp_path / "uninit"
    rc = rk.main(["--workspace", str(workspace), "--review-only"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "ERROR:" in err
