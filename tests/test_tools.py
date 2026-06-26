from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client, FastMCP
from pytest import MonkeyPatch

from logodev_mcp.domain import API_BASE, IMG_BASE
from logodev_mcp.server import make_server


async def _tool_names(mcp: FastMCP) -> set[str]:
    async with Client(mcp) as client:
        return {t.name for t in await client.list_tools()}


@pytest.mark.asyncio
async def test_only_logo_tool_with_publishable_only(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LOGODEV_MCP_PUBLISHABLE_KEY", "pk_x")
    monkeypatch.delenv("LOGODEV_MCP_SECRET_KEY", raising=False)
    names = await _tool_names(make_server())
    assert "get_logo" in names
    assert "search_brands" not in names
    assert "describe_company" not in names
    assert "get_brand" not in names


@pytest.mark.asyncio
async def test_only_rest_tools_with_secret_only(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("LOGODEV_MCP_SECRET_KEY", "sk_y")
    names = await _tool_names(make_server())
    assert "get_logo" not in names
    assert {"search_brands", "describe_company", "get_brand"} <= names


@pytest.mark.asyncio
async def test_no_api_tools_without_keys(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("LOGODEV_MCP_SECRET_KEY", raising=False)
    names = await _tool_names(make_server())
    assert {"get_logo", "search_brands", "describe_company", "get_brand"}.isdisjoint(
        names
    )


@pytest.mark.asyncio
async def test_get_logo_tool_returns_url_and_image(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LOGODEV_MCP_PUBLISHABLE_KEY", "pk_x")
    monkeypatch.delenv("LOGODEV_MCP_SECRET_KEY", raising=False)
    mcp = make_server()
    with respx.mock:
        respx.get(f"{IMG_BASE}/nike.com").mock(
            return_value=httpx.Response(200, content=b"\x89PNG")
        )
        async with Client(mcp) as client:
            result = await client.call_tool("get_logo", {"identifier": "nike.com"})
    blocks = result.content
    assert any(
        getattr(b, "type", None) == "text" and "img.logo.dev" in b.text for b in blocks
    )
    assert any(getattr(b, "type", None) == "image" for b in blocks)


@pytest.mark.asyncio
async def test_get_brand_tool_maps_error_to_message(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("LOGODEV_MCP_SECRET_KEY", "sk_y")
    mcp = make_server()
    with respx.mock:
        respx.get(f"{API_BASE}/brand/nike.com").mock(return_value=httpx.Response(401))
        async with Client(mcp) as client:
            result = await client.call_tool("get_brand", {"domain": "nike.com"})
    text = " ".join(
        b.text for b in result.content if getattr(b, "type", None) == "text"
    )
    assert "plan" in text.lower() or "secret" in text.lower()


@pytest.mark.asyncio
async def test_get_logo_tool_url_only_returns_only_url(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGODEV_MCP_PUBLISHABLE_KEY", "pk_x")
    monkeypatch.delenv("LOGODEV_MCP_SECRET_KEY", raising=False)
    async with Client(make_server()) as client:
        result = await client.call_tool(
            "get_logo", {"identifier": "nike.com", "url_only": True}
        )
    blocks = result.content
    assert all(getattr(b, "type", None) == "text" for b in blocks)
    assert not any(getattr(b, "type", None) == "image" for b in blocks)
    assert any("img.logo.dev" in b.text for b in blocks)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "path", "args"),
    [
        ("search_brands", "/search", {"query": "nike"}),
        ("describe_company", "/describe/nike.com", {"domain": "nike.com"}),
    ],
)
async def test_rest_tools_map_error_to_message(
    monkeypatch: MonkeyPatch, tool: str, path: str, args: dict[str, str]
) -> None:
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("LOGODEV_MCP_SECRET_KEY", "sk_y")
    with respx.mock:
        respx.get(f"{API_BASE}{path}").mock(return_value=httpx.Response(401))
        async with Client(make_server()) as client:
            result = await client.call_tool(tool, args)
    text = " ".join(
        b.text for b in result.content if getattr(b, "type", None) == "text"
    )
    assert "plan" in text.lower() or "secret" in text.lower()
