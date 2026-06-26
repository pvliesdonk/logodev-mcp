from __future__ import annotations

import httpx
import pytest
import respx

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


def _img_service() -> Service:
    return Service(ProjectConfig(publishable_key="pk_test"))


@pytest.mark.asyncio
async def test_get_logo_url_only_makes_no_request() -> None:
    service = _img_service()
    await service.start()
    try:
        with respx.mock:
            route = respx.get(url__startswith=IMG_BASE).mock(
                return_value=httpx.Response(200)
            )
            url, data = await service.get_logo("nike.com", url_only=True)
        assert data is None
        assert url.startswith(f"{IMG_BASE}/nike.com")
        assert "token=pk_test" in url
        assert "format=png" in url
        assert route.called is False
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_get_logo_fetches_bytes_and_builds_url() -> None:
    service = _img_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{IMG_BASE}/ticker/AAPL").mock(
                return_value=httpx.Response(200, content=b"\x89PNG...")
            )
            url, data = await service.get_logo(
                "AAPL",
                identifier_type="ticker",
                size=256,
                theme="dark",
                greyscale=True,
                retina=True,
            )
        assert data == b"\x89PNG..."
        assert url.startswith(f"{IMG_BASE}/ticker/AAPL")
        assert "size=256" in url
        assert "theme=dark" in url
        assert "greyscale=true" in url
        assert "retina=true" in url
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_get_logo_omits_default_params() -> None:
    service = _img_service()
    await service.start()
    try:
        url, _ = await service.get_logo("nike.com", url_only=True)
        # defaults (size=128, theme=auto, fallback=monogram) are omitted;
        # format is always sent (API default differs from ours).
        assert "size=" not in url
        assert "theme=" not in url
        assert "fallback=" not in url
        assert "format=png" in url
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {"identifier_type": "bogus"},
        {"size": 0},
        {"size": 801},
        {"image_format": "gif"},
        {"theme": "neon"},
        {"fallback": "blank"},
    ],
)
async def test_get_logo_rejects_bad_params_before_http(
    kwargs: dict[str, object],
) -> None:
    service = _img_service()
    await service.start()
    try:
        with respx.mock:
            route = respx.get(url__startswith=IMG_BASE).mock(
                return_value=httpx.Response(200)
            )
            with pytest.raises(LogoDevError):
                await service.get_logo("nike.com", **kwargs)  # type: ignore[arg-type]
            assert route.called is False
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_get_logo_without_publishable_key_raises() -> None:
    service = Service(ProjectConfig())  # no keys
    await service.start()
    try:
        with pytest.raises(LogoDevError):
            await service.get_logo("nike.com", url_only=True)
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_get_logo_maps_404() -> None:
    service = _img_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{IMG_BASE}/unknown.example").mock(
                return_value=httpx.Response(404)
            )
            with pytest.raises(LogoDevError) as exc:
                await service.get_logo("unknown.example")
        assert exc.value.status == 404
    finally:
        await service.stop()
