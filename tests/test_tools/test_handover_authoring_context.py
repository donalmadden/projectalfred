"""Tests for deterministic handover authoring context helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from alfred.tools.handover_authoring_context import (
    DocumentSelectionSpec,
    SectionSelector,
    build_authoring_context_packet,
    index_markdown_document,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_index_markdown_document_tracks_nested_paths_and_tags(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "PLAN.md"
    _write(
        doc,
        "# Plan\n\n"
        "## Hard Rules\n"
        "- one\n\n"
        "## Phase Plan\n"
        "### Phase 3 — Carry Proposed Stories As First-Class Runtime State\n"
        "**Goal:** Keep state.\n",
    )

    indexed = index_markdown_document(doc)

    assert indexed.title == "Plan"
    assert indexed.sections[0].display_path == "Plan"
    assert indexed.sections[1].display_path == "Plan > Hard Rules"
    assert indexed.sections[1].tags == ("hard_rules",)
    assert indexed.sections[3].display_path.endswith(
        "Phase Plan > Phase 3 — Carry Proposed Stories As First-Class Runtime State"
    )
    assert "phase_detail" in indexed.sections[3].tags


def test_build_authoring_context_packet_selects_requested_sections_and_facts(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    doc = repo_root / "docs" / "PLAN.md"
    _write(
        doc,
        "# Plan\n\n"
        "## Hard Rules\n"
        "- Do not drift.\n\n"
        "## Phase Plan\n"
        "### Phase 3 — Carry Proposed Stories As First-Class Runtime State\n"
        "**Goal:** Preserve proposals.\n"
        "- Keep approval state.\n\n"
        "### Phase 4 — Close The HITL Gate Into GitHub Board Writes\n"
        "- future.\n",
    )

    packet = build_authoring_context_packet(
        (
            DocumentSelectionSpec(
                source_path=doc,
                selectors=(
                    SectionSelector("Hard Rules", "constraints"),
                    SectionSelector(
                        "Phase Plan > Phase 3 — Carry Proposed Stories As First-Class Runtime State",
                        "active phase",
                    ),
                ),
            ),
        ),
        repo_root=repo_root,
        intro_lines=("INTRO",),
    )

    assert packet.source_doc_paths == ("docs/PLAN.md",)
    assert packet.packet_char_count > 0
    assert "Do not drift." in packet.text
    assert "Goal: Preserve proposals." in packet.text
    assert "Phase 4 — Close The HITL Gate Into GitHub Board Writes" not in packet.text


def test_build_authoring_context_packet_requires_declared_section(tmp_path: Path) -> None:
    repo_root = tmp_path
    doc = repo_root / "docs" / "PLAN.md"
    _write(doc, "# Plan\n\n## Hard Rules\n- one\n")

    with pytest.raises(ValueError, match="missing required section path suffix"):
        build_authoring_context_packet(
            (
                DocumentSelectionSpec(
                    source_path=doc,
                    selectors=(SectionSelector("Missing Section", "broken"),),
                ),
            ),
            repo_root=repo_root,
            intro_lines=("INTRO",),
        )
