from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING

import httpx
import pytest
import respx

if TYPE_CHECKING:
    from pathlib import Path

from logodev_mcp.config import ProjectConfig
from logodev_mcp.domain import (
    API_BASE,
    ENTITLEMENT_PROBE_DOMAIN,
    IMG_BASE,
    LogoDevError,
    Service,
)


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
    service = Service(ProjectConfig(publishable_key="pk_x", secret_key="sk_y"))
    await service.start()
    await service.stop()
    await service.stop()  # second close must not raise
    assert service._api is None
    assert service._img is None


@pytest.mark.asyncio
async def test_start_twice_replaces_clients_without_leak() -> None:
    service = Service(ProjectConfig(secret_key="sk_y"))
    await service.start()
    first_api = service._api
    await service.start()  # re-entrant: must close the first client, not leak it
    try:
        assert first_api is not None and first_api.is_closed
        assert service._api is not None and service._api is not first_api
    finally:
        await service.stop()


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
async def test_get_logo_encodes_identifier_in_path() -> None:
    service = _img_service()
    await service.start()
    try:
        url, _ = await service.get_logo(
            "Johnson & Johnson", identifier_type="name", url_only=True
        )
        # Spaces and '&' must be percent-encoded, not left to split the path.
        assert f"{IMG_BASE}/name/Johnson%20%26%20Johnson" in url
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


def _api_service() -> Service:
    return Service(ProjectConfig(secret_key="sk_test"))


@pytest.mark.asyncio
async def test_search_brands_sends_query_and_parses_json() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            route = respx.get(f"{API_BASE}/search").mock(
                return_value=httpx.Response(
                    200, json=[{"name": "Nike", "domain": "nike.com"}]
                )
            )
            result = await service.search_brands("nike", strategy="match")
        assert result == [{"name": "Nike", "domain": "nike.com"}]
        sent = route.calls.last.request
        assert sent.url.params["q"] == "nike"
        assert sent.url.params["strategy"] == "match"
        assert sent.headers["Authorization"] == "Bearer sk_test"
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_search_brands_omits_default_strategy() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            route = respx.get(f"{API_BASE}/search").mock(
                return_value=httpx.Response(200, json=[])
            )
            await service.search_brands("nike")
        assert "strategy" not in route.calls.last.request.url.params
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_search_brands_rejects_bad_strategy_before_http() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            route = respx.get(f"{API_BASE}/search").mock(
                return_value=httpx.Response(200, json=[])
            )
            with pytest.raises(LogoDevError):
                await service.search_brands("nike", strategy="fuzzy")
            assert route.called is False
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_describe_company_hits_describe_path() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/describe/nike.com").mock(
                return_value=httpx.Response(200, json={"name": "Nike"})
            )
            result = await service.describe_company("nike.com")
        assert result == {"name": "Nike"}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_get_brand_hits_brand_path() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/brand/nike.com").mock(
                return_value=httpx.Response(200, json={"colors": ["#111"]})
            )
            result = await service.get_brand("nike.com")
        assert result == {"colors": ["#111"]}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_rest_methods_map_401() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/brand/nike.com").mock(
                return_value=httpx.Response(401)
            )
            with pytest.raises(LogoDevError) as exc:
                await service.get_brand("nike.com")
        assert exc.value.status == 401
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "upstream_msg"),
    [
        (401, "api not available for free accounts. upgrade your account"),
        (403, "the brand API is available on Pro and Enterprise plans"),
    ],
)
async def test_rest_methods_surface_upstream_msg(
    status: int, upstream_msg: str
) -> None:
    # logo.dev returns a descriptive ``msg`` on 401/403; relay it verbatim
    # instead of a generic key-blaming string.
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/brand/nike.com").mock(
                return_value=httpx.Response(status, json={"msg": upstream_msg})
            )
            with pytest.raises(LogoDevError) as exc:
                await service.get_brand("nike.com")
        assert exc.value.status == status
        assert upstream_msg in exc.value.message
        # The misleading "check your key" generic must not bury the real reason.
        assert "LOGODEV_MCP_SECRET_KEY" not in exc.value.message
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"error": "forbidden"},  # dict, no ``msg`` key
        {"msg": ""},  # blank msg
        {"msg": "   "},  # whitespace-only msg
        {"msg": 123},  # non-string msg
        ["forbidden"],  # non-dict JSON body
    ],
)
async def test_rest_methods_fall_back_when_msg_unusable(body: object) -> None:
    # A JSON body without a usable ``msg`` (missing, blank, non-string, or a
    # non-object body) falls back to the generic message rather than raising.
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/brand/nike.com").mock(
                return_value=httpx.Response(403, json=body)
            )
            with pytest.raises(LogoDevError) as exc:
                await service.get_brand("nike.com")
        assert exc.value.status == 403
        assert "LOGODEV_MCP_SECRET_KEY" in exc.value.message
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_rest_methods_strip_surrounding_whitespace_from_msg() -> None:
    # The relayed message is stripped — an equality assertion guards against a
    # regression that a substring check would miss.
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/brand/nike.com").mock(
                return_value=httpx.Response(403, json={"msg": "  upgrade your plan  "})
            )
            with pytest.raises(LogoDevError) as exc:
                await service.get_brand("nike.com")
        assert exc.value.message == "logo.dev: upgrade your plan"
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_rest_methods_require_secret_key() -> None:
    service = Service(ProjectConfig())  # no keys
    await service.start()
    try:
        for factory, args in (
            (service.search_brands, ("nike",)),
            (service.describe_company, ("nike.com",)),
            (service.get_brand, ("nike.com",)),
        ):
            with pytest.raises(LogoDevError):
                await factory(*args)
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_search_brands_maps_timeout() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/search").mock(
                side_effect=httpx.ConnectTimeout("slow")
            )
            with pytest.raises(LogoDevError) as exc:
                await service.search_brands("nike")
        assert "did not respond" in exc.value.message
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_search_brands_maps_connect_error() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/search").mock(
                side_effect=httpx.ConnectError("refused")
            )
            with pytest.raises(LogoDevError) as exc:
                await service.search_brands("nike")
        assert "Cannot reach" in exc.value.message
    finally:
        await service.stop()


