# logodev-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A FastMCP server wrapping the logo.dev API with four tools — `get_logo`, `search_brands`, `describe_company`, `get_brand` — scaffolded from `pvliesdonk/fastmcp-server-template`.

**Architecture:** The current template separates plain-Python domain logic (`domain.py`, a `Service` class — no FastMCP types) from thin tool wrappers (`tools.py`). We follow that split: `Service` holds two `httpx.AsyncClient`s (one Bearer-authed against `api.logo.dev`, one token-query against `img.logo.dev`), does all validation and HTTP, and raises `LogoDevError`; `register_tools` reads config to decide which tools to register and wraps each `Service` method, mapping `LogoDevError` → an error string and logo bytes → an MCP `Image`. Two API keys gate two tool groups; missing keys hide their tools.

**Tech Stack:** Python 3.11+, `fastmcp>=3`, `fastmcp-pvl-core`, `httpx`, `respx` (test mocking), `pytest`/`pytest-asyncio`, `uv`.

## Global Constraints

- Env var prefix: `LOGODEV_MCP_` (exact; set via copier `env_prefix=LOGODEV_MCP`).
- Python import module: `logodev_mcp`. Project/PyPI name: `logodev-mcp`.
- All domain logic in `domain.py` stays **free of FastMCP types** (no `Image`, no `mcp` imports) — keep it unit-testable as plain Python.
- **Never edit `_server_deps.py` or `server.py` outside their `DOMAIN-*` sentinel blocks** — they are template-owned and re-rendered by `copier update`. All our changes live in `config.py` (inside `CONFIG-FIELDS` / `CONFIG-FROM-ENV` sentinels only), `domain.py`, `tools.py`, and `tests/` — all domain-owned.
- Tests use `respx` to mock HTTP; **no live network calls** in the test suite.
- logo.dev hosts: `https://api.logo.dev` (Search/Describe/Brand, `Authorization: Bearer <secret>`), `https://img.logo.dev` (Logo image CDN, `?token=<publishable>`).
- Run lint/type/test via `uv run ruff check .`, `uv run mypy src`, `uv run pytest` after each task.

---

### Task 1: Scaffold from the template and orient

**Files:**
- Create (via copier): the whole `src/logodev_mcp/` tree, `tests/`, `pyproject.toml`, `CLAUDE.md`, etc.
- The pre-existing `docs/superpowers/` (this plan + the spec) and `.git` are preserved — `docs/superpowers` is in the template `_exclude` list.

- [ ] **Step 1: Run copier into the current directory**

Run from `/mnt/code/mcp-servers/logodev-mcp`:

```bash
uv run --no-project --with copier copier copy --trust --defaults \
  --data project_name=logodev-mcp \
  --data pypi_name=logodev-mcp \
  --data python_module=logodev_mcp \
  --data env_prefix=LOGODEV_MCP \
  --data human_name='Logo.dev MCP' \
  --data domain_description='Look up company logos and brand data via the logo.dev API.' \
  --data github_org=pvliesdonk \
  --data include_mcp_apps_scaffold=false \
  --data enable_authorization=false \
  gh:pvliesdonk/fastmcp-server-template .
```

(If offline, replace the source with the local path `/mnt/code/mcp-servers/fastmcp-server-template`. `--defaults` accepts template defaults for any prompt not pinned via `--data`.)

- [ ] **Step 2: Re-read the generated project instructions**

The scaffold writes `CLAUDE.md` and `.claude/CLAUDE.md` with project-specific instructions that OVERRIDE default behavior. **Read both now** before writing any code:

```bash
cat CLAUDE.md .claude/CLAUDE.md 2>/dev/null
```

Read them with the Read tool and follow them for the rest of this plan (build/test commands, conventions). If they conflict with this plan on mechanics, the generated `CLAUDE.md` wins; note the conflict.

- [ ] **Step 3: Install and run the baseline suite**

```bash
uv sync --all-extras --all-groups
uv run pytest -q
```

Expected: the template smoke tests PASS (the placeholder `ping` tool and config tests). If `pytest` collects zero tests or errors, stop and inspect — the scaffold is wrong.

- [ ] **Step 4: Confirm the generated structure matches assumptions**

