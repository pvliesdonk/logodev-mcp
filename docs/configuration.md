# Configuration

Logo.dev MCP is configured via environment variables with the
``LOGODEV_MCP_`` prefix.

## Common variables

See `fastmcp-pvl-core`'s README for the full list of universal
variables (`LOGODEV_MCP_TRANSPORT`, `LOGODEV_MCP_HOST`,
`LOGODEV_MCP_PORT`, `LOGODEV_MCP_HTTP_PATH`,
`LOGODEV_MCP_BASE_URL`, auth vars, etc.).

## Server identity

These two are read by the scaffold's `make_server()` (not by
`ServerConfig`), so an operator can rename an instance or override its
instructions without editing template-owned code:

- `LOGODEV_MCP_SERVER_NAME`: the server name reported to clients and
  by `get_server_info`. Defaults to `logodev-mcp`.
- `LOGODEV_MCP_INSTRUCTIONS`: replaces the default MCP instructions
  text. Unset, the scaffold builds the default (which advertises this
  override).

<!-- DOMAIN-CONFIG-VARS-START -->
## Domain variables

logo.dev needs two API keys. At least one must be set for any API tool to be
registered; tools whose key is absent are hidden.

| Variable | Required | Description |
|---|---|---|
| `LOGODEV_MCP_PUBLISHABLE_KEY` | Conditional | Publishable key (`pk_...`). Enables the `get_logo` tool. |
| `LOGODEV_MCP_SECRET_KEY` | Conditional | Secret key (`sk_...`). Enables `search_brands`, `describe_company`, and `get_brand`. |
| `LOGODEV_MCP_DETECT_PLAN` | Optional (default `true`) | Probe `describe`/`brand` entitlement on startup and hide tools the plan does not allow. Set `false` to register every secret-key tool regardless of plan. |
| `LOGODEV_MCP_STATE_DIR` | Optional (default `/data/state`) | Directory holding the cached plan-detection verdict. |

Get keys from the [logo.dev dashboard](https://www.logo.dev). The publishable
key is sent as a query token to the image CDN; the secret key is sent as a
bearer token to the REST API.

When plan detection is on, `describe_company` and `get_brand` are hidden unless
the configured plan entitles them (`describe` needs any paid plan, `brand` needs
Pro or Enterprise). The verdict is cached for 7 days under the state directory;
a transient probe failure leaves the tools enabled.

## Plans and capabilities

logo.dev gates each tool by **API key type** and by **subscription plan**. A
tool is registered only when its key is set, and (when `LOGODEV_MCP_DETECT_PLAN`
is on) hidden unless your plan entitles it.

| Tool | Key | Minimum logo.dev plan |
|---|---|---|
| `get_logo` | publishable (`pk_…`) | Free |
| `search_brands` | secret (`sk_…`) | Free (with a secret key) |
| `describe_company` | secret (`sk_…`) | Any paid plan |
| `get_brand` | secret (`sk_…`) | Pro or Enterprise |

On a **free** account with a valid secret key, `search_brands` and `get_logo`
work, while `describe_company` and `get_brand` return a `logo.dev:`-prefixed
plan message relayed verbatim from logo.dev (free accounts are told the API is
unavailable and to upgrade; the brand API reports that it needs Pro or
Enterprise). Upgrading to any paid plan unlocks `describe_company`; `get_brand`
needs Pro or Enterprise. See the
[logo.dev pricing page](https://www.logo.dev/pricing) for current tiers.

With plan detection on (the default), the tools your plan does not allow are
hidden at startup rather than failing on call, so a client only ever sees tools
it can run.
<!-- DOMAIN-CONFIG-VARS-END -->
