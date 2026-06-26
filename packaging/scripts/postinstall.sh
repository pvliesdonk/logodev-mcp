#!/bin/bash
# Post-install script: create venv and install logodev-mcp from PyPI.
set -eu

INSTALL_DIR="/opt/logodev-mcp"
VENV_DIR="${INSTALL_DIR}/venv"
SERVICE_USER="logodev-mcp"

# Determine package version — set by nfpm via VERSION env var, or read
# from the installed package metadata as fallback.
PKG_VERSION="${VERSION:-}"

# Create install directory
mkdir -p "$INSTALL_DIR"

# Create or update the virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# Upgrade pip and install the package
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip

if [ -n "$PKG_VERSION" ]; then
    "${VENV_DIR}/bin/pip" install --quiet "logodev-mcp==${PKG_VERSION}"
else
    "${VENV_DIR}/bin/pip" install --quiet "logodev-mcp"
fi

# Ensure config directory exists
mkdir -p /etc/logodev-mcp

# Copy example env if no config exists yet
if [ ! -f /etc/logodev-mcp/env ]; then
    if [ -f /etc/logodev-mcp/env.example ]; then
        cp /etc/logodev-mcp/env.example /etc/logodev-mcp/env
    fi
fi

# Restrict env file permissions — it may contain secrets (tokens, API keys).
if [ -f /etc/logodev-mcp/env ]; then
    chmod 600 /etc/logodev-mcp/env
fi

# Reload systemd to pick up the unit file.
# Note: the service is intentionally NOT enabled here — start-on-boot requires
# explicit opt-in by the administrator via: systemctl enable logodev-mcp
systemctl daemon-reload 2>/dev/null || true

# On upgrade, restart the service if it's already running so the new version is loaded.
if systemctl is-active --quiet logodev-mcp 2>/dev/null; then
    systemctl restart logodev-mcp
fi
