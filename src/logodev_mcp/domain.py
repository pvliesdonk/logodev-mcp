"""Domain logic for Logo.dev MCP — a thin async client over the logo.dev API.

Plain Python only: no FastMCP types here so the logic is unit-testable
without a server.  Tool wrappers in ``tools.py`` adapt these methods to
MCP (error strings, ``Image`` content).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx

from logodev_mcp.config import ProjectConfig

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

logger = logging.getLogger(__name__)

API_BASE = "https://api.logo.dev"
IMG_BASE = "https://img.logo.dev"

# Plan detection: probe these secret-key endpoints once at startup to learn
# which the configured plan allows, then hide the tools it does not.
ENTITLEMENT_PROBE_DOMAIN = "logo.dev"
ENTITLEMENT_TTL_SECONDS = 7 * 24 * 3600
_ENTITLEMENT_CACHE_FILE = "entitlements.json"
# Probe name -> the tool registered for it. The tool name is also the Service
# method used to probe it (``describe_company`` / ``get_brand``), so this single
# mapping drives both the startup probe and the lifespan's disable call for any
# probe name that comes back not-entitled.
PLAN_GATED_TOOLS = {"describe": "describe_company", "brand": "get_brand"}

_IDENTIFIER_PATHS = {
    "domain": "/{ident}",
    "ticker": "/ticker/{ident}",
    "isin": "/isin/{ident}",
    "crypto": "/crypto/{ident}",
    "name": "/name/{ident}",
}
_FORMATS = ("jpg", "png", "webp")
_THEMES = ("auto", "light", "dark")
# "404" is passed through to logo.dev as the ``fallback`` query value (the
# alternative to "monogram"): it asks for an HTTP 404 rather than a placeholder
# image when no logo exists for the identifier.
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

    @property
    def config(self) -> ProjectConfig | None:
        """The resolved config, available after :meth:`start`."""
        return self._config

    async def start(self) -> None:
        """Load config (if not injected) and build the configured clients.

        Re-entrant: if called while already started, the existing clients are
        closed first so their connection pools are not leaked.
        """
        if self._api is not None or self._img is not None:
            await self.stop()
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

        # Report each API by its client object, not by the secret-named flags.
        # has_secret is only a bool (no key value), but CodeQL's
        # py/clear-text-logging-sensitive-data heuristic still flags the
        # config.secret_key -> has_secret -> log-sink path; logging client
        # presence avoids that false positive.
        logger.info(
            "service_started image_api=%s rest_api=%s",
            self._img is not None,
            self._api is not None,
        )

    async def stop(self) -> None:
        """Close any open clients.  Safe to call more than once."""
        # Null the references first so a failure mid-close cannot leave a
        # half-closed client reachable, and a second stop() is always a no-op.
        api, img = self._api, self._img
        self._api = None
        self._img = None
        for client in (api, img):
            if client is not None:
                await client.aclose()

    # --- internal helpers ---

    def _raise_for_status(self, resp: httpx.Response, *, subject: str) -> None:
        """Map an error response to a :class:`LogoDevError`; no-op on success."""
        code = resp.status_code
        if code < 400:
            return
        # Log server-side before surfacing the user-facing string — the caller
        # only sees the returned message, so this is the operator's trace.
        logger.warning("logodev_http_error status=%s subject=%s", code, subject)
        if code in (401, 403):
            # logo.dev's body carries a precise reason (e.g. "api not available
            # for free accounts" vs "the brand API is available on Pro and
            # Enterprise plans"). Relay it so operators aren't misdirected to
            # the key when the key is valid and the plan is the real limit.
            detail = self._error_detail(resp)
            if detail is not None:
                raise LogoDevError(f"logo.dev: {detail}", status=code)
            raise LogoDevError(
                "Authentication or plan-tier problem — check your "
                "LOGODEV_MCP_SECRET_KEY and that your plan includes this "
                "endpoint.",
                status=code,
            )
        if code == 404:
            raise LogoDevError(f"No result found for {subject!r}.", status=404)
        if code == 429:
            raise LogoDevError("logo.dev rate limit reached — retry later.", status=429)
        raise LogoDevError(f"logo.dev error: {code} {resp.text}", status=code)

    def _error_detail(self, resp: httpx.Response) -> str | None:
        """Extract logo.dev's human-readable error ``msg``, if the body has one.

        Returns the stripped ``msg`` string for a JSON object that carries a
        non-empty one, else ``None`` (non-JSON body, non-object, missing or
        blank ``msg``) so the caller can fall back to a generic message.
        """
        try:
            body = resp.json()
        except ValueError:  # json.JSONDecodeError is a ValueError subclass
            return None
        if isinstance(body, dict):
            msg = body.get("msg")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
        return None

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
            logger.warning("logodev_timeout subject=%s", subject)
            raise LogoDevError("logo.dev did not respond in time.") from exc
        except httpx.TransportError as exc:
            logger.warning(
                "logodev_transport_error subject=%s error=%s",
                subject,
                type(exc).__name__,
            )
            raise LogoDevError("Cannot reach logo.dev.") from exc
        self._raise_for_status(resp, subject=subject)
        return resp

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
        # The _config/_img None checks also narrow them to non-None for mypy below.
        if not self.has_publishable or self._config is None or self._img is None:
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

        path = _IDENTIFIER_PATHS[identifier_type].format(
            ident=quote(identifier, safe="")
        )
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

    def _require_secret(self) -> httpx.AsyncClient:
        """Return the api client, or raise if the secret key is unconfigured."""
        if not self.has_secret or self._api is None:
            raise LogoDevError(
                "This endpoint needs a secret key — set LOGODEV_MCP_SECRET_KEY "
                "(Search/Describe/Brand require a paid plan)."
            )
        return self._api

    def _json(self, resp: httpx.Response, *, subject: str) -> Any:
        """Parse a JSON body, mapping a malformed payload to a LogoDevError."""
        try:
            return resp.json()
        except ValueError as exc:  # json.JSONDecodeError is a ValueError subclass
            logger.warning("logodev_bad_json subject=%s", subject)
            raise LogoDevError(
                "logo.dev returned a response that could not be parsed."
            ) from exc

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
        return self._json(resp, subject=query)

    async def describe_company(self, domain: str) -> Any:
        """Return structured company data for a domain."""
        api = self._require_secret()
        if not domain.strip():
            raise LogoDevError("domain must not be empty.")
        resp = await self._get(
            api, f"/describe/{quote(domain, safe='')}", subject=domain
        )
        return self._json(resp, subject=domain)

    async def get_brand(self, domain: str) -> Any:
        """Return the full brand profile for a domain."""
        api = self._require_secret()
        if not domain.strip():
            raise LogoDevError("domain must not be empty.")
        resp = await self._get(api, f"/brand/{quote(domain, safe='')}", subject=domain)
        return self._json(resp, subject=domain)

    # --- plan detection ---

    async def probe_entitlements(self) -> dict[str, bool]:
        """Probe which secret-key endpoints the current plan allows.

        Returns a map of probe name (``"describe"``, ``"brand"``) to an
        entitled boolean, for endpoints with a *definitive* verdict only: HTTP
        ``200`` -> ``True``, ``401``/``403`` -> ``False``. Any other outcome
        (``404``/``429``/``5xx``, timeout, transport error) is *ambiguous* and
        omitted, so the caller leaves the tool enabled (fail open). A cached
        verdict is reused while fresh (``ENTITLEMENT_TTL_SECONDS``); newly
        probed verdicts are persisted. Returns ``{}`` with no secret key.
        """
        if not self.has_secret or self._api is None:
            return {}
        cached = self._read_entitlement_cache()
        result: dict[str, bool] = {}
        probed_live = False
        # PLAN_GATED_TOOLS is the single source of truth: the tool name is also
        # the Service method that backs it, so one mapping drives both the probe
        # here and the disable in the lifespan.
        for name, tool_name in PLAN_GATED_TOOLS.items():
            if name in cached:
                result[name] = cached[name]
                continue
            probe: Callable[[str], Awaitable[Any]] = getattr(self, tool_name)
            verdict = await self._probe_endpoint(probe(ENTITLEMENT_PROBE_DOMAIN))
            if verdict is not None:
                result[name] = verdict
                probed_live = True
        if probed_live:
            self._write_entitlement_cache(result)
        return result

    @staticmethod
    async def _probe_endpoint(probe: Awaitable[Any]) -> bool | None:
        """Await one probe; ``True``/``False`` for a definitive verdict, else
        ``None`` (ambiguous — caller fails open)."""
        try:
            await probe
        except LogoDevError as exc:
            if exc.status in (401, 403):
                return False
            return None
        return True

    def _entitlement_cache_path(self) -> Path | None:
        if self._config is None:
            return None
        return self._config.state_dir / _ENTITLEMENT_CACHE_FILE

    def _key_fingerprint(self) -> str:
        """Stable, non-reversible id of the secret key so a rotated key
        invalidates the cache without ever storing the key itself."""
        key = self._config.secret_key if self._config else None
        return hashlib.sha256((key or "").encode()).hexdigest()[:16]

    def _read_entitlement_cache(self) -> dict[str, bool]:
        """Return cached definitive verdicts that are fresh and match the
        current key, else ``{}`` (missing, corrupt, stale, or rotated key)."""
        path = self._entitlement_cache_path()
        if path is None:
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        if data.get("key_fingerprint") != self._key_fingerprint():
            return {}
        checked_at = data.get("checked_at")
        if not isinstance(checked_at, int | float):
            return {}
        age = time.time() - checked_at
        if age < 0 or age > ENTITLEMENT_TTL_SECONDS:
            return {}
        ents = data.get("entitlements")
        if not isinstance(ents, dict):
            return {}
        return {k: v for k, v in ents.items() if isinstance(v, bool)}

    def _write_entitlement_cache(self, entitlements: dict[str, bool]) -> None:
        """Persist verdicts atomically; never raise on an unwritable dir."""
        path = self._entitlement_cache_path()
        if path is None or not entitlements:
            return
        payload = {
            "key_fingerprint": self._key_fingerprint(),
            "checked_at": time.time(),
            "entitlements": entitlements,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(path)
        except OSError:
            logger.debug("entitlement_cache_write_failed path=%s", path, exc_info=True)
