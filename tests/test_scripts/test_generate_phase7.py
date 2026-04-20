"""Tests for ``scripts/generate_phase7.py`` — metadata consistency.

These tests exercise the pure, testable surface of the generator (constants
and the ``compute_generation_date`` helper) without running the end-to-end
pipeline, which requires an LLM, RAG index, and git history.
"""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import generate_phase7 as g7  # noqa: E402


def test_expected_handover_id_matches_output_filename() -> None:
    assert g7.OUTPUT_PATH.name == f"{g7.EXPECTED_HANDOVER_ID}_DRAFT.md"


def test_expected_previous_is_one_less() -> None:
    """Previous handover id should number one less than the expected id."""
    m_expected = re.search(r"_(\d+)$", g7.EXPECTED_HANDOVER_ID)
    m_prev = re.search(r"_(\d+)$", g7.EXPECTED_PREVIOUS_HANDOVER)
    assert m_expected and m_prev
    assert int(m_expected.group(1)) == int(m_prev.group(1)) + 1


def test_output_path_is_under_docs() -> None:
    # docs/ is the canonical location; prevents drift to scripts/ or tmp/.
    parts = g7.OUTPUT_PATH.parts
    assert "docs" in parts


def test_compute_generation_date_is_iso() -> None:
    today = g7.compute_generation_date()
    # Parseable as ISO date.
    parsed = datetime.date.fromisoformat(today)
    assert parsed == datetime.date.today()


def test_identity_constants_are_strings_not_none() -> None:
    for const in (g7.EXPECTED_HANDOVER_ID, g7.EXPECTED_PREVIOUS_HANDOVER, g7.DISPLAY_TITLE):
        assert isinstance(const, str)
        assert const  # non-empty


def test_identity_constants_shape() -> None:
    assert g7.EXPECTED_HANDOVER_ID.startswith("ALFRED_HANDOVER_")
    assert g7.EXPECTED_PREVIOUS_HANDOVER.startswith("ALFRED_HANDOVER_")
