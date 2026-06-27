# Tools

The tools registered in this server are listed below. See the
[FastMCP tools documentation](https://gofastmcp.com/servers/tools)
for the full tool API.

<!-- DOMAIN-TOOLS-LIST-START -->
Tools are registered only when the API key they need is configured (see
[Configuration](../configuration.md)); a tool whose key is absent is hidden.

## `get_logo`

Fetch a company logo image by domain, stock ticker, ISIN, crypto symbol, or
brand name. Supports `size`, `format`, `theme`, `greyscale`, `retina`, and
`fallback` options, and a `url_only` flag to return just the image URL.
Returns the image URL plus the logo (or only the URL when `url_only`).
**Requires the publishable key** (`LOGODEV_MCP_PUBLISHABLE_KEY`).

## `search_brands`

Resolve a brand or company name to candidate domains (with `suggest` or
`match` strategy). Returns a JSON array of candidates.
**Requires the secret key** (`LOGODEV_MCP_SECRET_KEY`).

## `describe_company`

Return structured company data (name, description, colours, socials) for a
domain, as JSON. **Requires the secret key** and a **paid logo.dev plan**.
Free accounts get a `logo.dev: api not available for free accounts` error.

## `get_brand`

Return the full brand profile (logo, brandmark, banners, colours, and
description) for a domain, as JSON. A richer superset of `describe_company`.
**Requires the secret key** and a **logo.dev Pro or Enterprise plan**. Lower
tiers get a `logo.dev: the brand API is available on Pro and Enterprise plans`
error.

When logo.dev rejects a request for an authentication or plan reason, the tool
relays logo.dev's own message verbatim (prefixed `logo.dev:`). A valid secret
key on too low a plan is a plan problem, not a key problem.
<!-- DOMAIN-TOOLS-LIST-END -->
