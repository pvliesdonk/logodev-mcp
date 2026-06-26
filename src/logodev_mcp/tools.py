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
    """Register logo.dev tools, gated by which API keys are configured.

    Args:
        mcp: The FastMCP server to register tools on.
        config: Project configuration; loaded from the environment when omitted.
    """
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
            # Intentionally ``Any``: a concrete return annotation makes FastMCP
            # 3.4.2 emit an output schema that rejects the mixed text+image
            # content this tool returns.
        ) -> Any:
            """Fetch a company logo from logo.dev.

            Args:
                identifier: Company identifier — a domain (``nike.com``), stock
                    ticker (``AAPL``), ISIN (``US0378331005``), crypto symbol
                    (``BTC``), or brand name, depending on ``identifier_type``.
                identifier_type: One of ``domain`` (default), ``ticker``,
                    ``isin``, ``crypto``, ``name``.
                size: Pixel size, 1-800 (default 128).
                image_format: ``png`` (default), ``jpg``, or ``webp``.
                theme: ``auto`` (default), ``light``, or ``dark``.
                greyscale: Render in greyscale.
                retina: Request a 2x retina asset.
                fallback: ``monogram`` (default) renders a placeholder when no
                    logo exists; ``404`` returns an error instead.
                url_only: Return only the image URL without fetching the bytes.

            Returns:
                The image URL plus the logo image, just the URL string when
                ``url_only`` is true, or a plain error message string if the
                logo.dev request fails.
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
            "no_api_keys_configured hint=%s",
            "set LOGODEV_MCP_PUBLISHABLE_KEY (Logo) and/or "
            "LOGODEV_MCP_SECRET_KEY (Search/Describe/Brand)",
        )