```bash
ls src/logodev_mcp/
grep -n 'CONFIG-FIELDS-START\|CONFIG-FROM-ENV-START' src/logodev_mcp/config.py
grep -n 'class Service' src/logodev_mcp/domain.py
grep -n 'def register_tools' src/logodev_mcp/tools.py
```

Expected: `config.py`, `domain.py`, `tools.py`, `_server_deps.py`, `server.py`, `cli.py` exist; the two `CONFIG-*` sentinels exist; `Service` and `register_tools` exist. If `domain.py`/`tools.py` differ materially from the patterns referenced in later tasks (a `Service` class with `start`/`stop`/`ping`; `register_tools(mcp)` using `@mcp.tool` + `Depends(get_service)`), adjust the later tasks' insertion points to match the actual scaffold (anchor to these grep patterns, not line numbers).

- [ ] **Step 5: Commit the scaffold**

```bash
git add -A
git commit -m "chore: scaffold logodev-mcp from fastmcp-server-template"
```

---

### Task 2: Configuration — two API keys

**Files:**
- Modify: `src/logodev_mcp/config.py` (inside `CONFIG-FIELDS` and `CONFIG-FROM-ENV` sentinels only)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `ProjectConfig.publishable_key: str | None`, `ProjectConfig.secret_key: str | None`, loaded from `LOGODEV_MCP_PUBLISHABLE_KEY` / `LOGODEV_MCP_SECRET_KEY`. (Booleans are derived by callers via `bool(config.publishable_key)` — we deliberately do **not** add properties, to keep all edits inside the sentinel blocks.)

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
from __future__ import annotations

from logodev_mcp.config import ProjectConfig


def test_keys_default_to_none(monkeypatch):
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("LOGODEV_MCP_SECRET_KEY", raising=False)
    config = ProjectConfig.from_env()
    assert config.publishable_key is None
    assert config.secret_key is None


def test_keys_load_from_env(monkeypatch):
    monkeypatch.setenv("LOGODEV_MCP_PUBLISHABLE_KEY", "pk_live_abc")
    monkeypatch.setenv("LOGODEV_MCP_SECRET_KEY", "sk_live_xyz")
    config = ProjectConfig.from_env()
    assert config.publishable_key == "pk_live_abc"
    assert config.secret_key == "sk_live_xyz"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: 'ProjectConfig' object has no attribute 'publishable_key'`.

- [ ] **Step 3: Add the fields and env reads**

In `src/logodev_mcp/config.py`, inside the `CONFIG-FIELDS-START … CONFIG-FIELDS-END` block, add:

```python
    publishable_key: str | None = None
    secret_key: str | None = None
```

In the `CONFIG-FROM-ENV-START … CONFIG-FROM-ENV-END` block (inside the `cls(...)` call), add:

```python
            publishable_key=env(_ENV_PREFIX, "PUBLISHABLE_KEY"),
            secret_key=env(_ENV_PREFIX, "SECRET_KEY"),
```

(`env` is already imported at the top of the generated `config.py`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add src/logodev_mcp/config.py tests/test_config.py
git commit -m "feat: load logo.dev publishable and secret keys from env"
```

---

### Task 3: Domain Service — lifecycle, clients, error type

**Files:**
- Modify: `src/logodev_mcp/domain.py` (replace the placeholder `Service`)
- Test: `tests/test_domain.py`

**Interfaces:**
- Produces:
  - `LogoDevError(Exception)` with `.message: str` and `.status: int | None`.
  - `Service(config: ProjectConfig | None = None)`; `async start()`, `async stop()`.
  - After `start()`: `Service.has_publishable: bool`, `Service.has_secret: bool` reflect the loaded config; `self._api` / `self._img` are `httpx.AsyncClient | None`.
  - Module constants `API_BASE = "https://api.logo.dev"`, `IMG_BASE = "https://img.logo.dev"`.
- Consumes: `ProjectConfig` from Task 2.

- [ ] **Step 1: Write the failing test**

Create `tests/test_domain.py`:

