# Configuration

Logo.dev MCP is configured via environment variables with the
``LOGODEV_MCP_`` prefix.

## Common variables

See `fastmcp-pvl-core`'s README for the full list of universal
variables (`LOGODEV_MCP_TRANSPORT`, `LOGODEV_MCP_HOST`,
`LOGODEV_MCP_PORT`, `LOGODEV_MCP_HTTP_PATH`,
`LOGODEV_MCP_BASE_URL`, auth vars, etc.).

<!-- DOMAIN-CONFIG-VARS-START -->
## Domain variables

logo.dev needs two API keys. At least one must be set for any API tool to be
registered; tools whose key is absent are hidden.

| Variable | Required | Description |
|---|---|---|
| `LOGODEV_MCP_PUBLISHABLE_KEY` | Conditional | Publishable key (`pk_...`). Enables the `get_logo` tool. |
| `LOGODEV_MCP_SECRET_KEY` | Conditional | Secret key (`sk_...`). Enables `search_brands`, `describe_company`, and `get_brand`. |

Get keys from the [logo.dev dashboard](https://www.logo.dev). The publishable
key is sent as a query token to the image CDN; the secret key is sent as a
bearer token to the REST API.
<!-- DOMAIN-CONFIG-VARS-END -->
