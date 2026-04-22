"""Structured JSON logging utilities for Alfred."""
from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import os
import sys
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the current request id, or ``-`` outside a request context."""
    return _REQUEST_ID.get()


@contextlib.contextmanager
def request_id_context(request_id: str) -> Iterator[None]:
    """Temporarily bind a request id for log emission in tests or helper flows."""
    token = _REQUEST_ID.set(request_id)
    try:
        yield
    finally:
        _REQUEST_ID.reset(token)


class JsonFormatter(logging.Formatter):
    """Render Alfred logs as stable JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", get_request_id()),
        }

        for key in (
            "method",
            "path",
            "status_code",
            "approval_id",
            "handover_id",
            "action_type",
            "expired_count",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, sort_keys=True)


def _resolve_level(level: str) -> int:
    resolved_name = (level or os.environ.get("LOG_LEVEL", "INFO")).strip().upper() or "INFO"
    resolved_level = getattr(logging, resolved_name, logging.INFO)
    if not isinstance(resolved_level, int):
        return logging.INFO
    return resolved_level


def configure_logging(level: str) -> None:
    """Install Alfred's JSON logger on the root logger."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root.addHandler(handler)
    root.setLevel(_resolve_level(level))

    # Route uvicorn logs through the same JSON formatter.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured by ``configure_logging``."""
    return logging.getLogger(name)


class RequestIdMiddleware:
    """ASGI middleware that binds a request id and emits one request log line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = get_logger("alfred.request")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get("x-request-id") or str(uuid.uuid4())
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "")
        status_code = 500
        token = _REQUEST_ID.set(request_id)

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                mutable_headers = MutableHeaders(scope=message)
                mutable_headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            self.logger.exception(
                "request failed",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                },
            )
            raise
        else:
            self.logger.info(
                "request completed",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                },
            )
        finally:
            _REQUEST_ID.reset(token)
