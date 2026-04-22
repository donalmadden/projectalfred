"""Integration coverage for Alfred shutdown draining."""
from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

from alfred.api import alfred_lifespan, app, set_config
from alfred.schemas.config import AlfredConfig
from alfred.tools import persistence


def _json_lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if line.strip()
    ]


def test_shutdown_expires_pending_approvals_and_logs_warning(
    tmp_path: Path,
    monkeypatch,
) -> None:
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("SHUTDOWN_DRAIN_TIMEOUT_S", "0")

    cfg = AlfredConfig()
    cfg.llm.provider = "fake"
    cfg.llm.model = "m"
    cfg.database.path = str(tmp_path / "alfred.db")
    cfg.github.org = ""
    cfg.rag.index_path = ""
    cfg.hitl.timeout_seconds = 3600
    set_config(cfg)

    approval_id = "approval-shutdown"

    async def run() -> None:
        async with alfred_lifespan(app):
            persistence.create_pending_approval(
                cfg.database.path,
                approval_id=approval_id,
                handover_id="ALFRED_HANDOVER_6",
                action_type="story_creation",
                item_id="PVTI_shutdown",
                timeout_seconds=3600,
            )
            assert len(persistence.get_pending_approvals(cfg.database.path)) == 1

    try:
        asyncio.run(run())
    finally:
        set_config(None)  # type: ignore[arg-type]

    approval = persistence.get_approval(cfg.database.path, approval_id)
    assert approval is not None
    assert approval["decision"] == "expired"
    assert approval["decided_at"] is not None
    assert persistence.get_pending_approvals(cfg.database.path) == []

    warning_log = next(
        payload
        for payload in _json_lines(stream)
        if payload["level"] == "WARNING"
    )
    assert warning_log["message"] == "expired pending approval during shutdown"
    assert warning_log["approval_id"] == approval_id
    assert warning_log["request_id"] == "-"
