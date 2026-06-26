from __future__ import annotations

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
