"""Tests for ``scripts/generate_phase8_canonical.py`` — metadata and path wiring."""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import generate_phase8_canonical as g8c  # noqa: E402


def test_expected_handover_id_matches_output_filename() -> None:
    assert g8c.OUTPUT_PATH.name == f"{g8c.EXPECTED_HANDOVER_ID}.md"


def test_expected_previous_is_one_less() -> None:
    m_expected = re.search(r"_(\d+)$", g8c.EXPECTED_HANDOVER_ID)
    m_prev = re.search(r"_(\d+)$", g8c.EXPECTED_PREVIOUS_HANDOVER)
    assert m_expected and m_prev
    assert int(m_expected.group(1)) == int(m_prev.group(1)) + 1


def test_source_filename_tracks_previous_canonical_handover() -> None:
    assert g8c.SOURCE_PATH.name == "ALFRED_HANDOVER_6.md"
    assert "canonical" in g8c.SOURCE_PATH.parts


def test_output_path_is_under_docs() -> None:
    assert "docs" in g8c.OUTPUT_PATH.parts
    assert "canonical" in g8c.OUTPUT_PATH.parts


def test_compute_generation_date_is_iso() -> None:
    today = g8c.compute_generation_date()
    parsed = datetime.date.fromisoformat(today)
    assert parsed == datetime.date.today()


def test_failed_output_path_uses_failed_candidate_suffix() -> None:
    failed = g8c.build_failed_output_path(Path("docs/canonical/ALFRED_HANDOVER_7.md"))
    assert failed == Path("docs/archive/ALFRED_HANDOVER_7_FAILED_CANDIDATE.md")


def test_parse_args_defaults_target_canonical_output() -> None:
    args = g8c.parse_args([])
    assert Path(args.output) == Path("docs/canonical/ALFRED_HANDOVER_7.md")
    assert Path(args.source) == Path("docs/canonical/ALFRED_HANDOVER_6.md")
    assert Path(args.failed_output) == Path("docs/archive/ALFRED_HANDOVER_7_FAILED_CANDIDATE.md")
    assert args.historical_context_mode == "summary"


def test_sprint_goal_preserves_existing_docs_governance_state() -> None:
    assert "`docs/DOCS_POLICY.md`" in g8c.SPRINT_GOAL
    assert "`docs/DOCS_MANIFEST.yaml`" in g8c.SPRINT_GOAL
    assert "`docs/archive/` already exist today" in g8c.SPRINT_GOAL
    assert "future work for the next phase" in g8c.SPRINT_GOAL


def test_context_attempt_order_degrades_to_none() -> None:
    assert g8c.build_context_attempt_order("summary") == ["summary", "minimal", "none"]
    assert g8c.build_context_attempt_order("full") == ["full", "summary", "minimal", "none"]


def test_load_historical_context_summary_is_bounded(tmp_path: Path) -> None:
    source = tmp_path / "docs" / "ALFRED_HANDOVER_6.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "**id:** ALFRED_HANDOVER_6\n"
        "**date:** 2026-04-21\n"
        "**author:** Planner\n"
        "**baseline_state:** some baseline\n"
        "- `docs/ALFRED_HANDOVER_5.md`\n\n"
        "## WHAT EXISTS TODAY\n"
        + "\n".join(f"- line {i}" for i in range(40))
        + "\n\n## TASK OVERVIEW\n"
        "| # | Task | Deliverable |\n"
        "|---|---|---|\n"
        "| 1 | Refresh | `docs/ALFRED_HANDOVER_7.md` |\n",
        encoding="utf-8",
    )

    summary = g8c.load_historical_context(source, mode="summary", max_chars=900)
    assert summary is not None
    assert g8c.DOCS_GOVERNANCE_GROUNDING in summary
    assert "Historical source:" in summary
    assert "Historical task overview:" in summary
    assert len(summary) <= 930
    assert "`docs/canonical/ALFRED_HANDOVER_5.md`" in summary


def test_load_historical_context_drops_archive_only_reference_bullets(tmp_path: Path) -> None:
    source = tmp_path / "docs" / "ALFRED_HANDOVER_6.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Alfred's Handover Document #6 — Phase 7\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "- `docs/archive/ALFRED_HANDOVER_6_FAILED_CANDIDATE.md`\n"
        "- `docs/ALFRED_HANDOVER_5.md`\n",
        encoding="utf-8",
    )

    summary = g8c.load_historical_context(source, mode="summary", max_chars=900)

    assert summary is not None
    assert "FAILED_CANDIDATE" not in summary
    assert "`docs/canonical/ALFRED_HANDOVER_5.md`" in summary


def test_load_historical_context_none_mode_returns_none(tmp_path: Path) -> None:
    source = tmp_path / "docs" / "ALFRED_HANDOVER_6.md"
    source.parent.mkdir(parents=True)
    source.write_text("# x\n", encoding="utf-8")
    assert g8c.load_historical_context(source, mode="none") is None


def test_normalise_generated_markdown_rewrites_and_filters_doc_refs() -> None:
    markdown = (
        "## CONTEXT — READ THIS FIRST\n"
        "**Reference Documents:**\n"
        "- `docs/ALFRED_HANDOVER_6.md` — baseline\n"
        "- `docs/archive/ALFRED_HANDOVER_7_FAILED_CANDIDATE.md` — archive\n\n"
        "## WHAT EXISTS TODAY\n"
        "Historical continuity came from `docs/ALFRED_HANDOVER_6.md`.\n"
        "`src/alfred/tools/nonexistent_logging.py` is to be created in this phase.\n"
    )

    normalised = g8c.normalise_generated_markdown(markdown)

    assert "`docs/canonical/ALFRED_HANDOVER_6.md`" in normalised
    assert "`docs/archive/ALFRED_HANDOVER_7_FAILED_CANDIDATE.md`" not in normalised
    assert "`src/alfred/tools/nonexistent_logging.py`" not in normalised
    assert "src/alfred/tools/nonexistent_logging.py" in normalised