```python
from __future__ import annotations

import httpx
import pytest

from logodev_mcp.config import ProjectConfig
from logodev_mcp.domain import API_BASE, IMG_BASE, LogoDevError, Service


@pytest.mark.asyncio
async def test_start_with_both_keys_builds_both_clients():
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
async def test_start_with_no_keys_builds_no_clients():
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
async def test_stop_is_idempotent():
    service = Service(ProjectConfig(secret_key="sk_y"))
    await service.start()
    await service.stop()
    await service.stop()  # second close must not raise
    assert service._api is None


def test_logodev_error_carries_message_and_status():
    err = LogoDevError("nope", status=404)
    assert err.message == "nope"
    assert err.status == 404
    assert str(err) == "nope"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_domain.py -v`
Expected: FAIL — `ImportError: cannot import name 'LogoDevError'` (and `API_BASE`).

- [ ] **Step 3: Replace `domain.py` with the Service skeleton**

Replace the entire body of `src/logodev_mcp/domain.py` with:

```python
"""Domain logic for Logo.dev MCP — a thin async client over the logo.dev API.

Plain Python only: no FastMCP types here so the logic is unit-testable
without a server.  Tool wrappers in ``tools.py`` adapt these methods to
MCP (error strings, ``Image`` content).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from logodev_mcp.config import ProjectConfig

logger = logging.getLogger(__name__)

API_BASE = "https://api.logo.dev"
IMG_BASE = "https://img.logo.dev"

_IDENTIFIER_PATHS = {
    "domain": "/{ident}",
    "ticker": "/ticker/{ident}",
    "isin": "/isin/{ident}",
    "crypto": "/crypto/{ident}",
    "name": "/name/{ident}",
}
_FORMATS = ("jpg", "png", "webp")
_THEMES = ("auto", "light", "dark")
_FALLBACKS = ("monogram", "404")
_STRATEGIES = ("suggest", "match")

_TIMEOUT = 30.0


class LogoDevError(Exception):
    """A logo.dev request failed validation or returned an error response."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class Service:
    """Async client over the logo.dev REST and image APIs.

    Pass an explicit :class:`ProjectConfig` for tests; in production the
    lifespan constructs ``Service()`` with no args and :meth:`start` loads
    config from the environment.
    """

    def __init__(self, config: ProjectConfig | None = None) -> None:
        self._config = config
        self._api: httpx.AsyncClient | None = None
        self._img: httpx.AsyncClient | None = None
        self.has_publishable = False
        self.has_secret = False

    async def start(self) -> None:
        """Load config (if not injected) and build the configured clients."""
        config = self._config or ProjectConfig.from_env()
        self._config = config
        self.has_publishable = bool(config.publishable_key)
        self.has_secret = bool(config.secret_key)

        if self.has_secret:
            self._api = httpx.AsyncClient(
                base_url=API_BASE,
                headers={"Authorization": f"Bearer {config.secret_key}"},
                timeout=_TIMEOUT,
            )
        if self.has_publishable:
            self._img = httpx.AsyncClient(base_url=IMG_BASE, timeout=_TIMEOUT)

        logger.info(
            "logo.dev service started (publishable=%s, secret=%s)",
            self.has_publishable,
            self.has_secret,
        )

    async def stop(self) -> None:
        """Close any open clients.  Safe to call more than once."""
        for client in (self._api, self._img):
            if client is not None:
                await client.aclose()
        self._api = None
        self._img = None

    # --- internal helpers (filled in by later tasks) ---

    def _raise_for_status(self, resp: httpx.Response, *, subject: str) -> None:
        """Map an error response to a :class:`LogoDevError`; no-op on success."""
        code = resp.status_code
        if code < 400:
            return
        if code in (401, 403):
            raise LogoDevError(
                "Authentication or plan-tier problem — check your "
                "LOGODEV_MCP_SECRET_KEY and that your plan includes this "
                "endpoint.",
                status=code,
            )
        if code == 404:
            raise LogoDevError(f"No result found for {subject!r}.", status=404)
        if code == 429:
            raise LogoDevError(
                "logo.dev rate limit reached — retry later.", status=429
            )
        raise LogoDevError(f"logo.dev error: {code} {resp.text}", status=code)

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        subject: str,
    ) -> httpx.Response:
        """GET with transport-error translation and status mapping."""
        try:
            resp = await client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise LogoDevError("logo.dev did not respond in time.") from exc
        except httpx.TransportError as exc:
            raise LogoDevError("Cannot reach logo.dev.") from exc
        self._raise_for_status(resp, subject=subject)
        return resp
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_domain.py -v`
Expected: PASS (4 tests). The `_server_deps.py` lifespan still calls `Service()` with no args — unchanged and compatible.

