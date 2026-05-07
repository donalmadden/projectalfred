"""Slice-7 pre-flight validator tests.

Coverage:

- One isolated negative test per check (A–E), each driving exactly the
  failure it owns and asserting the structured ``check`` id and a
  human-readable, fixture-derived error message.
- A real-ledger regression confirming the live seed ledger plus the
  generator's authoritative scope plan passes preflight.
- A script-boundary negative integration test proving a Check-C
  ``next_handover_id`` mismatch hard-fails ``main()`` before any
  planner / LLM call. Tripwires are patched into the post-preflight
  call sites so a regression that re-orders the gate fires a
  recognisable assertion, not just a non-zero exit code.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from alfred.ledger.loader import load_ledger  # noqa: E402
from alfred.ledger.models import Brief, Phase, PhaseLedger, TaskSeed  # noqa: E402
from alfred.validate import run_preflight  # noqa: E402
from alfred.validate.preflight import (  # noqa: E402
    PreflightError,
    check_carry_forward_ratified,
    check_no_role_collision,
    check_previous_next_handover_match,
    check_reference_tags_parse,
    check_scope_paths_exist,
    format_errors,
)


def _ledger_with_phases(phases: list[Phase]) -> PhaseLedger:
    return PhaseLedger(
        project="preflight_fixture",
        plan_path="docs/active/POST_GRILL_1.md",
        phases=phases,
    )


def _planning_phase(
    *,
    phase_id: int = 99,
    handover_id: str = "ALFRED_HANDOVER_999",
    previous_handover: str = "ALFRED_HANDOVER_998",
    carry_forward: list[int] | None = None,
) -> Phase:
    return Phase(
        id=phase_id,
        title="Fixture phase",
        status="planning",
        handover_id=handover_id,
        previous_handover=previous_handover,
        scope_carry_forward=carry_forward or [],
        brief=Brief(
            title="Fixture phase",
            goal="fixture goal",
            tasks=[
                TaskSeed(id="1", title="t", intent="i"),
            ],
        ),
    )


# ---------------------------------------------------------------------------
# Isolated negative tests — one per check (A–E).
# ---------------------------------------------------------------------------


def test_check_a_flags_missing_scope_path(tmp_path: Path) -> None:
    """Check A names the missing scope path and uses the structured id."""
    real = tmp_path / "exists.md"
    real.write_text("# present\n", encoding="utf-8")
    missing = tmp_path / "absent.md"

    errors = check_scope_paths_exist([real, missing])

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "A_scope_paths_exist"
    assert "absent.md" in error.message
    assert "exists.md" not in error.message  # only the failing path is named


def test_check_b_distinguishes_missing_id_from_unratified_status() -> None:
    """Check B reports separate errors for unknown ids and wrong status."""
    ledger = _ledger_with_phases(
        [
            Phase(
                id=1,
                title="ratified prior",
                status="ratified",
                handover_id="ALFRED_HANDOVER_900",
            ),
            _planning_phase(
                phase_id=2,
                handover_id="ALFRED_HANDOVER_901",
                previous_handover="ALFRED_HANDOVER_900",
            ),
        ]
    )

    errors = check_carry_forward_ratified(
        ledger=ledger,
        carry_forward_phase_ids=[1, 2, 42],
    )

    assert {e.check for e in errors} == {"B_carry_forward_ratified"}
    messages = "\n".join(e.message for e in errors)
    # Phase 2 is the planning row → wrong status, names the status verbatim.
    assert "phase id 2 has status 'planning'" in messages
    # Phase 42 is unknown → distinct missing-id message.
    assert "phase id 42 is not declared" in messages
    # Phase 1 is ratified → no error mentions it.
    assert "phase id 1 " not in messages


def test_check_c_flags_next_handover_mismatch(tmp_path: Path) -> None:
    """Check C names both the declared id and the expected id."""
    previous = tmp_path / "ALFRED_HANDOVER_900.md"
    previous.write_text(
        "# Old handover\n\n"
        "Some text.\n\n"
        "**next_handover_id:** ALFRED_HANDOVER_BAD\n",
        encoding="utf-8",
    )

    errors = check_previous_next_handover_match(
        previous_handover_path=previous,
        expected_handover_id="ALFRED_HANDOVER_901",
    )

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "C_continuity_next_handover_match"
    assert "ALFRED_HANDOVER_BAD" in error.message
    assert "ALFRED_HANDOVER_901" in error.message
    assert previous.as_posix() in error.message


def test_check_c_flags_missing_next_handover_line(tmp_path: Path) -> None:
    """Check C also catches the silent-omission variant (no continuity line)."""
    previous = tmp_path / "ALFRED_HANDOVER_900.md"
    previous.write_text("# Old handover\n\nNo continuity declared.\n", encoding="utf-8")

    errors = check_previous_next_handover_match(
        previous_handover_path=previous,
        expected_handover_id="ALFRED_HANDOVER_901",
    )

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "C_continuity_next_handover_match"
    assert "does not declare" in error.message
    assert "next_handover_id" in error.message


def test_check_d_flags_role_collision_with_paths_and_roles() -> None:
    """Check D names both roles that share a path."""
    errors = check_no_role_collision(
        [
            ("docs/active/X.md", "scope"),
            ("docs/active/Y.md", "carry_forward"),
            ("docs/active/X.md", "continuity"),
        ]
    )

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "D_no_role_collision"
    assert "docs/active/X.md" in error.message
    assert "scope" in error.message and "continuity" in error.message
    assert "docs/active/Y.md" not in error.message


def test_check_e_flags_malformed_reference_tag(tmp_path: Path) -> None:
    """Check E surfaces the parser's line/col snippet for the malformed tag."""
    bad = tmp_path / "bad.md"
    bad.write_text(
        "# title\n\n"
        "Reference tag missing colon: [future-doc oops/path.md]\n",
        encoding="utf-8",
    )
    good = tmp_path / "good.md"
    good.write_text(
        "# title\n\nWell-formed: [future-doc: ok/path.md]\n", encoding="utf-8"
    )

    errors = check_reference_tags_parse([bad, good])

    assert len(errors) == 1
    error = errors[0]
    assert error.check == "E_reference_tags_parse"
    assert bad.as_posix() in error.message
    assert "line 3" in error.message
    assert "future-doc oops" in error.message
    # The well-formed file in the same batch must not emit any error.
    assert good.as_posix() not in error.message


