"""Eval scorer: loads, validates, and scores a single fixture file.

Each fixture_type maps to a dedicated scorer function. All LLM calls use a
mock provider installed from mock_llm_response — no API keys required.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_SCHEMA_PATH = Path(__file__).parent / "fixtures" / "schema.json"
_MOCK_PROVIDER_NAME = "mock_eval"


@dataclass
class EvalResult:
    fixture_id: str
    passed: bool
    score: float
    diff: str


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def _validate_against_schema(data: dict) -> None:
    import jsonschema

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# Mock LLM lifecycle
# ---------------------------------------------------------------------------


def _install_mock_llm(response: dict) -> None:
    from alfred.tools import llm

    def mock_provider(
        prompt: str, output_schema: Any, model: str
    ) -> tuple[dict[str, Any], int]:
        return response, 0

    llm._PROVIDERS[_MOCK_PROVIDER_NAME] = mock_provider


def _remove_mock_llm() -> None:
    from alfred.tools import llm

    llm._PROVIDERS.pop(_MOCK_PROVIDER_NAME, None)


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------


def _eval_config():
    from alfred.schemas.config import AlfredConfig

    cfg = AlfredConfig()
    cfg.llm.provider = _MOCK_PROVIDER_NAME
    cfg.llm.model = "eval"
    cfg.database.path = ""
    cfg.github.org = ""
    cfg.rag.index_path = ""
    return cfg


# ---------------------------------------------------------------------------
# Per-type scorers
# ---------------------------------------------------------------------------


def _score_orchestration(fixture: dict) -> EvalResult:
    from alfred.orchestrator import orchestrate
    from alfred.schemas.handover import HandoverDocument

    cfg = _eval_config()
    handover = HandoverDocument.model_validate(fixture["input"]["handover"])
    expected = fixture["expected"]
    checks: dict[str, Any] = {}

    try:
        result = orchestrate(handover, cfg)
        checks["returns_handover_document"] = isinstance(result, HandoverDocument)
        checks["all_tasks_have_results"] = all(t.result is not None for t in result.tasks)
        checks["no_exception_raised"] = True
    except Exception as exc:
        checks["returns_handover_document"] = False
        checks["all_tasks_have_results"] = False
        checks["no_exception_raised"] = False
        checks["_exception"] = repr(exc)

    diffs = [
        f"{k}: expected={v!r}, got={checks.get(k)!r}"
        for k, v in expected.items()
        if checks.get(k) != v
    ]
    if "_exception" in checks and not expected.get("no_exception_raised", True):
        diffs.append(f"exception: {checks['_exception']}")

    passed_count = sum(1 for k, v in expected.items() if checks.get(k) == v)
    score = passed_count / len(expected) if expected else 1.0
    return EvalResult(
        fixture_id=fixture["id"],
        passed=score == 1.0,
        score=score,
        diff="; ".join(diffs),
    )


def _score_checkpoint_rejection(fixture: dict) -> EvalResult:
    from alfred.orchestrator import CheckpointHalt, orchestrate
    from alfred.schemas.handover import HandoverDocument

    cfg = _eval_config()
    handover = HandoverDocument.model_validate(fixture["input"]["handover"])
    expected_exc = fixture["expected"].get("raises_exception")
    got_exc: Optional[str] = None

    try:
        orchestrate(handover, cfg)
    except CheckpointHalt:
        got_exc = "CheckpointHalt"
    except Exception as exc:
        got_exc = type(exc).__name__

    passed = got_exc == expected_exc
    diff = (
        ""
        if passed
        else f"raises_exception: expected={expected_exc!r}, got={got_exc!r}"
    )
    return EvalResult(
        fixture_id=fixture["id"],
        passed=passed,
        score=1.0 if passed else 0.0,
        diff=diff,
    )


def _score_planner_output(fixture: dict) -> EvalResult:
    from alfred.agents.planner import run_planner
    from alfred.schemas.agent import PlannerInput

    planner_input = PlannerInput.model_validate(fixture["input"]["planner_input"])
    expected = fixture["expected"]
    checks: dict[str, Any] = {}

    try:
        output = run_planner(
            planner_input, provider=_MOCK_PROVIDER_NAME, model="eval"
        )
        if "draft_handover_markdown_non_empty" in expected:
            checks["draft_handover_markdown_non_empty"] = (
                len(output.draft_handover_markdown) > 0
            )
        if "task_decomposition_is_list" in expected:
            checks["task_decomposition_is_list"] = isinstance(
                output.task_decomposition, list
            )
        if "open_questions_is_list" in expected:
            checks["open_questions_is_list"] = isinstance(output.open_questions, list)
        if "draft_handover_markdown_contains" in expected:
            checks["draft_handover_markdown_contains"] = (
                expected["draft_handover_markdown_contains"]
                in output.draft_handover_markdown
            )
    except Exception as exc:
        for k in expected:
            checks[k] = False
        checks["_exception"] = repr(exc)

    tolerance = fixture.get("tolerance", {})
    # For "substring" tolerance keys the scorer stores a bool check; compare to True.
    def _passes(k: str, v: Any) -> bool:
        if tolerance.get(k) == "substring":
            return checks.get(k) is True
        return checks.get(k) == v

    diffs = [
        f"{k}: expected={v!r}, got={checks.get(k)!r}"
        for k, v in expected.items()
        if not _passes(k, v)
    ]
    if "_exception" in checks:
        diffs.append(f"exception: {checks['_exception']}")

    passed_count = sum(1 for k, v in expected.items() if _passes(k, v))
    score = passed_count / len(expected) if expected else 1.0
    return EvalResult(
        fixture_id=fixture["id"],
        passed=score == 1.0,
        score=score,
        diff="; ".join(diffs),
    )


_SCORERS = {
    "orchestration": _score_orchestration,
    "checkpoint_rejection": _score_checkpoint_rejection,
    "planner_output": _score_planner_output,
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def score_fixture(fixture_path: Path) -> EvalResult:
    """Load, schema-validate, and score a single fixture file."""
    raw: dict = json.loads(fixture_path.read_text(encoding="utf-8"))

    try:
        _validate_against_schema(raw)
    except Exception as exc:
        return EvalResult(
            fixture_id=raw.get("id", str(fixture_path)),
            passed=False,
            score=0.0,
            diff=f"schema validation failed: {exc}",
        )

    fixture_type = raw.get("fixture_type", "")
    scorer = _SCORERS.get(fixture_type)
    if scorer is None:
        return EvalResult(
            fixture_id=raw.get("id", str(fixture_path)),
            passed=False,
            score=0.0,
            diff=f"unknown fixture_type: {fixture_type!r}",
        )

    mock_response = raw.get("mock_llm_response") or {}
    _install_mock_llm(mock_response)
    try:
        return scorer(raw)
    finally:
        _remove_mock_llm()
