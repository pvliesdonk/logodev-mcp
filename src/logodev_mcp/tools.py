"""Tool registrations for Logo.dev MCP.

See FastMCP tool docs: https://gofastmcp.com/servers/tools
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register domain tools on *mcp*.

    Tool registrations are added in a later task; this is a no-op stub so the
    server still constructs cleanly.
    """
