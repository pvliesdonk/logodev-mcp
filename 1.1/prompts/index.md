# Prompts

MCP prompts are reusable prompt templates exposed to clients. The scaffold ships a minimal set defined in `src/logodev_mcp/prompts.py`; add domain-specific prompts there and document them in this page.

## Example

```
@mcp.prompt()
def summarize(topic: str) -> str:
    """Summarize the given topic in three sentences."""
    return f"Write a three-sentence summary of: {topic}"
```

See the [FastMCP prompts documentation](https://gofastmcp.com/servers/prompts) for the full prompt API.

## Built-in prompts

*None in the scaffold.* Define prompts with `@mcp.prompt(...)` decorators in `src/logodev_mcp/prompts.py` and list them here with their arguments, usage, and example output.
