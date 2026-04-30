"""Tests for ``scripts/run_kickoff_demo.py``.

The harness invokes the compiler agent (LLM) and the story generator
(LLM) on the real path. Tests inject deterministic stand-ins for both
so the suite never hits a network or requires an API key.
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


def _stub_compile_fn(handover: HandoverDocument):
    def fn(_markdown: str) -> HandoverDocument:
        return handover
    return fn


def _kickoff_handover_with_task(agent_type: str = "story_generator") -> HandoverDocument:
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
                agent_type=agent_type,
            )
        ],
    )


def _stories(n: int) -> list[Story]:
    return [
        Story(
            title=f"Story {i+1}",
            description=f"Description {i+1}",
            acceptance_criteria=["AC1", "AC2"],
            story_points=3,
        )
        for i in range(n)
    ]


def _stub_story_runner(stories: list[Story]):
    def runner(_input: StoryGeneratorInput) -> StoryGeneratorOutput:
        return StoryGeneratorOutput(
            stories=stories,
            rubric_applied="test-rubric",
            stories_failing_rubric=[],
        )
    return runner


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_build_kickoff_markdown_includes_required_sections() -> None:
    md = rk.build_kickoff_markdown("CHARTER TEXT")
    assert "## CONTEXT" in md
    assert "## WHAT EXISTS TODAY" in md
    assert "## KICKOFF GOALS" in md
    assert "## PROPOSED BACKLOG" in md
    assert f"## TASK {rk.KICKOFF_TASK_ID}" in md
    assert "## APPROVAL GATE" in md
    assert "## WHAT NOT TO DO" in md
    assert "## POST-MORTEM" in md
    assert "story_generator" in md
    assert "CHARTER TEXT" in md


def test_approval_prompt_template_is_verbatim_with_substitution() -> None:
    rendered = rk.APPROVAL_PROMPT_TEMPLATE.format(n=7)
    assert (
        rendered
        == "Alfred has proposed 7 draft backlog items for the Customer Onboarding Portal. "
        "Reviewing now will not modify the board. "
        "Approve to write these items to the GitHub Project."
    )


def test_render_proposal_listing_includes_all_fields() -> None:
    out = StoryGeneratorOutput(
        stories=[
            Story(
                title="Define onboarding journey",
                description="End-to-end flow.",
                acceptance_criteria=["bullet a", "bullet b"],
                story_points=5,
            )
        ],
        rubric_applied="r",
    )
    rendered = rk.render_proposal_listing(out)
    assert "1 proposals generated" in rendered
    assert "Define onboarding journey" in rendered
    assert "(5 pts)" in rendered
    assert "End-to-end flow." in rendered
    assert "- bullet a" in rendered
    assert "- bullet b" in rendered


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_persist_writes_to_frozen_path(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    target = rk.persist_kickoff_handover(workspace, "MARKDOWN")
    assert target == workspace / "docs" / "handovers" / rk.KICKOFF_HANDOVER_FILENAME
    assert target.read_text(encoding="utf-8") == "MARKDOWN"


def test_persist_fails_without_handovers_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        rk.persist_kickoff_handover(tmp_path / "missing", "X")


# ---------------------------------------------------------------------------
# run_demo end-to-end (with injection)
# ---------------------------------------------------------------------------


def test_run_demo_happy_path_prints_gate_and_returns_zero(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover_with_task()
    buf = io.StringIO()

    rc = rk.run_demo(
        workspace,
        compile_fn=_stub_compile_fn(handover),
        inner_story_runner=_stub_story_runner(_stories(7)),
        out_stream=buf,
    )

    output = buf.getvalue()
    assert rc == 0
    assert "[INIT] Workspace verified" in output
    assert "[PERSIST] Wrote" in output
    assert "[COMPILE] HandoverDocument compiled" in output
    assert "[ORCHESTRATE] Dispatching TASK-SEED-BOARD-001" in output
    assert "7 proposals persisted" in output
    assert "APPROVAL GATE" in output
    assert (
        "Alfred has proposed 7 draft backlog items for the Customer Onboarding Portal."
        in output
    )
    persisted = workspace / "docs" / "handovers" / rk.KICKOFF_HANDOVER_FILENAME
    assert persisted.is_file()
    assert "TASK-SEED-BOARD-001" in persisted.read_text(encoding="utf-8")


def test_run_demo_accepts_six_proposals(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover_with_task()
    rc = rk.run_demo(
        workspace,
        compile_fn=_stub_compile_fn(handover),
        inner_story_runner=_stub_story_runner(_stories(6)),
        out_stream=io.StringIO(),
    )
    assert rc == 0


def test_run_demo_accepts_eight_proposals(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover_with_task()
    rc = rk.run_demo(
        workspace,
        compile_fn=_stub_compile_fn(handover),
        inner_story_runner=_stub_story_runner(_stories(8)),
        out_stream=io.StringIO(),
    )
    assert rc == 0


def test_run_demo_rejects_count_below_six(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover_with_task()
    with pytest.raises(rk.HarnessError, match="produced 5 proposals"):
        rk.run_demo(
            workspace,
            compile_fn=_stub_compile_fn(handover),
            inner_story_runner=_stub_story_runner(_stories(5)),
            out_stream=io.StringIO(),
        )


def test_run_demo_rejects_count_above_eight(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover_with_task()
    with pytest.raises(rk.HarnessError, match="produced 9 proposals"):
        rk.run_demo(
            workspace,
            compile_fn=_stub_compile_fn(handover),
            inner_story_runner=_stub_story_runner(_stories(9)),
            out_stream=io.StringIO(),
        )


def test_run_demo_aborts_when_workspace_uninitialised(tmp_path: Path) -> None:
    workspace = tmp_path / "uninit"
    with pytest.raises(rk.HarnessError, match="not initialised"):
        rk.run_demo(
            workspace,
            compile_fn=_stub_compile_fn(_kickoff_handover_with_task()),
            inner_story_runner=_stub_story_runner(_stories(7)),
            out_stream=io.StringIO(),
        )


def test_run_demo_aborts_when_compiled_task_missing(tmp_path: Path) -> None:
    workspace = _initialised_workspace(tmp_path)
    bad = HandoverDocument(
        id=rk.KICKOFF_HANDOVER_ID,
        title="Kickoff",
        date=date(2026, 4, 29),
        author="Alfred",
        context=HandoverContext(narrative="X"),
        tasks=[
            HandoverTask(
                id="OTHER-TASK",
                title="Wrong",
                goal="Wrong",
                agent_type="story_generator",
            )
        ],
    )
    with pytest.raises(rk.HarnessError, match="missing task TASK-SEED-BOARD-001"):
        rk.run_demo(
            workspace,
            compile_fn=_stub_compile_fn(bad),
            inner_story_runner=_stub_story_runner(_stories(7)),
            out_stream=io.StringIO(),
        )


def test_run_demo_aborts_when_runner_not_invoked(tmp_path: Path) -> None:
    """If the compiled task has the wrong agent_type the orchestrator won't
    dispatch to story_generator and the harness must raise."""
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover_with_task(agent_type="planner")  # wrong!
    with pytest.raises(rk.HarnessError, match="was not invoked"):
        rk.run_demo(
            workspace,
            compile_fn=_stub_compile_fn(handover),
            inner_story_runner=_stub_story_runner(_stories(7)),
            out_stream=io.StringIO(),
        )


def test_run_demo_does_not_import_github_api_for_writes(tmp_path: Path) -> None:
    """No board mutation: the harness must not write to GitHub.

    We assert the harness module itself doesn't bind any board-mutation
    helper from github_api. (The orchestrator may transitively read board
    state, but with default_demo_config that path is short-circuited.)
    """
    workspace = _initialised_workspace(tmp_path)
    handover = _kickoff_handover_with_task()
    rk.run_demo(
        workspace,
        compile_fn=_stub_compile_fn(handover),
        inner_story_runner=_stub_story_runner(_stories(7)),
        out_stream=io.StringIO(),
    )
    # The harness module must not have imported any github_api write helper
    import scripts.run_kickoff_demo as harness_mod  # noqa: F401
    assert not hasattr(rk, "create_story_on_board")
    assert not hasattr(rk, "write_to_board")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_main_cli_errors_on_uninitialised_workspace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = tmp_path / "uninit"
    rc = rk.main(["--workspace", str(workspace)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "ERROR:" in err
