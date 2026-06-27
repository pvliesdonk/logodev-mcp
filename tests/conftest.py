"""Shared test fixtures for Logo.dev MCP."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from logodev_mcp.server import make_server


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip all ``LOGODEV_MCP_*`` env vars before each test.

    Plan detection defaults off so server-building tests never probe the real
    logo.dev API on startup; tests that exercise plan gating opt back in with
    ``LOGODEV_MCP_DETECT_PLAN=true`` and mock the HTTP calls.
    """
    for key in list(os.environ):
        if key.startswith("LOGODEV_MCP_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LOGODEV_MCP_DETECT_PLAN", "false")


@pytest.fixture
async def client() -> AsyncIterator[Client[Any]]:
    """Return an in-memory FastMCP client connected to a fresh server."""
    server = make_server()
    async with Client(server) as c:
        yield c
