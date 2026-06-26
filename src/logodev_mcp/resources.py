"""Resource registrations for Logo.dev MCP.

See FastMCP resource docs: https://gofastmcp.com/servers/resources
"""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.dependencies import Depends

from logodev_mcp._server_deps import get_service
from logodev_mcp.domain import Service


def register_resources(mcp: FastMCP) -> None:
    """Register all domain resources on *mcp*."""

    @mcp.resource("status://logodev-mcp")
    async def status(service: Service = Depends(get_service)) -> dict[str, object]:
        """Service status resource — JSON-serialisable dict.

        Templated resources take path parameters in the URI; static
        resources don't. See
        https://gofastmcp.com/servers/resources#templates for the full
        pattern.
        """
        return {
            # "ready" reflects an operable service: started AND at least one
            # API key configured, so a keyless (no-tool) deployment reports
            # not-ready rather than masking the misconfiguration.
            "ready": service.has_publishable or service.has_secret,
            "has_publishable": service.has_publishable,
            "has_secret": service.has_secret,
        }
