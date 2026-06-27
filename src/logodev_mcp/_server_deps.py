"""Service lifespan + dependency injection for Logo.dev MCP."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, TypedDict

from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

from logodev_mcp.domain import PLAN_GATED_TOOLS, Service

logger = logging.getLogger(__name__)


class LifespanState(TypedDict):
    """Shape of the lifespan context yielded to request handlers."""

    service: Service


@asynccontextmanager
async def server_lifespan(mcp: Any) -> AsyncIterator[dict[str, Any]]:
    """Start the service on startup; stop it on shutdown.

    When plan detection is enabled, probe the secret-key endpoints once and
    hide the tools the configured logo.dev plan does not entitle.
    """
    service = Service()
    await service.start()
    logger.info("Service started")
    await _apply_plan_gating(mcp, service)
    try:
        yield {"service": service}
    finally:
        await service.stop()
        logger.info("Service stopped")


async def _apply_plan_gating(mcp: Any, service: Service) -> None:
    """Disable plan-gated tools the current plan does not allow.

    Fail-open in two phases, so neither a probe failure nor a disable failure
    can break startup or hide a paid tool. The phases are logged under distinct
    events because their failures mean different things: a probe failure is
    usually transient (logo.dev unreachable), whereas a disable failure is a
    wiring bug (a tool name out of sync with what is registered).
    """
    config = service.config
    if config is None or not config.detect_plan:
        return
    try:
        entitlements = await service.probe_entitlements()
    except Exception:
        logger.warning("plan_probe_failed leaving_all_tools_enabled", exc_info=True)
        return
    # probe_entitlements only ever returns PLAN_GATED_TOOLS keys, so the lookup
    # is always safe.
    disable_names = {
        PLAN_GATED_TOOLS[name]
        for name, entitled in entitlements.items()
        if not entitled
    }
    if not disable_names:
        return
    try:
        mcp.disable(names=disable_names)
    except Exception:
        logger.warning(
            "plan_disable_failed tools=%s leaving_all_tools_enabled",
            sorted(disable_names),
            exc_info=True,
        )
        return
    logger.info("plan_gated_tools_disabled tools=%s", sorted(disable_names))


def get_service(ctx: Context = CurrentContext()) -> Service:
    """Resolve the running :class:`Service` from the request context.

    Use as a ``Depends`` default in tool/resource/prompt handlers.

    Raises:
        RuntimeError: If the server lifespan has not run.
    """
    service: Service | None = ctx.lifespan_context.get("service")
    if service is None:
        msg = "Service not initialised — server lifespan has not run"
        raise RuntimeError(msg)
    return service