# ---------------------------------------------------------------------------
# Integration regression — real seed ledger passes preflight.
# ---------------------------------------------------------------------------


def test_real_seed_ledger_passes_preflight() -> None:
    """The live PHASE_LEDGER.yaml + the generator's authoritative scope plan
    must pass preflight. This is the regression guard against accidental
    drift between the generator's wiring and the live ledger.
    """
    import generate_next_canonical_handover as gnch

    errors = gnch.run_generator_preflight(gnch.SOURCE_PATH)

    assert errors == [], format_errors(errors)


# ---------------------------------------------------------------------------
# Script-boundary negative integration — Check-C mismatch blocks the planner.
# ---------------------------------------------------------------------------


def test_next_handover_id_mismatch_blocks_planner_invocation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """End-to-end deterministic proof: a previous-handover whose
    ``**next_handover_id:**`` line declares the wrong id forces preflight
    Check C to fail and ``main()`` to exit 1 before any planner / LLM
    call. Tripwires patched onto every post-preflight call site fire a
    labelled ``AssertionError`` if a regression ever lets execution flow
    past the gate. No real LLM is invoked or required.
    """
    import alfred.agents.planner as planner_module
    import generate_next_canonical_handover as gnch

    bad_source = tmp_path / "MISMATCHED_PREVIOUS.md"
    bad_source.write_text(
        "# Spurious previous handover\n\n"
        "Body content.\n\n"
        "**next_handover_id:** ALFRED_HANDOVER_FAKE_TARGET\n",
        encoding="utf-8",
    )

    def _tripwire(name: str):
        def _raise(*_args, **_kwargs):
            raise AssertionError(
                f"{name} was invoked after a Check-C mismatch; the "
                "post-preflight / LLM code path must not run."
            )

        return _raise

    monkeypatch.setattr(
        gnch,
        "validate_required_citable_docs",
        _tripwire("validate_required_citable_docs"),
    )
    monkeypatch.setattr(gnch, "index_corpus", _tripwire("index_corpus"))
    monkeypatch.setattr(
        planner_module,
        "run_planner",
        _tripwire("alfred.agents.planner.run_planner"),
        raising=False,
    )

    rc = gnch.main(["--source", str(bad_source)])

    assert rc == 1
    captured = capsys.readouterr().out
    assert "Pre-flight validation failed" in captured
    assert "[C_continuity_next_handover_match]" in captured
    assert "ALFRED_HANDOVER_FAKE_TARGET" in captured
    assert gnch.EXPECTED_HANDOVER_ID in captured  # the expected id is reported too


# ---------------------------------------------------------------------------
# Sanity: orchestrator wires every check id and surfaces every error.
# ---------------------------------------------------------------------------


def test_run_preflight_orchestrator_collects_every_check_id(tmp_path: Path) -> None:
    """``run_preflight`` runs all five checks without short-circuiting.

    Builds a fixture that fails A, B, C, D, and E simultaneously and
    asserts every check id appears in the returned errors. This locks
    the orchestrator's "report all blocking issues in one pass" contract
    so a regression that adds short-circuit logic is caught.
    """
    missing_scope = tmp_path / "missing.md"  # never created → A fails
    bad_previous = tmp_path / "bad_prev.md"
    bad_previous.write_text(
        "# x\n\n**next_handover_id:** ALFRED_HANDOVER_WRONG\n", encoding="utf-8"
    )
    bad_tags = tmp_path / "bad_tags.md"
    bad_tags.write_text("[future-doc no-colon]\n", encoding="utf-8")

    ledger = _ledger_with_phases(
        [
            _planning_phase(
                phase_id=1,
                handover_id="ALFRED_HANDOVER_TARGET",
                previous_handover="ALFRED_HANDOVER_PRIOR",
            ),
        ]
    )

    errors = run_preflight(
        ledger=ledger,
        scope_paths=[missing_scope],
        carry_forward_phase_ids=[42],  # unknown id → B
        previous_handover_path=bad_previous,  # mismatch → C
        expected_handover_id="ALFRED_HANDOVER_TARGET",
        role_assignments=[
            ("docs/x.md", "scope"),
            ("docs/x.md", "carry_forward"),  # collision → D
        ],
        reference_tag_sources=[bad_tags],  # malformed → E
    )

    assert {e.check for e in errors} == {
        "A_scope_paths_exist",
        "B_carry_forward_ratified",
        "C_continuity_next_handover_match",
        "D_no_role_collision",
        "E_reference_tags_parse",
    }


def test_format_errors_renders_one_line_per_error() -> None:
    """``format_errors`` is the operator-facing surface; lock its shape."""
    rendered = format_errors(
        [
            PreflightError(check="A_scope_paths_exist", message="missing /x"),
            PreflightError(check="D_no_role_collision", message="path /y dual role"),
        ]
    )
    lines = rendered.splitlines()
    assert lines == [
        "- [A_scope_paths_exist] missing /x",
        "- [D_no_role_collision] path /y dual role",
    ]
