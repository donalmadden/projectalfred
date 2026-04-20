"""Per-module coverage gate script.

Reads a pytest-cov JSON report and a thresholds config, then asserts that:
  1. The global coverage total meets the global threshold.
  2. Each named module meets its per-module threshold.

Exits 0 if all gates pass; exits 1 with a summary of violations otherwise.

Usage:
    python scripts/check_coverage.py
    python scripts/check_coverage.py --report coverage.json --config scripts/coverage_thresholds.json

Note: pytest-cov's native fail_under is global only; this script enforces
per-module gates that the native config cannot express.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_DEFAULT_REPORT = "coverage.json"
_DEFAULT_CONFIG = Path(__file__).parent / "coverage_thresholds.json"

_COL_MODULE = 42
_COL_ACTUAL = 7
_COL_THRESHOLD = 9
_SEP = "-" * (_COL_MODULE + _COL_ACTUAL + _COL_THRESHOLD + 13)


def _load_report(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"ERROR: coverage report not found: {path}")
        print("Run: pytest --cov=alfred --cov-report=json")
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


def _load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"ERROR: thresholds config not found: {path}")
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


def _percent(report: dict, module_key: str) -> float | None:
    file_data = report.get("files", {}).get(module_key)
    if file_data is None:
        return None
    return file_data["summary"]["percent_covered"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Per-module coverage gate.")
    parser.add_argument(
        "--report",
        default=_DEFAULT_REPORT,
        help=f"Path to coverage JSON report (default: {_DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--config",
        default=str(_DEFAULT_CONFIG),
        help=f"Path to thresholds config JSON (default: {_DEFAULT_CONFIG})",
    )
    args = parser.parse_args()

    report = _load_report(args.report)
    config = _load_config(args.config)

    global_threshold: float = float(config.get("global", 0))
    module_thresholds: dict[str, float] = {
        k: float(v) for k, v in config.get("modules", {}).items()
    }

    violations: list[str] = []

    # --- Global gate ---
    global_actual = report.get("totals", {}).get("percent_covered", 0.0)
    print(f"\n{'Module':<{_COL_MODULE}} | {'Actual':>{_COL_ACTUAL}} | {'Threshold':>{_COL_THRESHOLD}} | Status")
    print(_SEP)

    global_status = "PASS" if global_actual >= global_threshold else "FAIL"
    print(
        f"{'[GLOBAL]':<{_COL_MODULE}} | {global_actual:>{_COL_ACTUAL}.1f}% | "
        f"{global_threshold:>{_COL_THRESHOLD}.0f}% | {global_status}"
    )
    if global_actual < global_threshold:
        violations.append(
            f"[GLOBAL] {global_actual:.1f}% < {global_threshold:.0f}%"
        )

    # --- Per-module gates ---
    for module_key, threshold in sorted(module_thresholds.items()):
        actual = _percent(report, module_key)
        if actual is None:
            status = "MISSING"
            violations.append(f"{module_key}: not found in report")
            print(
                f"{module_key:<{_COL_MODULE}} | {'N/A':>{_COL_ACTUAL}} | "
                f"{threshold:>{_COL_THRESHOLD}.0f}% | {status}"
            )
            continue
        status = "PASS" if actual >= threshold else "FAIL"
        print(
            f"{module_key:<{_COL_MODULE}} | {actual:>{_COL_ACTUAL}.1f}% | "
            f"{threshold:>{_COL_THRESHOLD}.0f}% | {status}"
        )
        if actual < threshold:
            violations.append(f"{module_key}: {actual:.1f}% < {threshold:.0f}%")

    print(_SEP)

    if violations:
        print(f"\nFAIL — {len(violations)} threshold(s) violated:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print(f"\nOK — all {1 + len(module_thresholds)} gate(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
