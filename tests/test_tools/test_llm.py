"""Tests for the provider-agnostic LLM adapter."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from alfred.tools import llm


class _Echo(BaseModel):
    value: str
    count: int


@pytest.fixture(autouse=True)
def _reset_providers():
    """Snapshot the provider dispatch table so tests can inject fakes safely."""
    original = dict(llm._PROVIDERS)
    yield
    llm._PROVIDERS.clear()
    llm._PROVIDERS.update(original)


def _install_fake(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[Any],
    tokens: int = 42,
) -> dict[str, int]:
    """Install a fake provider that yields successive `responses`. Returns a call counter."""
    state = {"calls": 0}

    def fake(prompt: str, output_schema, model: str) -> tuple[dict[str, Any], int]:
        idx = state["calls"]
        state["calls"] += 1
        resp = responses[idx]
        if isinstance(resp, Exception):
            raise resp
        return resp, tokens

    monkeypatch.setitem(llm._PROVIDERS, "fake", fake)
    return state


def test_complete_returns_validated_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake(monkeypatch, [{"value": "hello", "count": 3}])
    result = llm.complete("prompt", _Echo, provider="fake", model="m")
    assert isinstance(result, _Echo)
    assert result.value == "hello"
    assert result.count == 3


def test_complete_unknown_provider_raises() -> None:
    with pytest.raises(llm.LLMError, match="Unknown provider"):
        llm.complete("prompt", _Echo, provider="nope", model="m")


def test_complete_retries_on_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _install_fake(
        monkeypatch,
        [
            {"value": "x"},  # missing 'count' — ValidationError
            {"value": "x", "count": 1},  # valid
        ],
    )
    result = llm.complete("p", _Echo, provider="fake", model="m", max_retries=2)
    assert result.count == 1
    assert state["calls"] == 2


def test_complete_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _install_fake(
        monkeypatch,
        [{"value": "x"}, {"value": "y"}, {"value": "z"}],
    )
    with pytest.raises(llm.LLMError, match="Failed to produce schema-valid output"):
        llm.complete("p", _Echo, provider="fake", model="m", max_retries=2)
    assert state["calls"] == 3


def test_complete_logs_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake(monkeypatch, [{"value": "ok", "count": 1}])
    db = str(tmp_path / "alfred.db")
    llm.complete("p", _Echo, provider="fake", model="m", db_path=db)

    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT agent_name, tokens_used, error, output_hash FROM agent_invocations"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["agent_name"] == "llm:fake:m"
    assert rows[0]["tokens_used"] == 42
    assert rows[0]["error"] is None
    assert rows[0]["output_hash"] is not None


def test_complete_logs_retry_attempts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake(
        monkeypatch,
        [{"value": "x"}, {"value": "y", "count": 2}],
    )
    db = str(tmp_path / "alfred.db")
    llm.complete(
        "p", _Echo, provider="fake", model="m", max_retries=2, db_path=db
    )
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT error FROM agent_invocations ORDER BY id"
        ).fetchall()
    assert len(rows) == 2
    assert rows[0]["error"] == "validation:attempt=0"
    assert rows[1]["error"] is None