# --- entitlement probing (plan detection) ---

_DESCRIBE_URL = f"{API_BASE}/describe/{ENTITLEMENT_PROBE_DOMAIN}"
_BRAND_URL = f"{API_BASE}/brand/{ENTITLEMENT_PROBE_DOMAIN}"


def _probe_service(state_dir: Path, *, secret_key: str = "sk_test") -> Service:
    return Service(ProjectConfig(secret_key=secret_key, state_dir=state_dir))


def _fingerprint(secret_key: str) -> str:
    return hashlib.sha256(secret_key.encode()).hexdigest()[:16]


def _write_cache(
    state_dir: Path,
    entitlements: dict[str, bool],
    *,
    secret_key: str = "sk_test",
    age_seconds: float = 0.0,
) -> Path:
    path = state_dir / "entitlements.json"
    path.write_text(
        json.dumps(
            {
                "key_fingerprint": _fingerprint(secret_key),
                "checked_at": time.time() - age_seconds,
                "entitlements": entitlements,
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.asyncio
async def test_probe_entitlements_both_available_and_cached(tmp_path: Path) -> None:
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(200, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(200, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": True, "brand": True}
        cached = json.loads((tmp_path / "entitlements.json").read_text())
        assert cached["entitlements"] == {"describe": True, "brand": True}
        assert cached["key_fingerprint"] == _fingerprint("sk_test")
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_both_denied(tmp_path: Path) -> None:
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(401, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(403, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": False, "brand": False}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_mixed(tmp_path: Path) -> None:
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(200, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(403, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": True, "brand": False}
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [404, 429, 500])
async def test_probe_entitlements_ambiguous_status_omitted(
    tmp_path: Path, status: int
) -> None:
    # Anything other than 200/401/403 is ambiguous — omit it (fail open),
    # never treat it as "denied". 404 in particular must not hide a tool.
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(status, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(200, json={}))
            result = await service.probe_entitlements()
        assert "describe" not in result
        assert result["brand"] is True
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [httpx.ConnectError("refused"), httpx.ConnectTimeout("slow")],
)
async def test_probe_entitlements_network_error_omitted(
    tmp_path: Path, error: Exception
) -> None:
    # Transport errors and timeouts both fail open (omitted), never "denied".
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(side_effect=error)
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(403, json={}))
            result = await service.probe_entitlements()
        assert result == {"brand": False}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_merges_partial_fresh_cache(tmp_path: Path) -> None:
    # A fresh cache covering only one probe (the realistic state when the other
    # was ambiguous last run): the cached one is reused without HTTP, the missing
    # one is probed live, and the merged verdict is persisted.
    _write_cache(tmp_path, {"describe": True})
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            describe = respx.get(_DESCRIBE_URL).mock(
                return_value=httpx.Response(200, json={})
            )
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(200, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": True, "brand": True}
        assert describe.called is False  # cached describe must not be re-probed
        merged = json.loads((tmp_path / "entitlements.json").read_text())
        assert merged["entitlements"] == {"describe": True, "brand": True}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_no_secret_returns_empty(tmp_path: Path) -> None:
    service = Service(ProjectConfig(state_dir=tmp_path))  # no secret key
    await service.start()
    try:
        with respx.mock:
            route = respx.get(url__startswith=API_BASE).mock(
                return_value=httpx.Response(200, json={})
            )
            result = await service.probe_entitlements()
        assert result == {}
        assert route.called is False
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_uses_fresh_cache_without_http(tmp_path: Path) -> None:
    _write_cache(tmp_path, {"describe": True, "brand": False})
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            route = respx.get(url__startswith=API_BASE).mock(
                return_value=httpx.Response(200, json={})
            )
            result = await service.probe_entitlements()
        assert result == {"describe": True, "brand": False}
        assert route.called is False
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_reprobes_stale_cache(tmp_path: Path) -> None:
    _write_cache(
        tmp_path, {"describe": False, "brand": False}, age_seconds=8 * 24 * 3600
    )
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(200, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(200, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": True, "brand": True}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_ignores_cache_for_different_key(
    tmp_path: Path,
) -> None:
    _write_cache(tmp_path, {"describe": False, "brand": False}, secret_key="sk_other")
    service = _probe_service(tmp_path, secret_key="sk_test")
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(200, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(200, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": True, "brand": True}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_ignores_corrupt_cache(tmp_path: Path) -> None:
    (tmp_path / "entitlements.json").write_text("{not json", encoding="utf-8")
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(401, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(403, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": False, "brand": False}
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        "[]",  # valid JSON but not an object
        '{"key_fingerprint": "FP", "checked_at": "soon", "entitlements": {}}',
        '{"key_fingerprint": "FP", "checked_at": 0, "entitlements": ["x"]}',
        # well-formed envelope but a non-bool value: the bad key is dropped and
        # re-probed rather than trusted as a truthy "entitled".
        '{"key_fingerprint": "FP", "checked_at": NOW,'
        ' "entitlements": {"describe": "yes", "brand": true}}',
    ],
)
async def test_probe_entitlements_ignores_malformed_cache(
    tmp_path: Path, payload: str
) -> None:
    # A structurally-wrong cache (non-object, bad timestamp type, non-object
    # entitlements, or a non-bool value) is treated as a miss and re-probed,
    # never crashing or trusting the bad value.
    payload = payload.replace("FP", _fingerprint("sk_test")).replace(
        "NOW", str(time.time())
    )
    (tmp_path / "entitlements.json").write_text(payload, encoding="utf-8")
    service = _probe_service(tmp_path)
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(200, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(200, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": True, "brand": True}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_probe_entitlements_survives_unwritable_cache_dir(tmp_path: Path) -> None:
    # state_dir points at a path whose parent is a file, so mkdir/write fails;
    # the probe must still return its verdict without raising.
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    service = _probe_service(blocker / "state")
    await service.start()
    try:
        with respx.mock:
            respx.get(_DESCRIBE_URL).mock(return_value=httpx.Response(200, json={}))
            respx.get(_BRAND_URL).mock(return_value=httpx.Response(403, json={}))
            result = await service.probe_entitlements()
        assert result == {"describe": True, "brand": False}
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_describe_company_encodes_domain_in_path() -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            route = respx.get(f"{API_BASE}/describe/foo%2Fbar").mock(
                return_value=httpx.Response(200, json={})
            )
            await service.describe_company("foo/bar")
        # '/' must be percent-encoded, not split into a new path segment.
        assert route.called
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "needle"),
    [
        (403, "Authentication or plan-tier"),
        (429, "rate limit"),
        (500, "logo.dev error: 500"),
    ],
)
async def test_rest_methods_map_status_codes(status: int, needle: str) -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{API_BASE}/brand/nike.com").mock(
                return_value=httpx.Response(status, text="boom")
            )
            with pytest.raises(LogoDevError) as exc:
                await service.get_brand("nike.com")
        assert exc.value.status == status
        assert needle in exc.value.message
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("factory_name", "arg"),
    [
        ("search_brands", "   "),
        ("describe_company", ""),
        ("get_brand", "  "),
    ],
)
async def test_rest_methods_reject_blank_input_before_http(
    factory_name: str, arg: str
) -> None:
    service = _api_service()
    await service.start()
    try:
        with respx.mock:
            route = respx.get(url__startswith=API_BASE).mock(
                return_value=httpx.Response(200, json={})
            )
            with pytest.raises(LogoDevError):
                await getattr(service, factory_name)(arg)
            assert route.called is False
    finally:
        await service.stop()
