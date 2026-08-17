# Configuration

Logo.dev MCP is configured via environment variables with the
``LOGODEV_MCP_`` prefix.

## Common variables

See `fastmcp-pvl-core`'s README for the full list of universal
variables (`LOGODEV_MCP_TRANSPORT`, `LOGODEV_MCP_HOST`,
`LOGODEV_MCP_PORT`, `LOGODEV_MCP_HTTP_PATH`,
`LOGODEV_MCP_BASE_URL`, auth vars, etc.).

## Server identity

These two let an operator rename an instance or override its
instructions, with no configuration beyond the variable itself:

- `LOGODEV_MCP_SERVER_NAME`: the server name reported to clients and
  by `get_server_info`. Defaults to `logodev-mcp`.
- `LOGODEV_MCP_INSTRUCTIONS`: replaces the default MCP instructions
  text. Unset, the scaffold builds the default (which advertises this
  override).

## Tool visibility

Operators can trim which tools this instance exposes. Each variable takes a
comma-separated list of explicit tool names:

- `LOGODEV_MCP_TOOLS_ALLOW`: expose *only* the listed tools.
- `LOGODEV_MCP_TOOLS_DENY`: hide the listed tools.

Hidden tools disappear from `tools/list` and are rejected on `tools/call`;
resources and prompts are unaffected. Setting both variables, or setting one
to a value with no names in it, is a startup error. A name matching no
registered tool is ignored, but an allowlist that matches nothing logs a
startup `WARNING` since the instance then exposes zero tools. See
`fastmcp-pvl-core`'s README for the full semantics.

## Background tasks

Every Logo.dev MCP instance wires a background-task backend at startup, so
a tool registered with `task=True` works with no extra setup. One variable
picks the backend:

- `LOGODEV_MCP_TASKS_URL`: `memory://` runs tasks in-process and loses
  them on restart; `redis://...` is durable and shared across processes.

Unset, a `redis://` `LOGODEV_MCP_KV_STORE_URL` is reused for tasks as
well, so a single URL configures every stateful subsystem. With neither set,
the backend falls back to `memory://`, which the server logs at startup when
running over HTTP. The queue name comes from the `LOGODEV_MCP` prefix, so
two servers sharing one Redis do not share a queue.

Worker tuning stays on the native `FASTMCP_DOCKET_*` variables
(`FASTMCP_DOCKET_CONCURRENCY` and friends, listed in `.env.example`). Set the
backend through `LOGODEV_MCP_TASKS_URL` rather than
`FASTMCP_DOCKET_URL`: the former wins when both are set, and the server warns
about the disagreement.

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
