"""Tests for ``scripts/generate_next_canonical_handover.py`` — metadata and path wiring."""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import generate_next_canonical_handover as gnch  # noqa: E402


def test_expected_handover_id_matches_output_filename() -> None:
    assert gnch.OUTPUT_PATH.name == f"{gnch.EXPECTED_HANDOVER_ID}.md"


def test_expected_previous_is_one_less() -> None:
    m_expected = re.search(r"_(\d+)$", gnch.EXPECTED_HANDOVER_ID)
    m_prev = re.search(r"_(\d+)$", gnch.EXPECTED_PREVIOUS_HANDOVER)
    assert m_expected and m_prev
    assert int(m_expected.group(1)) == int(m_prev.group(1)) + 1


def test_source_filename_tracks_previous_canonical_handover() -> None:
    assert gnch.SOURCE_PATH.name == "ALFRED_HANDOVER_7.md"
    assert "canonical" in gnch.SOURCE_PATH.parts


def test_output_path_is_under_docs() -> None:
    assert "docs" in gnch.OUTPUT_PATH.parts
    assert "canonical" in gnch.OUTPUT_PATH.parts


def test_compute_generation_date_is_iso() -> None:
    today = gnch.compute_generation_date()
    parsed = datetime.date.fromisoformat(today)
    assert parsed == datetime.date.today()


def test_failed_output_path_uses_failed_candidate_suffix() -> None:
    failed = gnch.build_failed_output_path(Path("docs/canonical/ALFRED_HANDOVER_8.md"))
    assert failed == Path("docs/archive/ALFRED_HANDOVER_8_FAILED_CANDIDATE.md")


def test_parse_args_defaults_target_canonical_output() -> None:
    args = gnch.parse_args([])
    assert Path(args.output) == Path("docs/canonical/ALFRED_HANDOVER_8.md")
    assert Path(args.source) == Path("docs/canonical/ALFRED_HANDOVER_7.md")
    assert Path(args.failed_output) == Path("docs/archive/ALFRED_HANDOVER_8_FAILED_CANDIDATE.md")
    assert args.historical_context_mode == "summary"


def test_sprint_goal_is_scoped_to_demo_phase_1() -> None:
    assert "Phase 1 of the blank-project kickoff demo plan" in gnch.SPRINT_GOAL
    assert "Phase 2–5 deliverables" in gnch.SPRINT_GOAL
    assert "blank GitHub Project board" in gnch.SPRINT_GOAL


def test_context_attempt_order_degrades_to_none() -> None:
    assert gnch.build_context_attempt_order("summary") == ["summary", "minimal", "none"]
    assert gnch.build_context_attempt_order("full") == ["full", "summary", "minimal", "none"]


def test_load_historical_context_summary_is_bounded(tmp_path: Path) -> None:
    source = tmp_path / "docs" / "ALFRED_HANDOVER_7.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Alfred's Handover Document #7 — Phase 8\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_7\n"
        "**date:** 2026-04-21\n"
        "**author:** Planner\n"
        "**baseline_state:** some baseline\n"
        "- `docs/ALFRED_HANDOVER_6.md`\n\n"
        "## WHAT EXISTS TODAY\n"
        + "\n".join(f"- line {i}" for i in range(40))
        + "\n\n## TASK OVERVIEW\n"
        "| # | Task | Deliverable |\n"
        "|---|---|---|\n"
        "| 1 | Refresh | `docs/ALFRED_HANDOVER_8.md` |\n",
        encoding="utf-8",
    )

    summary = gnch.load_historical_context(source, mode="summary", max_chars=2500)
    assert summary is not None
    assert gnch.DEMO_PLAN_GROUNDING in summary
    assert "Historical source:" in summary
    assert "Historical task overview:" in summary
    assert len(summary) <= 2530
    assert "`docs/canonical/ALFRED_HANDOVER_6.md`" in summary


def test_load_historical_context_drops_archive_only_reference_bullets(tmp_path: Path) -> None:
    source = tmp_path / "docs" / "ALFRED_HANDOVER_7.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Alfred's Handover Document #7 — Phase 8\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "- `docs/archive/ALFRED_HANDOVER_7_FAILED_CANDIDATE.md`\n"
        "- `docs/ALFRED_HANDOVER_6.md`\n",
        encoding="utf-8",
    )

    summary = gnch.load_historical_context(source, mode="summary", max_chars=2500)

    assert summary is not None
    assert "FAILED_CANDIDATE" not in summary
    assert "`docs/canonical/ALFRED_HANDOVER_6.md`" in summary


def test_load_historical_context_none_mode_returns_none(tmp_path: Path) -> None:
    source = tmp_path / "docs" / "ALFRED_HANDOVER_7.md"
    source.parent.mkdir(parents=True)
    source.write_text("# x\n", encoding="utf-8")
    assert gnch.load_historical_context(source, mode="none") is None


def test_normalise_generated_markdown_rewrites_and_filters_doc_refs() -> None:
    markdown = (
        "## CONTEXT — READ THIS FIRST\n"
        "**Reference Documents:**\n"
        "- `docs/ALFRED_HANDOVER_7.md` — baseline\n"
        "- `docs/archive/ALFRED_HANDOVER_8_FAILED_CANDIDATE.md` — archive\n\n"
        "## WHAT EXISTS TODAY\n"
        "Historical continuity came from `docs/ALFRED_HANDOVER_7.md`.\n"
        "`src/alfred/tools/nonexistent_logging.py` is to be created in this phase.\n"
    )

    normalised = gnch.normalise_generated_markdown(markdown)

    assert "`docs/canonical/ALFRED_HANDOVER_7.md`" in normalised
    assert "`docs/archive/ALFRED_HANDOVER_8_FAILED_CANDIDATE.md`" not in normalised
    assert "`src/alfred/tools/nonexistent_logging.py`" not in normalised
    assert "src/alfred/tools/nonexistent_logging.py" in normalised
