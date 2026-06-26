# logodev-mcp — Design

**Date:** 2026-06-26
**Status:** Approved

A FastMCP server wrapping the [logo.dev](https://www.logo.dev) API, scaffolded
from [`pvliesdonk/fastmcp-server-template`](https://github.com/pvliesdonk/fastmcp-server-template)
and depending on `fastmcp-pvl-core`, consistent with the rest of the fleet
(kroki-mcp, scholar-mcp, etc.).

## Goal

Let an MCP client / LLM agent look up company logos and brand data: resolve a
name to a domain, fetch a logo image, and retrieve structured company / brand
profiles.

## Architecture

Standard fastmcp-server-template layout, mirroring kroki-mcp:

```
src/logodev_mcp/
  __init__.py
  cli.py
  config.py            # env-driven ServerConfig + load_config()
  mcp_server.py        # create_server(): wires config, lifespan, registrations
  _server_deps.py      # httpx clients in lifespan + Depends() getters
  _server_tools.py     # register_tools(mcp)
  _server_resources.py # register_resources(mcp)  (minimal / template default)
  _server_prompts.py   # register_prompts(mcp)    (minimal / template default)
tests/
  conftest.py
  test_config.py
  test_tools.py
  ...
```

Two `httpx.AsyncClient`s are created in the lifespan and stored in the lifespan
context:

- **`api_client`** → `https://api.logo.dev`, sends `Authorization: Bearer
  {secret_key}`. Backs Search / Describe / Brand.
- **`img_client`** → `https://img.logo.dev`, sends the publishable key as the
  `token` query parameter. Backs the Logo tool.

A client is only created when its key is configured (see degradation). Env
prefix: `LOGODEV_MCP_`.

## Configuration (`config.py`)

| Env var                        | Purpose                                            |
|--------------------------------|----------------------------------------------------|
| `LOGODEV_MCP_PUBLISHABLE_KEY`  | `pk_…` key; enables the **Logo** tool.             |
| `LOGODEV_MCP_SECRET_KEY`       | `sk_…` key; enables **Search / Describe / Brand**. |
| `LOGODEV_MCP_LOG_LEVEL`        | Standard template log-level control.               |

`ServerConfig` carries `publishable_key: str | None`, `secret_key: str | None`,
and the derived booleans `has_publishable` / `has_secret`.

### Graceful degradation

At startup, tools whose backing key is absent are **not registered**; the
server still starts.

- Only publishable key → only `get_logo` is exposed.
- Only secret key → only `search_brands`, `describe_company`, `get_brand`.
- Both keys → all four tools.
- **Neither key** → no API tools registered; a prominent warning is logged
  explaining that at least one key is required.

Each missing key logs a clear, single warning naming the env var and which
tools it gates.

## Tools

### 1. `get_logo` — publishable key, `img.logo.dev`

Fetch a company logo image.

Parameters:

- `identifier` (str, required) — e.g. `nike.com`, `AAPL`, `US0378331005`, `BTC`.
- `identifier_type` (enum, default `domain`) — `domain` | `ticker` | `isin` |
  `crypto` | `name`. Maps to the path: `/{id}`, `/ticker/{id}`, `/isin/{id}`,
  `/crypto/{id}`, `/name/{id}`.
- `size` (int 1–800, default 128).
- `format` (enum, default `png`) — `jpg` | `png` | `webp`.
- `theme` (enum, default `auto`) — `auto` | `light` | `dark`.
- `greyscale` (bool, default `False`).
- `retina` (bool, default `False`).
- `fallback` (enum, default `monogram`) — `monogram` | `404`.
- `url_only` (bool, default `False`) — when `True`, skip the network fetch.

Behaviour: build the `img.logo.dev` URL (publishable key as `token`, plus the
non-default query params). Return **both** the URL (as text) and, unless
`url_only`, the fetched bytes as an MCP `Image`. `fallback=404` lets the caller
detect "no logo" via a `404` instead of receiving a monogram placeholder.

### 2. `search_brands` — secret key, `GET /search`

Resolve a brand/company name to candidate domains.

Parameters: `query` (str, required → `q`), `strategy` (enum, default `suggest`)
— `suggest` | `match`. Returns the JSON array (name, domain, logo URL, …).

### 3. `describe_company` — secret key, `GET /describe/{domain}`

Domain → structured company data (name, description, colors, socials). Returns
the JSON object. Requires a paid plan (surfaced via the 401/403 mapping).

### 4. `get_brand` — secret key, `GET /brand/{domain}`

Domain → full brand profile (logo, brandmark, banners, colors, description) —
a richer superset of Describe. Returns the JSON object. Requires Pro/Enterprise
(surfaced via the 401/403 mapping).

Describe and Brand are kept as **separate tools** (not one tool with a `detail`
flag) because they map to distinct endpoints with distinct plan requirements,
and the agent benefits from picking the cheaper one when it only needs basics.

## Error handling

Each tool validates enums / numeric ranges **locally before any HTTP call**.
HTTP responses are mapped to clear messages (mirrors kroki's status-code
branching):

- `400` → return the API's message (bad identifier / params).
- `401` / `403` → "Authentication or plan-tier problem — check
  `LOGODEV_MCP_SECRET_KEY` and that your plan includes this endpoint."
- `404` → "No result found for `{identifier}`."
- `429` → "logo.dev rate limit reached — retry later."
- Other `>=400` → generic "logo.dev error: {status} {body}".
- `httpx.TimeoutException` → "logo.dev did not respond in time."
- Other `httpx.TransportError` → "Cannot reach logo.dev."

## Testing (TDD)

`respx`-mocked httpx; **no live network**. Enumerated failure modes per tool:

- **Happy path** — correct URL/path/headers built; response parsed/returned.
- **Local validation** — invalid `identifier_type`, out-of-range `size`,
  invalid `format`/`theme`/`strategy`/`fallback` are rejected **before** any
  HTTP call (assert respx route not called).
- **Status mapping** — `401`, `404`, `429`, generic `>=400` each map to the
  expected message.
- **Transport** — timeout and connection error map to their messages.
- `get_logo` specifics — `url_only=True` returns URL and makes **no** request;
  default returns both URL text and an `Image`; publishable key present in the
  `token` query param; non-default params appear in the URL, defaults omitted.

Config / registration tests:

- publishable only → only `get_logo` registered.
- secret only → only the three REST tools registered.
- both → all four.
- neither → none registered + warning logged.

## Out of scope

- **Transaction API** (early access).
- Extra image-CDN paths `exchange` / `index` — `get_logo` covers
  domain/ticker/isin/crypto/name.
- The `api.logo.dev` `/logo/*` record endpoints (Pro/Enterprise) — image needs
  are served by the `img.logo.dev` CDN via `get_logo`.
