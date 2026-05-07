"""Tests for ``scripts/generate_next_canonical_handover.py`` — metadata and path wiring."""
from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import generate_next_canonical_handover as gnch  # noqa: E402

from alfred.context import ContextItem  # noqa: E402
from alfred.ledger.models import Brief, Phase, PhaseLedger, TaskSeed  # noqa: E402
from alfred.render.handover_inputs import render_handover_inputs  # noqa: E402
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


def test_build_planner_context_routes_through_context_bundle_render(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Generator must use ``ContextBundle.render()`` as the assembly mechanism."""
    monkeypatch.setattr(gnch, "REPO_ROOT", tmp_path)
    source = tmp_path / "docs" / "canonical" / f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Alfred's Handover Document #11\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "Continuity body line.\n",
        encoding="utf-8",
    )

    render_calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    original_render = gnch.ContextBundle.render

    def spy_render(self, *, summarizer):  # type: ignore[no-untyped-def]
        render_calls.append(
            (
                tuple(item.role for item in self.items),
                tuple(item.path for item in self.items),
            )
        )
        return original_render(self, summarizer=summarizer)

    monkeypatch.setattr(gnch.ContextBundle, "render", spy_render)
    monkeypatch.setattr(
        gnch,
        "_render_historical_continuity",
        lambda text, *, mode, max_chars=gnch.DEFAULT_CONTEXT_CHARS: "HIST_BLOCK",
    )

    scope = "SCOPE_PACKET"
    context, historical_chars = gnch.build_planner_context(scope, source, mode="summary")

    assert len(render_calls) == 1
    roles, paths = render_calls[0]
    assert "scope" in roles
    assert "continuity" in roles
    source_rel = gnch._repo_relative_doc_path(source)
    assert source_rel in paths

    # Output is the concatenation of bundle-rendered blocks, in role order.
    assert context == "SCOPE_PACKET\n\nHIST_BLOCK"
    assert historical_chars == len("HIST_BLOCK")


def test_build_planner_context_skips_continuity_when_dedup_drops_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """When source path collides with a scope source path, the continuity
    rendering must be omitted — no scope-packet duplication leaks through."""
    monkeypatch.setattr(gnch, "REPO_ROOT", tmp_path)
    source = tmp_path / "docs" / "canonical" / f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    source.parent.mkdir(parents=True)
    source.write_text("# x\n## CONTEXT — READ THIS FIRST\nbody\n", encoding="utf-8")
    source_rel = gnch._repo_relative_doc_path(source)

    summarizer_calls: list[str] = []

    def fake_summary(text, *, mode, max_chars=gnch.DEFAULT_CONTEXT_CHARS):
        summarizer_calls.append(mode)
        return "SHOULD_NOT_APPEAR"

    monkeypatch.setattr(gnch, "_render_historical_continuity", fake_summary)

    scope_packet = gnch.AuthoringContextPacket(
        text="SCOPE_BODY",
        source_doc_paths=(source_rel,),
        selected_sections=(),
        facts=(),
        source_char_count=10,
        packet_char_count=10,
    )

    context, historical_chars = gnch.build_planner_context(
        scope_packet, source, mode="summary"
    )

    assert context == "SCOPE_BODY"
    assert historical_chars == 0
    assert summarizer_calls == []  # continuity was dropped before rendering


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


def test_authoritative_scope_includes_phase_ledger_brief_and_context_roles() -> None:
    context_specs = [
        spec for spec in gnch.AUTHORITATIVE_SCOPE_SELECTION_SPECS if spec.source_path.name == "CONTEXT.md"
    ]

    assert len(context_specs) == 1
    assert any(
        selector.path_suffix == "Phase Ledger" for selector in context_specs[0].selectors
    )
    assert any(
        selector.path_suffix == "Brief" for selector in context_specs[0].selectors
    )
    assert any(
        selector.path_suffix == "Context Roles" for selector in context_specs[0].selectors
    )
    assert any(
        selector.path_suffix == "Doc Class" for selector in context_specs[0].selectors
    )


def test_sprint_goal_and_grounding_are_renderer_derived() -> None:
    """Identity-bearing globals must come from ``HANDOVER_INPUTS``.

    Asserts the wiring rather than prose substrings tied to a specific
    phase number. The ground truth is the renderer over the live ledger;
    if the planning row's brief changes, these globals should follow
    automatically.
    """
    assert gnch.SPRINT_GOAL == gnch.HANDOVER_INPUTS.sprint_goal
    assert gnch.DEMO_PLAN_GROUNDING == gnch.HANDOVER_INPUTS.demo_plan_grounding

    # The renderer produces a non-empty grounding block that cites at least
    # one of the active phase's declared scope sources.
    active = gnch.HANDOVER_INPUTS
    assert active.sprint_goal.strip()
    assert active.demo_plan_grounding.strip()
    assert "deterministic" in active.demo_plan_grounding


def test_all_identity_globals_track_handover_inputs() -> None:
    """Every identity-bearing module global must equal its renderer source.

    This is the wiring contract for Slice 6: if these ever drift, the
    generator has reintroduced a hand-edited literal somewhere.
    """
    inputs = gnch.HANDOVER_INPUTS
    assert gnch.EXPECTED_HANDOVER_ID == inputs.handover_id
    assert gnch.EXPECTED_PREVIOUS_HANDOVER == inputs.previous_handover
    assert gnch.DISPLAY_TITLE == inputs.display_title
    assert gnch.SOURCE_FILENAME == f"{inputs.previous_handover}.md"
    assert gnch.FAILED_FILENAME == f"{inputs.handover_id}_FAILED_CANDIDATE.md"


def _fixture_ledger_with(
    *,
    handover_id: str,
    previous_handover: str,
    title: str,
    goal: str,
) -> PhaseLedger:
    return PhaseLedger(
        project="renderer_wiring_fixture",
        plan_path="docs/active/POST_GRILL_1.md",
        phases=[
            Phase(
                id=1,
                title="Earlier ratified",
                status="ratified",
                handover_id=previous_handover,
            ),
            Phase(
                id=2,
                title=title,
                status="planning",
                handover_id=handover_id,
                previous_handover=previous_handover,
                scope_sources=["docs/active/POST_GRILL_1.md"],
                brief=Brief(
                    title=title,
                    goal=goal,
                    hard_rules=["fixture rule"],
                    tasks=[
                        TaskSeed(
                            id="1",
                            title="Fixture task",
                            intent="Prove the script's defaults follow the renderer.",
                        ),
                    ],
                ),
            ),
        ],
    )


def test_renderer_drives_argparse_defaults_over_a_fixture_ledger() -> None:
    """A different ledger ⇒ different argparse defaults — no prose pinning."""
    fixture = _fixture_ledger_with(
        handover_id="ALFRED_HANDOVER_999",
        previous_handover="ALFRED_HANDOVER_998",
        title="Fixture phase title",
        goal="Fixture goal that drives sprint-goal rendering deterministically.",
    )
    inputs = render_handover_inputs(fixture)

    assert inputs.argparse_defaults.source_default == (
        "docs/canonical/ALFRED_HANDOVER_998.md"
    )
    assert inputs.argparse_defaults.output_default == (
        "docs/canonical/ALFRED_HANDOVER_999.md"
    )
    assert inputs.argparse_defaults.failed_output_default == (
        "docs/archive/ALFRED_HANDOVER_999_FAILED_CANDIDATE.md"
    )
    # Sprint goal includes brief.goal verbatim and the hard-rules header.
    assert inputs.sprint_goal.startswith(
        "Fixture goal that drives sprint-goal rendering deterministically."
    )
    assert "Hard rules" in inputs.sprint_goal
    # Display title matches the fixture brief title (and phase title).
    assert inputs.display_title == "Fixture phase title"


def test_dry_run_output_reflects_renderer_derived_identity() -> None:
    """``--dry-run`` reports the live renderer's identity and would-write paths.

    Pin the assertions to ``HANDOVER_INPUTS`` rather than to specific phase
    numbers so this test stays green across phase advances.
    """
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_next_canonical_handover.py"), "--dry-run"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    out = completed.stdout
    inputs = gnch.HANDOVER_INPUTS

    assert "--- DRY RUN: renderer-derived identity ---" in out
    assert f"# {inputs.display_title}" in out
    assert f"id: {inputs.handover_id}" in out
    assert f"previous_handover: {inputs.previous_handover}" in out
    assert f"docs/canonical/{inputs.previous_handover}.md" in out
    assert f"docs/canonical/{inputs.handover_id}.md" in out
    assert f"docs/archive/{inputs.handover_id}_FAILED_CANDIDATE.md" in out
    assert "no LLM call, no files modified" in out


def test_dry_run_does_not_write_canonical_output(tmp_path: Path) -> None:
    """``--dry-run`` must not touch the canonical or failed output paths."""
    fake_output = tmp_path / "fake_canonical.md"
    fake_failed = tmp_path / "fake_failed.md"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/generate_next_canonical_handover.py"),
            "--dry-run",
            "--output",
            str(fake_output),
            "--failed-output",
            str(fake_failed),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert not fake_output.exists()
    assert not fake_failed.exists()


def _legacy_split_level2_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_key = None
    in_fence = False

    for line in markdown.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            if current_key is not None:
                sections[current_key].append(line)
            continue
        if not in_fence and line.startswith("## "):
            current_key = line[3:].strip().lower()
            sections[current_key] = []
            continue
        if current_key is not None:
            sections[current_key].append(line)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _legacy_summary_context(source_path: Path, *, max_chars: int) -> str:
    text = source_path.read_text(encoding="utf-8")
    sections = _legacy_split_level2_sections(text)
    title = gnch._extract_title(text)
    metadata = gnch._extract_metadata_lines(text)
    context_body = sections.get("context — read this first", "")
    what_exists = sections.get("what exists today", "")
    produces = sections.get("what this phase produces", "") or sections.get(
        "what this handover produces", ""
    )
    task_overview = sections.get("task overview", "")

    parts: list[str] = [
        "Use this previous canonical handover for continuity only. Treat repo facts, "
        "validator findings, reference-doc checks, and current git history as more "
        "authoritative than any stale content from the earlier phase handover.",
        gnch.DEMO_PLAN_GROUNDING,
        "Historical source: previous canonical handover (continuity only).",
        f"Historical title: {title}",
    ]
    if metadata:
        parts.append("Historical metadata:")
        parts.extend(metadata[:5])

    ref_docs = gnch._normalise_reference_bullets(
        gnch._extract_bullets(context_body, max_items=4)
    )
    if ref_docs:
        parts.append("Historical reference documents:")
        parts.extend(ref_docs)

    task_rows = [
        gnch._normalise_historical_text(line)
        for line in gnch._extract_table_rows(task_overview, max_rows=8)
    ]
    if task_rows:
        parts.append("Historical task overview:")
        parts.extend(task_rows)

    current_lines = [
        gnch._normalise_historical_text(line)
        for line in gnch._extract_signal_lines(what_exists, max_lines=10)
    ]
    if current_lines:
        parts.append("Historical WHAT EXISTS TODAY snapshot (may be stale):")
        parts.extend(current_lines)

    produces_lines = [
        gnch._normalise_historical_text(line)
        for line in gnch._extract_bullets(produces, max_items=8)
    ]
    if produces_lines:
        parts.append("Historical planned deliverables:")
        parts.extend(produces_lines)

    return gnch._truncate_context("\n".join(parts), max_chars=max_chars)


def test_load_historical_context_summary_is_byte_identical_for_handover_12() -> None:
    source = ROOT / "docs" / "canonical" / "ALFRED_HANDOVER_12.md"

    expected = _legacy_summary_context(source, max_chars=gnch.DEFAULT_CONTEXT_CHARS)
    actual = gnch.load_historical_context(
        source,
        mode="summary",
        max_chars=gnch.DEFAULT_CONTEXT_CHARS,
    )

    assert actual == expected


def test_build_planner_context_renders_carry_forward_non_handover_full_text(
    tmp_path: Path,
) -> None:
    """A non-handover ``carry_forward`` item must render its full text."""
    source = tmp_path / "docs" / "canonical" / f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    source.parent.mkdir(parents=True)
    # Make source nonexistent so continuity is omitted and we isolate carry_forward.
    carry = ContextItem(
        path="docs/adr/0007-context-roles.md",
        role="carry_forward",
        text="ADR 0007 BODY — full carry-forward text.",
        is_canonical_handover=False,
    )

    context, historical_chars = gnch.build_planner_context(
        "SCOPE_PACKET",
        source,
        mode="none",
        carry_forward_items=(carry,),
    )

    assert context is not None
    assert "SCOPE_PACKET" in context
    assert "ADR 0007 BODY — full carry-forward text." in context
    assert historical_chars == 0


def test_build_planner_context_renders_carry_forward_canonical_handover_as_summary(
    tmp_path: Path,
) -> None:
    """A canonical-handover ``carry_forward`` item must render via the
    contract-driven deterministic summary, not its raw full text."""
    source = tmp_path / "docs" / "canonical" / f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    source.parent.mkdir(parents=True)

    handover_markdown = (
        "# Old Handover\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "Carried context body line.\n\n"
        "## TASK OVERVIEW\n"
        "| # | Task |\n|---|---|\n| 1 | do x |\n\n"
        "## HARD RULES\n"
        "UNIQUE_RAW_TOKEN_THAT_SHOULD_NOT_LEAK\n"
    )
    carry = ContextItem(
        path="docs/canonical/ALFRED_HANDOVER_15.md",
        role="carry_forward",
        text=handover_markdown,
        is_canonical_handover=True,
    )

    context, historical_chars = gnch.build_planner_context(
        "SCOPE_PACKET",
        source,
        mode="none",
        carry_forward_items=(carry,),
    )

    assert context is not None
    assert "SCOPE_PACKET" in context
    # Summary surfaces contract section keys (per summarize_canonical_handover)…
    assert "### context" in context
    assert "Carried context body line." in context
    # …but does not include arbitrary out-of-section raw text.
    assert "UNIQUE_RAW_TOKEN_THAT_SHOULD_NOT_LEAK" not in context
    assert historical_chars == 0


def test_build_planner_context_rejects_mistagged_carry_forward_items(
    tmp_path: Path,
) -> None:
    """Defensive: callers must hand role-tagged items, not silently mixed roles."""
    import pytest

    source = tmp_path / "docs" / "canonical" / f"{gnch.EXPECTED_PREVIOUS_HANDOVER}.md"
    source.parent.mkdir(parents=True)
    bogus = ContextItem(path="x.md", role="scope", text="x")

    with pytest.raises(ValueError):
        gnch.build_planner_context(
            "SCOPE",
            source,
            mode="none",
            carry_forward_items=(bogus,),
        )
