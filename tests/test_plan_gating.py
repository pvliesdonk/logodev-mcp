"""End-to-end plan-detection gating: the lifespan probes entitlement and hides
the tools the configured logo.dev plan does not allow."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx
from fastmcp import Client, FastMCP
from pytest import MonkeyPatch

from logodev_mcp.domain import API_BASE, ENTITLEMENT_PROBE_DOMAIN
from logodev_mcp.server import make_server

if TYPE_CHECKING:
    from pathlib import Path

_DESCRIBE_URL = f"{API_BASE}/describe/{ENTITLEMENT_PROBE_DOMAIN}"
_BRAND_URL = f"{API_BASE}/brand/{ENTITLEMENT_PROBE_DOMAIN}"


async def _tool_names(mcp: FastMCP) -> set[str]:
    async with Client(mcp) as client:
        return {t.name for t in await client.list_tools()}


def _enable_detection(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOGODEV_MCP_PUBLISHABLE_KEY", "pk_x")
    monkeypatch.setenv("LOGODEV_MCP_SECRET_KEY", "sk_y")
    monkeypatch.setenv("LOGODEV_MCP_DETECT_PLAN", "true")
    monkeypatch.setenv("LOGODEV_MCP_STATE_DIR", str(tmp_path))


@pytest.mark.asyncio
async def test_unentitled_tools_hidden(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _enable_detection(monkeypatch, tmp_path)
    with respx.mock:
        respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(401, json={}))
        respx.get(_BRAND_URL).mock(return_value=httpx.Response(403, json={}))
        names = await _tool_names(make_server())
    assert "describe_company" not in names
    assert "get_brand" not in names
    # search_brands and get_logo are not plan-gated.
    assert {"search_brands", "get_logo"} <= names


@pytest.mark.asyncio
async def test_entitled_tools_visible(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    _enable_detection(monkeypatch, tmp_path)
    with respx.mock:
        respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(200, json={}))
        respx.get(_BRAND_URL).mock(return_value=httpx.Response(200, json={}))
        names = await _tool_names(make_server())
    assert {"describe_company", "get_brand", "search_brands", "get_logo"} <= names


@pytest.mark.asyncio
async def test_partial_entitlement_hides_only_brand(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _enable_detection(monkeypatch, tmp_path)
    with respx.mock:
        respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(200, json={}))
        respx.get(_BRAND_URL).mock(return_value=httpx.Response(403, json={}))
        names = await _tool_names(make_server())
    assert "describe_company" in names
    assert "get_brand" not in names


@pytest.mark.asyncio
async def test_ambiguous_probe_keeps_tools_enabled(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    # A 5xx (or any non-200/401/403) is ambiguous — fail open, keep the tools.
    _enable_detection(monkeypatch, tmp_path)
    with respx.mock:
        respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(500, json={}))
        respx.get(_BRAND_URL).mock(return_value=httpx.Response(500, json={}))
        names = await _tool_names(make_server())
    assert {"describe_company", "get_brand"} <= names


@pytest.mark.asyncio
async def test_probe_failure_fails_open(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    # If probing itself raises, startup must not break and tools stay enabled.
    _enable_detection(monkeypatch, tmp_path)

    async def _boom(_self: object) -> dict[str, bool]:
        raise RuntimeError("probe exploded")

    monkeypatch.setattr(
        "logodev_mcp.domain.Service.probe_entitlements", _boom, raising=True
    )
    names = await _tool_names(make_server())
    assert {"describe_company", "get_brand"} <= names


@pytest.mark.asyncio
async def test_disable_failure_fails_open(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    # If mcp.disable() itself raises (e.g. a tool-name/registration desync),
    # startup must still complete and the tools stay enabled.
    _enable_detection(monkeypatch, tmp_path)

    def _boom(_self: object, **_kwargs: object) -> None:
        raise RuntimeError("disable exploded")

    monkeypatch.setattr(FastMCP, "disable", _boom, raising=True)
    with respx.mock:
        respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(401, json={}))
        respx.get(_BRAND_URL).mock(return_value=httpx.Response(403, json={}))
        names = await _tool_names(make_server())
    assert {"describe_company", "get_brand"} <= names


@pytest.mark.asyncio
async def test_detection_disabled_skips_probe(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _enable_detection(monkeypatch, tmp_path)
    monkeypatch.setenv("LOGODEV_MCP_DETECT_PLAN", "false")
    with respx.mock:
        route = respx.get(url__startswith=API_BASE).mock(
            return_value=httpx.Response(401, json={})
        )
        names = await _tool_names(make_server())
    assert {"describe_company", "get_brand"} <= names
    assert route.called is False
