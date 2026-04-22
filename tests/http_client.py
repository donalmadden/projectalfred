"""Lightweight synchronous test client backed by httpx ASGI transport."""
from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from typing import Any

import httpx
from fastapi import FastAPI


class SyncASGIClient(AbstractContextManager["SyncASGIClient"]):
    """Minimal sync facade for exercising the FastAPI app in tests."""

    def __init__(self, app: FastAPI, *, base_url: str = "http://testserver") -> None:
        self._app = app
        self._base_url = base_url

    def __enter__(self) -> SyncASGIClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async def _send() -> httpx.Response:
            transport = httpx.ASGITransport(app=self._app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url=self._base_url,
            ) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(_send())

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)
