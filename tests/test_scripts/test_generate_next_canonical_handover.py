"""Tests for ``scripts/generate_next_canonical_handover.py`` — metadata and path wiring."""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import generate_next_canonical_handover as gnch  # noqa: E402

from alfred.tools.docs_policy import is_citable_doc


def test_expected_handover_id_matches_output_filename() -> None:
    assert gnch.OUTPUT_PATH.name == f"{gnch.EXPECTED_HANDOVER_ID}.md"


def test_expected_previous_is_one_less() -> None:
    m_expected = re.search(r"_(\d+)$", gnch.EXPECTED_HANDOVER_ID)
    m_prev = re.search(r"_(\d+)$", gnch.EXPECTED_PREVIOUS_HANDOVER)
    assert m_expected and m_prev
    assert int(m_expected.group(1)) == int(m_prev.group(1)) + 1


def test_source_filename_tracks_previous_canonical_handover() -> None:
    assert gnch.SOURCE_PATH.name == f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
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
    assert Path(args.output) == Path(f"docs/canonical/{gnch.EXPECTED_HANDOVER_ID}.md")
    assert Path(args.source) == Path(f"docs/canonical/{gnch.EXPECTED_PREVIOUS_HANDOVER}.md")
    assert Path(args.failed_output) == Path(
        f"docs/archive/{gnch.EXPECTED_HANDOVER_ID}_FAILED_CANDIDATE.md"
    )
    assert args.historical_context_mode == "summary"


def test_previous_canonical_source_is_citable_under_docs_policy() -> None:
    assert is_citable_doc(f"docs/canonical/{gnch.EXPECTED_PREVIOUS_HANDOVER}.md")


def test_context_attempt_order_degrades_to_none() -> None:
    assert gnch.build_context_attempt_order("summary") == ["summary", "minimal", "none"]
    assert gnch.build_context_attempt_order("full") == ["full", "summary", "minimal", "none"]


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

    summary = gnch.load_historical_context(source, mode="summary", max_chars=4500)

    assert summary is not None
    assert "FAILED_CANDIDATE" not in summary
    assert "`docs/canonical/ALFRED_HANDOVER_6.md`" in summary


def test_load_historical_context_none_mode_returns_none(tmp_path: Path) -> None:
    source = tmp_path / "docs" / "ALFRED_HANDOVER_7.md"
    source.parent.mkdir(parents=True)
    source.write_text("# x\n", encoding="utf-8")
    assert gnch.load_historical_context(source, mode="none") is None


def test_validate_required_citable_docs_reports_policy_gaps(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(gnch, "REPO_ROOT", tmp_path)
    source = tmp_path / "docs" / "canonical" / f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    source.parent.mkdir(parents=True)
    source.write_text("# x\n", encoding="utf-8")

    monkeypatch.setattr(
        gnch,
        "AUTHORITATIVE_SCOPE_SELECTION_SPECS",
        (),
    )
    monkeypatch.setattr(
        gnch,
        "is_citable_doc",
        lambda path, repo_root=None: False,
    )

    assert gnch.validate_required_citable_docs(source) == [
        f"docs/canonical/{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    ]


def test_load_historical_context_skips_when_source_already_in_authoritative_scope(
    tmp_path: Path,
) -> None:
    source = tmp_path / "docs" / "canonical" / f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    source.parent.mkdir(parents=True)
    source.write_text("# x\n", encoding="utf-8")
    source_key = gnch._repo_relative_doc_path(source)

    summary = gnch.load_historical_context(
        source,
        mode="summary",
        excluded_doc_paths=(source_key,),
    )

    assert summary is None


def test_build_planner_context_deduplicates_overlap_between_scope_and_history(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(gnch, "REPO_ROOT", tmp_path)
    source = tmp_path / "docs" / "canonical" / f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Alfred's Handover Document #11\n\n"
        "## TASK OVERVIEW\n"
        "| # | Task | Deliverable |\n"
        "|---|---|---|\n"
        f"| 1 | Keep | `docs/canonical/{gnch.EXPECTED_HANDOVER_ID}.md` |\n",
        encoding="utf-8",
    )

    scope = (
        "AUTHORITATIVE\n"
        f"----- BEGIN docs/canonical/{gnch.EXPECTED_PREVIOUS_HANDOVER}.md -----\n"
        "body"
    )

    context, historical_chars = gnch.build_planner_context(scope, source, mode="summary")

    assert context == scope
    assert historical_chars == 0


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


def test_authoritative_scope_includes_context_reference_tags() -> None:
    context_specs = [
        spec for spec in gnch.AUTHORITATIVE_SCOPE_SELECTION_SPECS if spec.source_path.name == "CONTEXT.md"
    ]

    assert len(context_specs) == 1
    assert any(
        selector.path_suffix == "Reference Tags" for selector in context_specs[0].selectors
    )


def test_slice_three_grounding_mentions_canonical_reference_tags() -> None:
    assert "[future-doc: <path>]" in gnch.SPRINT_GOAL
    assert "[future-path: <path>]" in gnch.SPRINT_GOAL
    assert "`CONTEXT.md`" in gnch.DEMO_PLAN_GROUNDING