- [ ] **Step 5: Verify the placeholder smoke test still passes or is updated**

Run: `uv run pytest -q`
Expected: PASS. If a generated `tests/test_smoke.py` asserted on the placeholder `ping` tool / `Service.ping`, and `ping` no longer exists, update that test to call `Service.start`/`stop` (or delete the `ping`-specific assertion) rather than leaving it broken — the removed placeholder's tests get rewritten to the new state.

- [ ] **Step 6: Commit**

```bash
git add src/logodev_mcp/domain.py tests/test_domain.py tests/test_smoke.py
git commit -m "feat: logo.dev Service lifecycle, clients, and error type"
```

---

### Task 4: Domain — `get_logo`

**Files:**
- Modify: `src/logodev_mcp/domain.py` (add `get_logo` method)
- Test: `tests/test_domain.py`

**Interfaces:**
- Produces: `async Service.get_logo(identifier: str, *, identifier_type="domain", size=128, image_format="png", theme="auto", greyscale=False, retina=False, fallback="monogram", url_only=False) -> tuple[str, bytes | None]`. Returns `(url, bytes)`; `bytes is None` when `url_only=True`. Raises `LogoDevError` on bad params, missing publishable key, or HTTP error.
- Consumes: `_get`, `_raise_for_status`, constants from Task 3.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_domain.py`:

```python
import respx


def _img_service() -> Service:
    return Service(ProjectConfig(publishable_key="pk_test"))


