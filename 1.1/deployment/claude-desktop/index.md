# Claude Desktop

Logo.dev MCP integrates with [Claude Desktop](https://claude.ai/download) via the stdio transport.

## Setup

### 1. Install

From PyPI:

```
pip install logodev-mcp
```

Or with uv (installs `logodev-mcp` as a global command on your PATH):

```
uv tool install logodev-mcp
```

Or download the `.mcpb` bundle from the [GitHub Releases](https://github.com/pvliesdonk/logodev-mcp/releases) page and double-click to install; Claude Desktop prompts for required env vars via a GUI wizard, no manual JSON editing needed.

### 2. Configure Claude Desktop

If you installed via `.mcpb`, skip this step — Claude Desktop was configured automatically by the wizard.

Otherwise, add the server to your Claude Desktop configuration file. The path varies by operating system:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

```
{
  "mcpServers": {
    "logodev-mcp": {
      "command": "logodev-mcp",
      "args": ["serve"],
      "env": {
        "LOGODEV_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

Restart the application to pick up the new configuration. If the server connects successfully, `Logo.dev MCP` tools appear in Claude's tool list. If not, see [Troubleshooting](#troubleshooting) below.

## Configuration examples

## Troubleshooting

### Server not appearing in Claude Desktop

1. Check the config file path is correct for your OS
1. Ensure the JSON is valid (no trailing commas)
1. Restart Claude Desktop completely (quit and reopen)
1. Check Claude Desktop logs for error messages

### "Command not found"

Ensure `logodev-mcp` is on your PATH. If installed in a virtualenv, use the full path to the binary. Replace only the `"command"` value in your existing config — keep `"args"` and `"env"` as-is.

macOS/Linux:

```
{
  "mcpServers": {
    "logodev-mcp": {
      "command": "/Users/me/.venvs/mcp/bin/logodev-mcp",
      "args": ["serve"],
      "env": {
        "LOGODEV_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

Windows (`Scripts\` not `bin\`, `.exe` suffix):

```
{
  "mcpServers": {
    "logodev-mcp": {
      "command": "C:\\Users\\me\\.venvs\\mcp\\Scripts\\logodev-mcp.exe",
      "args": ["serve"],
      "env": {
        "LOGODEV_MCP_READ_ONLY": "true"
      }
    }
  }
}
```
