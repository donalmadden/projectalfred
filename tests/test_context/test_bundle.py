"""Tests for `src/alfred/context/bundle.py` — dedup precedence + role rendering."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import get_args

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from alfred.context import (  # noqa: E402
    ROLES,
    ContextBundle,
    ContextItem,
    Role,
    summarize_canonical_handover,
)


def _stub_summarizer(item: ContextItem) -> str:
    return f"SUMMARY({item.path})"


# --------------------------------------------------------------------------- #
# Closed role set
# --------------------------------------------------------------------------- #


def test_role_set_is_exactly_three() -> None:
    assert ROLES == ("scope", "carry_forward", "continuity")
    assert set(get_args(Role)) == {"scope", "carry_forward", "continuity"}


def test_unknown_role_is_rejected_at_construction() -> None:
    import pytest

    with pytest.raises(ValueError):
        ContextItem(path="x.md", role="reference", text="x")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Dedup precedence
# --------------------------------------------------------------------------- #


def test_scope_overrides_continuity_when_paths_collide() -> None:
    bundle = ContextBundle(
        items=(
            ContextItem(path="a.md", role="scope", text="scope-text"),
            ContextItem(
                path="a.md",
                role="continuity",
                text="cont-text",
                is_canonical_handover=True,
            ),
        )
    )
    result = bundle.dedup()
    assert [i.role for i in result.kept] == ["scope"]
    assert [i.role for i in result.dropped] == ["continuity"]


def test_carry_forward_overrides_continuity_when_paths_collide() -> None:
    bundle = ContextBundle(
        items=(
            ContextItem(path="b.md", role="carry_forward", text="carry"),
            ContextItem(
                path="b.md",
                role="continuity",
                text="cont",
                is_canonical_handover=True,
            ),
        )
    )
    result = bundle.dedup()
    assert [i.role for i in result.kept] == ["carry_forward"]
    assert [i.role for i in result.dropped] == ["continuity"]


def test_dedup_preserves_independent_paths() -> None:
    bundle = ContextBundle(
        items=(
            ContextItem(path="a.md", role="scope", text="a"),
            ContextItem(path="b.md", role="continuity", text="b", is_canonical_handover=True),
        )
    )
    result = bundle.dedup()
    assert {i.path for i in result.kept} == {"a.md", "b.md"}
    assert result.dropped == ()


# --------------------------------------------------------------------------- #
# Role rendering rules
# --------------------------------------------------------------------------- #


def test_scope_renders_full_text() -> None:
    bundle = ContextBundle(
        items=(ContextItem(path="x.md", role="scope", text="FULL"),),
    )
    rendered = bundle.render(summarizer=_stub_summarizer)
    assert len(rendered) == 1
    assert rendered[0].render_mode == "full"
    assert rendered[0].rendered_text == "FULL"


def test_carry_forward_non_handover_renders_full_text() -> None:
    bundle = ContextBundle(
        items=(
            ContextItem(
                path="adr/0001.md",
                role="carry_forward",
                text="ADR BODY",
                is_canonical_handover=False,
            ),
        )
    )
    rendered = bundle.render(summarizer=_stub_summarizer)
    assert rendered[0].render_mode == "full"
    assert rendered[0].rendered_text == "ADR BODY"


def test_carry_forward_canonical_handover_renders_summary() -> None:
    bundle = ContextBundle(
        items=(
            ContextItem(
                path="docs/canonical/ALFRED_HANDOVER_16.md",
                role="carry_forward",
                text="full handover text",
                is_canonical_handover=True,
            ),
        )
    )
    rendered = bundle.render(summarizer=_stub_summarizer)
    assert rendered[0].render_mode == "summary"
    assert rendered[0].rendered_text == "SUMMARY(docs/canonical/ALFRED_HANDOVER_16.md)"


def test_continuity_always_renders_summary() -> None:
    bundle = ContextBundle(
        items=(
            ContextItem(
                path="docs/canonical/ALFRED_HANDOVER_16.md",
                role="continuity",
                text="full handover text",
                is_canonical_handover=True,
            ),
        )
    )
    rendered = bundle.render(summarizer=_stub_summarizer)
    assert rendered[0].render_mode == "summary"
    assert rendered[0].rendered_text.startswith("SUMMARY(")


# --------------------------------------------------------------------------- #
# Phase 3 duplicate-context scenario
# --------------------------------------------------------------------------- #


def test_phase_three_scope_continuity_duplication_is_suppressed() -> None:
    handover_path = "docs/canonical/ALFRED_HANDOVER_16.md"
    bundle = ContextBundle(
        items=(
            ContextItem(path=handover_path, role="scope", text="SCOPE-FULL-TEXT"),
            ContextItem(
                path=handover_path,
                role="continuity",
                text="DUPLICATE-CONTINUITY-TEXT",
                is_canonical_handover=True,
            ),
        )
    )

    rendered = bundle.render(summarizer=_stub_summarizer)

    assert len(rendered) == 1
    assert rendered[0].item.role == "scope"
    assert rendered[0].render_mode == "full"
    assert rendered[0].rendered_text == "SCOPE-FULL-TEXT"
    rendered_text = "\n".join(r.rendered_text for r in rendered)
    assert "DUPLICATE-CONTINUITY-TEXT" not in rendered_text
    assert "SUMMARY(" not in rendered_text


# --------------------------------------------------------------------------- #
# Default summarizer routes through the Slice 4 contract extractor
# --------------------------------------------------------------------------- #


def test_default_summarizer_uses_canonical_handover_contract() -> None:
    """The deterministic summary should reflect contract section keys, not
    hardcoded heading strings — proving reuse of Slice 4's extractor."""
    sample = (
        "# Sample\n\n"
        "## CONTEXT — READ THIS FIRST\n"
        "Context body line.\n\n"
        "## WHAT EXISTS TODAY\n"
        "- existing thing\n\n"
        "## TASK OVERVIEW\n"
        "| # | Task |\n|---|---|\n| 1 | do x |\n"
    )
    summary = summarize_canonical_handover(sample)
    # Section keys come from the manifest contract, not from heading strings.
    assert "### context" in summary
    assert "### current_state" in summary
    assert "### task_overview" in summary
    assert "Context body line." in summary
    assert "existing thing" in summary
