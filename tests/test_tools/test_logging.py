"""Tests for ``alfred.tools.logging``."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys

from alfred.api import alfred_lifespan, app
from alfred.tools import logging as alfred_logging
from tests.http_client import SyncASGIClient


def _json_lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if line.strip()
    ]


def test_configure_logging_emits_expected_json_shape(monkeypatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stream)

    alfred_logging.configure_logging("INFO")
    with alfred_logging.request_id_context("req-123"):
        alfred_logging.get_logger("alfred.test").info("hello world")

    payload = _json_lines(stream)[-1]
    assert payload["timestamp"]
    assert payload["level"] == "INFO"
    assert payload["logger"] == "alfred.test"
    assert payload["message"] == "hello world"
    assert payload["request_id"] == "req-123"


def test_configure_logging_respects_log_level(monkeypatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    alfred_logging.configure_logging(os.environ.get("LOG_LEVEL", "INFO"))
    alfred_logging.get_logger("alfred.test").debug("debug enabled")

    payload = _json_lines(stream)[-1]
    assert logging.getLogger().level == logging.DEBUG
    assert payload["level"] == "DEBUG"
    assert payload["message"] == "debug enabled"


def test_request_id_middleware_propagates_header_into_logs(monkeypatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stream)
    alfred_logging.configure_logging("INFO")

    response = SyncASGIClient(app).get("/healthz", headers={"X-Request-ID": "test-123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-123"

    request_log = next(
        payload
        for payload in _json_lines(stream)
        if payload["message"] == "request completed"
    )
    assert request_log["request_id"] == "test-123"
    assert request_log["path"] == "/healthz"
    assert request_log["status_code"] == 200


def test_lifespan_configures_logging_from_env(monkeypatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    async def run() -> None:
        async with alfred_lifespan(app):
            pass

    asyncio.run(run())

    payload = _json_lines(stream)[0]
    assert logging.getLogger().level == logging.DEBUG
    assert payload["message"] == "application startup"
