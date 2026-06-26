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
            "service_started publishable=%s secret=%s",
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
            raise LogoDevError("logo.dev rate limit reached — retry later.", status=429)
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
