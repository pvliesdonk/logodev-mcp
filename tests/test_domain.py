from __future__ import annotations

import httpx
import pytest

from logodev_mcp.config import ProjectConfig
from logodev_mcp.domain import API_BASE, IMG_BASE, LogoDevError, Service


@pytest.mark.asyncio
async def test_start_with_both_keys_builds_both_clients() -> None:
    config = ProjectConfig(publishable_key="pk_x", secret_key="sk_y")
    service = Service(config)
    await service.start()
    try:
        assert service.has_publishable is True
        assert service.has_secret is True
        assert isinstance(service._api, httpx.AsyncClient)
        assert isinstance(service._img, httpx.AsyncClient)
        assert str(service._api.base_url).rstrip("/") == API_BASE
        assert str(service._img.base_url).rstrip("/") == IMG_BASE
        assert service._api.headers["Authorization"] == "Bearer sk_y"
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_start_with_no_keys_builds_no_clients() -> None:
    service = Service(ProjectConfig())
    await service.start()
    try:
        assert service.has_publishable is False
        assert service.has_secret is False
        assert service._api is None
        assert service._img is None
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_stop_is_idempotent() -> None:
    service = Service(ProjectConfig(secret_key="sk_y"))
    await service.start()
    await service.stop()
    await service.stop()  # second close must not raise
    assert service._api is None


def test_logodev_error_carries_message_and_status() -> None:
    err = LogoDevError("nope", status=404)
    assert err.message == "nope"
    assert err.status == 404
    assert str(err) == "nope"
