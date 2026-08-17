"""Configuration for Logo.dev MCP.

Composes :class:`fastmcp_pvl_core.ServerConfig` via the domain
:class:`ProjectConfig` dataclass — never inherits.

Add domain-specific fields between the CONFIG-FIELDS sentinels, populate
them in ``from_env`` between the CONFIG-FROM-ENV sentinels, and enforce
their invariants in ``__post_init__`` between the CONFIG-VALIDATE
sentinels; copier update preserves all three blocks across template
updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fastmcp_pvl_core import (
    ServerConfig,
    env,
)

_TRUTHY = {"1", "true", "yes", "on"}

_ENV_PREFIX = "LOGODEV_MCP"


@dataclass(frozen=True)
class ProjectConfig:
    """Domain config for Logo.dev MCP.  Compose — don't inherit."""

    server: ServerConfig = field(default_factory=ServerConfig)

    # CONFIG-FIELDS-START — add domain fields below; kept across copier update
    # (uncommenting the Path-typed examples below also requires adding
<<<<<<< before updating
    #  ``from pathlib import Path`` to the imports at the top of this file.)
    # (example)
    # vault_path: Path = Path("/data/vault")
    publishable_key: str | None = None
    secret_key: str | None = None
    # Plan-tier gating: probe describe/brand entitlement on startup and hide the
    # tools the plan does not allow.  ``state_dir`` holds the cached verdict.
    detect_plan: bool = True
    state_dir: Path = Path("/data/state")
=======
    #  ``from pathlib import Path`` to the imports at the top of this file;
    #  ``field`` is already imported from ``dataclasses`` above.)
    # (example — domain env-var discovery reads a field's ``metadata={"help":
    #  ..., "tags": ...}`` to populate the generated .env.example,
    #  packaging/env.example, and config wizard, so give every real field both.)
    # vault_path: Path = field(
    #     default=Path("/data/vault"),
    #     metadata={"help": "Filesystem root of the vault.", "tags": ("storage",)},
    # )
>>>>>>> after updating
    # CONFIG-FIELDS-END

    def __post_init__(self) -> None:
        """Validate composed domain fields.  Raise ``ValueError`` when invalid.

        Runs on EVERY construction path — ``from_env`` and a direct
        ``ProjectConfig(field=...)`` alike.  That is what makes this the right
        home for a field invariant: ``env_float`` / ``env_int`` bounds check
        only the *env-sourced* value, never the default, so a direct
        construction slips past them.  They also cannot express an exclusive
        bound (their ``minimum`` / ``maximum`` are inclusive, so "must be > 0"
        lets ``0`` through) or a cross-field rule (A requires B,
        mutually-exclusive pairs).  All three belong here.

        The dataclass is ``frozen=True``: read fields freely, but plain
        assignment raises.  To *normalise* rather than merely check, use
        ``object.__setattr__(self, "name", value)``.
        """
        # CONFIG-VALIDATE-START — validate domain fields below; kept across copier update
        # (example: an exclusive lower bound, which env_float cannot express
        #  and which also holds for ProjectConfig(http_timeout=0))
        # if self.http_timeout <= 0:
        #     raise ValueError(
        #         f"{_ENV_PREFIX}_HTTP_TIMEOUT must be > 0, got {self.http_timeout}"
        #     )
        #
        # (example: a cross-field invariant, which no per-field bound can
        #  express at all)
        # if self.cache_dir is not None and not self.cache_enabled:
        #     raise ValueError(
        #         f"{_ENV_PREFIX}_CACHE_DIR is set but {_ENV_PREFIX}_CACHE_ENABLED is false"
        #     )
        # CONFIG-VALIDATE-END

    @classmethod
    def from_env(cls) -> ProjectConfig:
        """Load :class:`ProjectConfig` from ``LOGODEV_MCP_*`` env vars."""
        return cls(
            server=ServerConfig.from_env(_ENV_PREFIX),
            # CONFIG-FROM-ENV-START — populate domain fields below; kept across copier update
            # (example)
            # vault_path=Path(env(_ENV_PREFIX, "VAULT_PATH", "/data/vault")),
            publishable_key=env(_ENV_PREFIX, "PUBLISHABLE_KEY"),
            secret_key=env(_ENV_PREFIX, "SECRET_KEY"),
            detect_plan=(env(_ENV_PREFIX, "DETECT_PLAN", "true") or "true")
            .strip()
            .lower()
            in _TRUTHY,
            state_dir=Path(
                env(_ENV_PREFIX, "STATE_DIR", "/data/state") or "/data/state"
            ),
            # CONFIG-FROM-ENV-END
        )
