"""Phase 5 demo preflight helper.

Prints the frozen inputs, checks whether the required demo environment
variables are present, probes Alfred's local ``/healthz`` and ``/readyz``
endpoints, and reminds the operator to confirm the GitHub Project board is
blank in the browser.

This script never prints secret values.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
SCENARIO_NAME = "Customer Onboarding Portal"
CHARTER_SOURCE = "docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md"
WORKSPACE_SHAPE = (
    "<demo-project-root>/README.md",
    "<demo-project-root>/docs/CHARTER.md",
    "<demo-project-root>/docs/handovers/",
)


@dataclass(frozen=True)
class EnvSpec:
    name: str
    required: bool
    description: str
    secret: bool = False
    numeric: bool = False


@dataclass(frozen=True)
class EnvCheck:
    spec: EnvSpec
    present: bool
    valid: bool
    detail: str


@dataclass(frozen=True)
class ProbeCheck:
    name: str
    ok: bool
    detail: str


FetchJson = Callable[[str, float], tuple[int, object]]


ENV_SPECS: tuple[EnvSpec, ...] = (
    EnvSpec(
        name="DEMO_PROJECT_ROOT",
        required=True,
        description="external demo workspace root",
    ),
    EnvSpec(
        name="ALFRED_DEMO_GITHUB_ORG",
        required=True,
        description="target GitHub Project owner",
    ),
    EnvSpec(
        name="ALFRED_DEMO_GITHUB_PROJECT_NUMBER",
        required=True,
        description="target GitHub Project number",
        numeric=True,
    ),
    EnvSpec(
        name="ANTHROPIC_API_KEY",
        required=True,
        description="kickoff harness compile + story generation",
        secret=True,
    ),
    EnvSpec(
        name="GITHUB_TOKEN",
        required=True,
        description="Phase 4 GitHub Project write",
        secret=True,
    ),
    EnvSpec(
        name="OPENAI_API_KEY",
        required=False,
        description="optional unless you intentionally route the runtime through the default OpenAI config",
        secret=True,
    ),
)


def _normalise_base_url(value: str) -> str:
    return value.rstrip("/")


def _fetch_json(url: str, timeout: float) -> tuple[int, object]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
        return response.getcode(), json.loads(payload)


def _check_env(environ: Mapping[str, str], spec: EnvSpec) -> EnvCheck:
    value = environ.get(spec.name, "").strip()
    if not value:
        detail = "missing"
        if spec.required:
            detail += f" ({spec.description})"
        return EnvCheck(spec=spec, present=False, valid=not spec.required, detail=detail)

    if spec.numeric and not value.isdigit():
        return EnvCheck(
            spec=spec,
            present=True,
            valid=False,
            detail=f"present but not numeric: {value!r}",
        )

    if spec.secret:
        detail = f"present ({spec.description})"
    else:
        detail = f"present: {value} ({spec.description})"
    return EnvCheck(spec=spec, present=True, valid=True, detail=detail)


def collect_env_checks(environ: Mapping[str, str]) -> list[EnvCheck]:
    return [_check_env(environ, spec) for spec in ENV_SPECS]


def collect_probe_checks(
    base_url: str,
    *,
    timeout: float,
    fetch_json: Optional[FetchJson] = None,
) -> list[ProbeCheck]:
    active_fetch_json = _fetch_json if fetch_json is None else fetch_json
    checks: list[ProbeCheck] = []
    for path, expected_status in (("/healthz", "ok"), ("/readyz", "ready")):
        url = f"{_normalise_base_url(base_url)}{path}"
        try:
            code, payload = active_fetch_json(url, timeout)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            checks.append(
                ProbeCheck(
                    name=path,
                    ok=False,
                    detail=f"HTTP {exc.code}: {body}",
                )
            )
            continue
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            checks.append(ProbeCheck(name=path, ok=False, detail=str(exc)))
            continue

        if not isinstance(payload, dict):
            checks.append(
                ProbeCheck(
                    name=path,
                    ok=False,
                    detail=f"unexpected payload type {type(payload).__name__}",
                )
            )
            continue

        status = payload.get("status")
        ok = code == 200 and status == expected_status
        checks.append(
            ProbeCheck(
                name=path,
                ok=ok,
                detail=f"HTTP {code} {json.dumps(payload, sort_keys=True)}",
            )
        )
    return checks


def render_report(
    env_checks: list[EnvCheck],
    probe_checks: list[ProbeCheck],
    *,
    base_url: str,
) -> str:
    lines: list[str] = []
    lines.append("[FROZEN INPUTS]")
    lines.append(f"- scenario: {SCENARIO_NAME}")
    lines.append(f"- charter source: {CHARTER_SOURCE}")
    lines.append("- required workspace shape:")
    for entry in WORKSPACE_SHAPE:
        lines.append(f"  - {entry}")
    lines.append("")
    lines.append("[ENVIRONMENT]")
    for check in env_checks:
        label = "PASS" if check.valid else "FAIL"
        required = "required" if check.spec.required else "optional"
        lines.append(f"{label} {check.spec.name} ({required}) - {check.detail}")
    lines.append("")
    lines.append(f"[PROBES] base_url={_normalise_base_url(base_url)}")
    for check in probe_checks:
        label = "PASS" if check.ok else "FAIL"
        lines.append(f"{label} GET {check.name} - {check.detail}")
    lines.append("")
    lines.append("[REMINDERS]")
    lines.append("- Confirm the target GitHub Project V2 board is the intended one and currently shows 0 items.")
    lines.append("- Record the exact board URL/name before rehearsal so both clean runs target the same board.")
    return "\n".join(lines)


def run_preflight(
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 2.0,
    environ: Optional[Mapping[str, str]] = None,
    fetch_json: Optional[FetchJson] = None,
) -> tuple[bool, str]:
    active_environ = os.environ if environ is None else environ
    env_checks = collect_env_checks(active_environ)
    probe_checks = collect_probe_checks(base_url, timeout=timeout, fetch_json=fetch_json)
    ok = all(check.valid for check in env_checks) and all(check.ok for check in probe_checks)
    report = render_report(env_checks, probe_checks, base_url=base_url)
    return ok, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Alfred Phase 5 kickoff-demo preflight checks.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL for Alfred's API probes. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="HTTP timeout in seconds for probe requests. Default: 2.0",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    ok, report = run_preflight(base_url=args.base_url, timeout=args.timeout)
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