@pytest.mark.asyncio
async def test_get_logo_url_only_makes_no_request():
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
async def test_get_logo_fetches_bytes_and_builds_url():
    service = _img_service()
    await service.start()
    try:
        with respx.mock:
            respx.get(f"{IMG_BASE}/ticker/AAPL").mock(
                return_value=httpx.Response(200, content=b"\x89PNG...")
            )
            url, data = await service.get_logo(
                "AAPL", identifier_type="ticker", size=256, theme="dark",
                greyscale=True, retina=True,
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
async def test_get_logo_omits_default_params():
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
async def test_get_logo_rejects_bad_params_before_http(kwargs):
    service = _img_service()
    await service.start()
    try:
        with respx.mock:
            route = respx.get(url__startswith=IMG_BASE).mock(
                return_value=httpx.Response(200)
            )
            with pytest.raises(LogoDevError):
                await service.get_logo("nike.com", **kwargs)
            assert route.called is False
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_get_logo_without_publishable_key_raises():
    service = Service(ProjectConfig())  # no keys
    await service.start()
    try:
        with pytest.raises(LogoDevError):
            await service.get_logo("nike.com", url_only=True)
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_get_logo_maps_404():
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_domain.py -k get_logo -v`
Expected: FAIL — `AttributeError: 'Service' object has no attribute 'get_logo'`.

- [ ] **Step 3: Implement `get_logo`**

Add to the `Service` class in `src/logodev_mcp/domain.py` (after `_get`):

```python
    async def get_logo(
        self,
        identifier: str,
        *,
        identifier_type: str = "domain",
        size: int = 128,
        image_format: str = "png",
        theme: str = "auto",
        greyscale: bool = False,
        retina: bool = False,
        fallback: str = "monogram",
        url_only: bool = False,
    ) -> tuple[str, bytes | None]:
        """Build the img.logo.dev URL and (unless ``url_only``) fetch the bytes."""
        if not self.has_publishable or self._config is None or self._img is None:
            if not self.has_publishable:
                raise LogoDevError(
                    "Logo API not configured — set LOGODEV_MCP_PUBLISHABLE_KEY."
                )
        if identifier_type not in _IDENTIFIER_PATHS:
            raise LogoDevError(
                f"Invalid identifier_type {identifier_type!r}; expected one of "
                f"{list(_IDENTIFIER_PATHS)}."
            )
        if not 1 <= size <= 800:
            raise LogoDevError("size must be between 1 and 800.")
        if image_format not in _FORMATS:
            raise LogoDevError(
                f"Invalid format {image_format!r}; expected one of {list(_FORMATS)}."
            )
        if theme not in _THEMES:
            raise LogoDevError(
                f"Invalid theme {theme!r}; expected one of {list(_THEMES)}."
            )
        if fallback not in _FALLBACKS:
            raise LogoDevError(
                f"Invalid fallback {fallback!r}; expected one of {list(_FALLBACKS)}."
            )

        path = _IDENTIFIER_PATHS[identifier_type].format(ident=identifier)
        params: dict[str, Any] = {
            "token": self._config.publishable_key,
            "format": image_format,
        }
        if size != 128:
            params["size"] = size
        if theme != "auto":
            params["theme"] = theme
        if greyscale:
            params["greyscale"] = "true"
        if retina:
            params["retina"] = "true"
        if fallback != "monogram":
            params["fallback"] = fallback

        url = str(httpx.URL(IMG_BASE + path, params=params))
        if url_only:
            return url, None

        resp = await self._get(self._img, path, params=params, subject=identifier)
        return url, resp.content
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_domain.py -k get_logo -v`
Expected: PASS (all `get_logo` tests).

- [ ] **Step 5: Commit**

```bash
git add src/logodev_mcp/domain.py tests/test_domain.py
git commit -m "feat: Service.get_logo with validation and URL building"
```

---

### Task 5: Domain — `search_brands`, `describe_company`, `get_brand`

**Files:**
- Modify: `src/logodev_mcp/domain.py` (add three REST methods)
- Test: `tests/test_domain.py`

**Interfaces:**
- Produces:
  - `async Service.search_brands(query: str, *, strategy="suggest") -> Any` → parsed JSON (`GET /search?q=…`).
  - `async Service.describe_company(domain: str) -> Any` → parsed JSON (`GET /describe/{domain}`).
  - `async Service.get_brand(domain: str) -> Any` → parsed JSON (`GET /brand/{domain}`).
  - Each raises `LogoDevError` when the secret key is absent, on invalid params, or on HTTP error.
- Consumes: `_get`, `_STRATEGIES`, `self._api` from Task 3.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_domain.py`:

```python
def _api_service() -> Service:
    return Service(ProjectConfig(secret_key="sk_test"))


@pytest.mark.asyncio
async def test_search_brands_sends_query_and_parses_json():
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
async def test_search_brands_omits_default_strategy():
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
async def test_search_brands_rejects_bad_strategy_before_http():
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
async def test_describe_company_hits_describe_path():
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
async def test_get_brand_hits_brand_path():
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
async def test_rest_methods_map_401(monkeypatch):
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
async def test_rest_methods_require_secret_key():
    service = Service(ProjectConfig())  # no keys
    await service.start()
    try:
        for call in (
            service.search_brands("nike"),
            service.describe_company("nike.com"),
            service.get_brand("nike.com"),
        ):
            with pytest.raises(LogoDevError):
                await call
    finally:
        await service.stop()


@pytest.mark.asyncio
async def test_search_brands_maps_timeout():
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_domain.py -k "search_brands or describe or brand or rest_methods" -v`
Expected: FAIL — `AttributeError: 'Service' object has no attribute 'search_brands'`.

- [ ] **Step 3: Implement the three REST methods**

Add to the `Service` class in `src/logodev_mcp/domain.py` (after `get_logo`):

```python
    def _require_secret(self) -> httpx.AsyncClient:
        """Return the api client, or raise if the secret key is unconfigured."""
        if not self.has_secret or self._api is None:
            raise LogoDevError(
                "This endpoint needs a secret key — set LOGODEV_MCP_SECRET_KEY "
                "(Search/Describe/Brand require a paid plan)."
            )
        return self._api

    async def search_brands(self, query: str, *, strategy: str = "suggest") -> Any:
        """Resolve a brand/company name to candidate domains."""
        api = self._require_secret()
        if strategy not in _STRATEGIES:
            raise LogoDevError(
                f"Invalid strategy {strategy!r}; expected one of {list(_STRATEGIES)}."
            )
        if not query.strip():
            raise LogoDevError("query must not be empty.")
        params: dict[str, Any] = {"q": query}
        if strategy != "suggest":
            params["strategy"] = strategy
        resp = await self._get(api, "/search", params=params, subject=query)
        return resp.json()

    async def describe_company(self, domain: str) -> Any:
        """Return structured company data for a domain."""
        api = self._require_secret()
        if not domain.strip():
            raise LogoDevError("domain must not be empty.")
        resp = await self._get(api, f"/describe/{domain}", subject=domain)
        return resp.json()

    async def get_brand(self, domain: str) -> Any:
        """Return the full brand profile for a domain."""
        api = self._require_secret()
        if not domain.strip():
            raise LogoDevError("domain must not be empty.")
        resp = await self._get(api, f"/brand/{domain}", subject=domain)
        return resp.json()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_domain.py -v`
Expected: PASS (all domain tests, including Tasks 3–5).

- [ ] **Step 5: Commit**

```bash
git add src/logodev_mcp/domain.py tests/test_domain.py
git commit -m "feat: Service search_brands, describe_company, get_brand"
```

---

### Task 6: Tool registration — conditional, with Image and error mapping

**Files:**
- Modify: `src/logodev_mcp/tools.py` (replace placeholder `register_tools`)
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `Service` methods (Tasks 4–5), `get_service` dependency (from generated `_server_deps.py`), `ProjectConfig` (Task 2), `make_server` (generated `server.py`).
- Produces: `register_tools(mcp: FastMCP, config: ProjectConfig | None = None) -> None` registering `get_logo` only when a publishable key is set, and `search_brands` / `describe_company` / `get_brand` only when a secret key is set. Each tool returns JSON-serialisable data or, on `LogoDevError`, the error message string; `get_logo` returns `[url, Image]` (or just the URL string when `url_only=True`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tools.py`:

```python
from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.utilities.types import Image

from logodev_mcp.domain import API_BASE, IMG_BASE
from logodev_mcp.server import make_server


async def _tool_names(mcp) -> set[str]:
    async with Client(mcp) as client:
        return {t.name for t in await client.list_tools()}


@pytest.mark.asyncio
async def test_only_logo_tool_with_publishable_only(monkeypatch):
    monkeypatch.setenv("LOGODEV_MCP_PUBLISHABLE_KEY", "pk_x")
    monkeypatch.delenv("LOGODEV_MCP_SECRET_KEY", raising=False)
    names = await _tool_names(make_server())
    assert "get_logo" in names
    assert "search_brands" not in names
    assert "get_brand" not in names


@pytest.mark.asyncio
async def test_only_rest_tools_with_secret_only(monkeypatch):
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("LOGODEV_MCP_SECRET_KEY", "sk_y")
    names = await _tool_names(make_server())
    assert "get_logo" not in names
    assert {"search_brands", "describe_company", "get_brand"} <= names


@pytest.mark.asyncio
async def test_no_api_tools_without_keys(monkeypatch):
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("LOGODEV_MCP_SECRET_KEY", raising=False)
    names = await _tool_names(make_server())
    assert {"get_logo", "search_brands", "describe_company", "get_brand"}.isdisjoint(
        names
    )


@pytest.mark.asyncio
async def test_get_logo_tool_returns_url_and_image(monkeypatch):
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
    assert any(getattr(b, "type", None) == "text" and "img.logo.dev" in b.text
               for b in blocks)
    assert any(getattr(b, "type", None) == "image" for b in blocks)


@pytest.mark.asyncio
async def test_get_brand_tool_maps_error_to_message(monkeypatch):
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("LOGODEV_MCP_SECRET_KEY", "sk_y")
    mcp = make_server()
    with respx.mock:
        respx.get(f"{API_BASE}/brand/nike.com").mock(
            return_value=httpx.Response(401)
        )
        async with Client(mcp) as client:
            result = await client.call_tool("get_brand", {"domain": "nike.com"})
    text = " ".join(b.text for b in result.content if getattr(b, "type", None) == "text")
    assert "plan" in text.lower() or "secret" in text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tools.py -v`
Expected: FAIL — all four API tools are absent (placeholder `ping` is still the only tool), so the registration assertions fail.

- [ ] **Step 3: Replace `register_tools`**

Replace the body of `src/logodev_mcp/tools.py` with:

```python
"""Tool registrations for Logo.dev MCP.

See FastMCP tool docs: https://gofastmcp.com/servers/tools
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from fastmcp.utilities.types import Image

from logodev_mcp._server_deps import get_service
from logodev_mcp.config import ProjectConfig
from logodev_mcp.domain import LogoDevError, Service

logger = logging.getLogger(__name__)

_IMAGE_FORMATS = {"jpg": "jpeg", "png": "png", "webp": "webp"}


def register_tools(mcp: FastMCP, config: ProjectConfig | None = None) -> None:
    """Register logo.dev tools, gated by which API keys are configured."""
    config = config or ProjectConfig.from_env()

    if config.publishable_key:

        @mcp.tool(annotations={"readOnlyHint": True})
        async def get_logo(
            identifier: str,
            identifier_type: str = "domain",
            size: int = 128,
            image_format: str = "png",
            theme: str = "auto",
            greyscale: bool = False,
            retina: bool = False,
            fallback: str = "monogram",
            url_only: bool = False,
            service: Service = Depends(get_service),
        ) -> Any:
            """Fetch a company logo from logo.dev.

            Args:
                identifier: Company identifier — a domain (``nike.com``), stock
                    ticker (``AAPL``), ISIN (``US0378331005``), crypto symbol
                    (``BTC``), or brand name, depending on ``identifier_type``.
                identifier_type: One of ``domain`` (default), ``ticker``,
                    ``isin``, ``crypto``, ``name``.
                size: Pixel size, 1–800 (default 128).
                image_format: ``png`` (default), ``jpg``, or ``webp``.
                theme: ``auto`` (default), ``light``, or ``dark``.
                greyscale: Render in greyscale.
                retina: Request a 2× retina asset.
                fallback: ``monogram`` (default) renders a placeholder when no
                    logo exists; ``404`` returns an error instead.
                url_only: Return only the image URL without fetching the bytes.

            Returns:
                The image URL plus the logo image, or just the URL when
                ``url_only`` is true.
            """
            try:
                url, data = await service.get_logo(
                    identifier,
                    identifier_type=identifier_type,
                    size=size,
                    image_format=image_format,
                    theme=theme,
                    greyscale=greyscale,
                    retina=retina,
                    fallback=fallback,
                    url_only=url_only,
                )
            except LogoDevError as exc:
                return exc.message
            if data is None:
                return url
            return [url, Image(data=data, format=_IMAGE_FORMATS[image_format])]

    if config.secret_key:

        @mcp.tool(annotations={"readOnlyHint": True})
        async def search_brands(
            query: str,
            strategy: str = "suggest",
            service: Service = Depends(get_service),
        ) -> str:
            """Resolve a brand or company name to candidate domains.

            Args:
                query: The brand/company name to look up.
                strategy: ``suggest`` (default, typeahead) or ``match``.

            Returns:
                A JSON array of candidate brands (name, domain, logo URL).
            """
            try:
                return json.dumps(await service.search_brands(query, strategy=strategy))
            except LogoDevError as exc:
                return exc.message

        @mcp.tool(annotations={"readOnlyHint": True})
        async def describe_company(
            domain: str,
            service: Service = Depends(get_service),
        ) -> str:
            """Return structured company data for a domain.

            Args:
                domain: The company domain (e.g. ``nike.com``).

            Returns:
                A JSON object with name, description, colors, and socials.
            """
            try:
                return json.dumps(await service.describe_company(domain))
            except LogoDevError as exc:
                return exc.message

        @mcp.tool(annotations={"readOnlyHint": True})
        async def get_brand(
            domain: str,
            service: Service = Depends(get_service),
        ) -> str:
            """Return the full brand profile for a domain.

            Args:
                domain: The company domain (e.g. ``nike.com``).

            Returns:
                A JSON object with logo, brandmark, banners, colors, and
                description — a richer superset of ``describe_company``.
            """
            try:
                return json.dumps(await service.get_brand(domain))
            except LogoDevError as exc:
                return exc.message

    if not config.publishable_key and not config.secret_key:
        logger.warning(
            "No logo.dev API keys configured — no API tools registered. "
            "Set LOGODEV_MCP_PUBLISHABLE_KEY (Logo) and/or "
            "LOGODEV_MCP_SECRET_KEY (Search/Describe/Brand)."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tools.py -v`
Expected: PASS (5 tests). If the `result.content` block attribute names differ in the installed FastMCP version, adjust the assertions to match (`uv run python -c "import fastmcp, inspect"` and inspect a real `CallToolResult`) — the behavior (a text block with the URL + an image block) is the contract.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q && uv run ruff check . && uv run mypy src`
Expected: all PASS / clean.

- [ ] **Step 6: Commit**

```bash
git add src/logodev_mcp/tools.py tests/test_tools.py
git commit -m "feat: register logo.dev tools gated by configured API keys"
```

---

### Task 7: Server instructions, docs, and final verification

**Files:**
- Modify: `src/logodev_mcp/server.py` (only the `domain_line` / instructions text if it still reads the placeholder — inside template wiring; otherwise skip)
- Modify: `README.md` (inside `DOMAIN-START … DOMAIN-END` markers), `.env.example`
- Modify: `CLAUDE.md` (inside its `DOMAIN-START … DOMAIN-END` markers) — describe the four tools and two keys

- [ ] **Step 1: Document the env vars**

In `.env.example`, add (near the other commented vars):

```bash
# logo.dev publishable key (pk_…) — enables the get_logo tool
# LOGODEV_MCP_PUBLISHABLE_KEY=pk_live_xxx
# logo.dev secret key (sk_…) — enables search_brands / describe_company / get_brand
# LOGODEV_MCP_SECRET_KEY=sk_live_xxx
```

- [ ] **Step 2: Fill the README and CLAUDE.md domain blocks**

In `README.md`, inside the `<!-- DOMAIN-START -->` / `<!-- DOMAIN-END -->` block, write a short overview: the four tools, which key each needs, and the graceful-degradation behavior. In `CLAUDE.md`, inside its `DOMAIN-START`/`DOMAIN-END` markers, note the domain/tools/error-string convention and the "domain.py stays FastMCP-free" rule so future sessions follow it.

- [ ] **Step 3: Confirm the MCP instructions read sensibly**

The generated `server.py` builds instructions from the copier `domain_description`. Verify it reads correctly:

```bash
grep -n 'domain_line\|domain_description' src/logodev_mcp/server.py
```

If the rendered text is the placeholder rather than "Look up company logos and brand data via the logo.dev API.", fix it inside the template wiring (it is set from the copier answer, so it should already be correct).

- [ ] **Step 4: Full verification**

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run logodev-mcp --help
```

Expected: tests PASS, lint/type clean, the CLI entry point prints help. Optionally smoke-run with a real key set to confirm a live call works (not part of the automated suite).

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md .env.example src/logodev_mcp/server.py
git commit -m "docs: document logo.dev tools, keys, and conventions"
```

---

## Self-Review notes

- **Spec coverage:** Logo (Task 4), Search/Describe/Brand (Task 5), two-key config (Task 2), graceful degradation (Task 6 conditional registration + Task 3 client gating), error mapping (Task 3 `_raise_for_status`/`_get`, surfaced as strings in Task 6), both-URL-and-image logo output (Task 6 `[url, Image]`), `url_only` (Tasks 4/6), TDD with respx and no live network (all tasks). Transaction API and extra CDN paths remain out of scope per the spec.
- **Update-safety:** all edits are confined to domain-owned files (`config.py` sentinels, `domain.py`, `tools.py`, `tests/`) plus sentinel-bracketed `README.md`/`CLAUDE.md`; `_server_deps.py` and `server.py` core wiring are left untouched, so `copier update` stays clean.
- **Type consistency:** `Service` method names and signatures in Tasks 4–5 match their call sites in Task 6; `get_logo` returns `tuple[str, bytes | None]` consumed as `url, data`; `_IMAGE_FORMATS` maps `jpg→jpeg` for the `Image` format arg.
