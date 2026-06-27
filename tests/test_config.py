from __future__ import annotations

from pathlib import Path

import pytest

from logodev_mcp.config import ProjectConfig


def test_keys_default_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that publishable_key and secret_key default to None when env vars are unset."""
    monkeypatch.delenv("LOGODEV_MCP_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("LOGODEV_MCP_SECRET_KEY", raising=False)
    config = ProjectConfig.from_env()
    assert config.publishable_key is None
    assert config.secret_key is None


def test_keys_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that publishable_key and secret_key are loaded from env vars."""
    monkeypatch.setenv("LOGODEV_MCP_PUBLISHABLE_KEY", "pk_live_abc")
    monkeypatch.setenv("LOGODEV_MCP_SECRET_KEY", "sk_live_xyz")
    config = ProjectConfig.from_env()
    assert config.publishable_key == "pk_live_abc"
    assert config.secret_key == "sk_live_xyz"


def test_detect_plan_defaults_true_and_state_dir() -> None:
    """The dataclass defaults enable plan detection under the Docker state dir."""
    config = ProjectConfig()
    assert config.detect_plan is True
    assert config.state_dir == Path("/data/state")


def test_detect_plan_defaults_true_from_env_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOGODEV_MCP_DETECT_PLAN", raising=False)
    assert ProjectConfig.from_env().detect_plan is True


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("false", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("true", True),
        ("1", True),
        ("YES", True),
    ],
)
def test_detect_plan_parses_env(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    monkeypatch.setenv("LOGODEV_MCP_DETECT_PLAN", value)
    assert ProjectConfig.from_env().detect_plan is expected


def test_state_dir_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGODEV_MCP_STATE_DIR", "/tmp/logodev-state")
    assert ProjectConfig.from_env().state_dir == Path("/tmp/logodev-state")
