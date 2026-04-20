"""Eval harness runner.

Discovers every fixture in evals/fixtures/*.json (skipping schema.json),
scores each one with evals/scorer.py, prints a human-readable table to stdout,
and exits non-zero if the pass rate falls below EVAL_PASS_THRESHOLD.

Usage:
    python evals/run_evals.py

Environment:
    EVAL_PASS_THRESHOLD  float in [0, 1], default 0.8
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_EVALS_DIR = Path(__file__).parent
_FIXTURES_DIR = _EVALS_DIR / "fixtures"
_SCHEMA_FILENAME = "schema.json"
_DEFAULT_THRESHOLD = 0.8

# Ensure the project root is importable so `from evals.scorer import …` works
# when the script is run directly (python evals/run_evals.py).
_PROJECT_ROOT = _EVALS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evals.scorer import EvalResult, score_fixture  # noqa: E402,I001


# ---------------------------------------------------------------------------
# Report table
# ---------------------------------------------------------------------------

_COL_ID = 42
_COL_STATUS = 6
_COL_SCORE = 5
_COL_NOTES = 40
_SEP = "-" * (_COL_ID + _COL_STATUS + _COL_SCORE + _COL_NOTES + 9)


def _header() -> str:
    return (
        f"{'Fixture ID':<{_COL_ID}} | {'Status':<{_COL_STATUS}} | "
        f"{'Score':<{_COL_SCORE}} | Notes"
    )


def _row(result: EvalResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    notes = result.diff[:_COL_NOTES] if result.diff else ""
    return (
        f"{result.fixture_id:<{_COL_ID}} | {status:<{_COL_STATUS}} | "
        f"{result.score:<{_COL_SCORE}.2f} | {notes}"
    )


def _print_report(results: list[EvalResult], pass_rate: float, threshold: float) -> None:
    print(_header())
    print(_SEP)
    for r in results:
        print(_row(r))
    print(_SEP)
    passed = sum(1 for r in results if r.passed)
    status = "OK" if pass_rate >= threshold else "FAIL"
    print(
        f"Pass rate: {passed}/{len(results)} ({pass_rate:.2f})"
        f" {'≥' if pass_rate >= threshold else '<'} threshold {threshold:.2f} → {status}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    threshold = float(os.environ.get("EVAL_PASS_THRESHOLD", str(_DEFAULT_THRESHOLD)))

    fixture_paths = sorted(
        p for p in _FIXTURES_DIR.glob("*.json") if p.name != _SCHEMA_FILENAME
    )

    if not fixture_paths:
        print(f"No fixtures found in {_FIXTURES_DIR}")
        return 1

    results: list[EvalResult] = []
    for path in fixture_paths:
        result = score_fixture(path)
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    pass_rate = passed / len(results)

    _print_report(results, pass_rate, threshold)

    return 0 if pass_rate >= threshold else 1


if __name__ == "__main__":
    sys.exit(main())
