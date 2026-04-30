"""Tests for ``scripts/demo_preflight.py``."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import demo_preflight as dp  # noqa: E402


def _good_env() -> dict[str, str]:
    return {
        "DEMO_PROJECT_ROOT": "/tmp/cop_demo",
        "ALFRED_DEMO_GITHUB_ORG": "acme",
        "ALFRED_DEMO_GITHUB_PROJECT_NUMBER": "17",
        "ANTHROPIC_API_KEY": "secret-a",
        "GITHUB_TOKEN": "secret-b",
    }


def _good_fetch(url: str, timeout: float) -> tuple[int, object]:
    assert timeout == 2.0
    if url.endswith("/healthz"):
        return 200, {"status": "ok"}
    if url.endswith("/readyz"):
        return 200, {"status": "ready"}
    raise AssertionError(f"Unexpected URL: {url}")


def test_collect_env_checks_marks_required_and_optional_fields() -> None:
    checks = dp.collect_env_checks(_good_env())

    by_name = {check.spec.name: check for check in checks}
    assert by_name["DEMO_PROJECT_ROOT"].valid is True
    assert "present: /tmp/cop_demo" in by_name["DEMO_PROJECT_ROOT"].detail
    assert by_name["ANTHROPIC_API_KEY"].valid is True
    assert "secret-a" not in by_name["ANTHROPIC_API_KEY"].detail
    assert by_name["OPENAI_API_KEY"].valid is True
    assert by_name["OPENAI_API_KEY"].present is False


def test_collect_env_checks_rejects_non_numeric_project_number() -> None:
    env = _good_env()
    env["ALFRED_DEMO_GITHUB_PROJECT_NUMBER"] = "abc"

    checks = dp.collect_env_checks(env)

    project_number = next(
        check for check in checks if check.spec.name == "ALFRED_DEMO_GITHUB_PROJECT_NUMBER"
    )
    assert project_number.valid is False
    assert "not numeric" in project_number.detail


def test_run_preflight_returns_true_when_env_and_probes_pass() -> None:
    ok, report = dp.run_preflight(
        environ=_good_env(),
        fetch_json=_good_fetch,
    )

    assert ok is True
    assert "[FROZEN INPUTS]" in report
    assert "Customer Onboarding Portal" in report
    assert "PASS DEMO_PROJECT_ROOT" in report
    assert "PASS GET /healthz" in report
    assert "PASS GET /readyz" in report
    assert "0 items" in report


def test_run_preflight_returns_false_when_required_env_missing() -> None:
    env = _good_env()
    del env["GITHUB_TOKEN"]

    ok, report = dp.run_preflight(
        environ=env,
        fetch_json=_good_fetch,
    )

    assert ok is False
    assert "FAIL GITHUB_TOKEN" in report


def test_run_preflight_returns_false_when_probe_fails() -> None:
    def failing_fetch(url: str, timeout: float) -> tuple[int, object]:
        if url.endswith("/healthz"):
            return 200, {"status": "ok"}
        if url.endswith("/readyz"):
            return 503, {"status": "unavailable", "reason": "db"}
        raise AssertionError(f"Unexpected URL: {url}")

    ok, report = dp.run_preflight(
        environ=_good_env(),
        fetch_json=failing_fetch,
    )

    assert ok is False
    assert "FAIL GET /readyz" in report
    assert '"status": "unavailable"' in report


def test_main_prints_report_and_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for name, value in _good_env().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(dp, "_fetch_json", _good_fetch)

    rc = dp.main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert "[PROBES]" in out
    assert "PASS GET /healthz" in out
