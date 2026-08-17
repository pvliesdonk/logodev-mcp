# Logo.dev MCP

<!-- mcp-name: io.github.pvliesdonk/logodev-mcp -->

[![CI](https://github.com/pvliesdonk/logodev-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/pvliesdonk/logodev-mcp/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/pvliesdonk/logodev-mcp/graph/badge.svg)](https://codecov.io/gh/pvliesdonk/logodev-mcp) [![PyPI](https://img.shields.io/pypi/v/logodev-mcp)](https://pypi.org/project/logodev-mcp/) [![Python](https://img.shields.io/pypi/pyversions/logodev-mcp)](https://pypi.org/project/logodev-mcp/) [![License](https://img.shields.io/github/license/pvliesdonk/logodev-mcp)](LICENSE) [![Docker](https://img.shields.io/github/v/release/pvliesdonk/logodev-mcp?label=ghcr.io&logo=docker)](https://github.com/pvliesdonk/logodev-mcp/pkgs/container/logodev-mcp) [![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://pvliesdonk.github.io/logodev-mcp/) [![llms.txt](https://img.shields.io/badge/llms.txt-available-brightgreen)](https://pvliesdonk.github.io/logodev-mcp/llms.txt) [![Template](https://img.shields.io/badge/dynamic/yaml?url=https://raw.githubusercontent.com/pvliesdonk/logodev-mcp/main/.copier-answers.yml&query=%24._commit&label=template)](https://github.com/pvliesdonk/fastmcp-server-template)

Look up company logos and brand data via the logo.dev API.

**[Documentation](https://pvliesdonk.github.io/logodev-mcp/)** | **[Config wizard](https://pvliesdonk.github.io/logodev-mcp/latest/configuration-generator/)** | **[PyPI](https://pypi.org/project/logodev-mcp/)** | **[Docker](https://github.com/pvliesdonk/logodev-mcp/pkgs/container/logodev-mcp)**

## Features

<!-- DOMAIN-START -->
- **Logo retrieval** (`get_logo`) — fetch a company logo as an image plus URL by domain, ticker, ISIN, crypto symbol, or brand name; supports size, format, theme, greyscale, retina, and fallback options. Requires a publishable key (`pk_…`).
- **Brand search** (`search_brands`) — resolve a brand or company name to candidate domains and logo URLs via typeahead or exact-match. Requires a secret key (`sk_…`).
- **Company description** (`describe_company`) — return structured company data (name, description, brand colours, social links) for a domain. Requires a secret key (`sk_…`).
- **Full brand profile** (`get_brand`) — return the complete brand profile (logo, brandmark, banners, colours, description) for a domain — a richer superset of `describe_company`. Requires a secret key (`sk_…`).
- **Graceful degradation** — tools are registered only when the corresponding API key is present; missing-key tools are hidden from the MCP client rather than registered and failing at call time.
<!-- DOMAIN-END -->

## What you can do with it

<!-- DOMAIN-START -->
With this server mounted in an MCP client (Claude, etc.), you can:

- **Fetch a logo** — "Get the logo for stripe.com." Uses `get_logo` (publishable key required).
- **Identify a brand's domain** — "What domain is behind the brand 'Stripe'?" Uses `search_brands` (secret key required).
- **Look up company info** — "What colours does Stripe use in their branding?" Uses `describe_company` (secret key required).
- **Get the full brand kit** — "Show me the complete brand profile for shopify.com." Uses `get_brand` (secret key required).
- **Logo by ticker** — "Fetch the logo for AAPL." Uses `get_logo` with `identifier_type=ticker` (publishable key required).
<!-- DOMAIN-END -->

<!-- ===== TEMPLATE-OWNED SECTIONS BELOW — DO NOT EDIT; CHANGES WILL BE OVERWRITTEN ON COPIER UPDATE ===== -->

## Installation

### From PyPI

```bash
pip install logodev-mcp
```

If you add optional extras via the `PROJECT-EXTRAS-START` / `PROJECT-EXTRAS-END` sentinels in `pyproject.toml`, document them below:

<!-- DOMAIN-START -->
<!-- List optional extras and their purpose here (e.g. `pip install logodev-mcp[embeddings]`). Kept across copier update. -->
<!-- DOMAIN-END -->

### From source

```bash
git clone https://github.com/pvliesdonk/logodev-mcp.git
cd logodev-mcp
uv sync --all-extras --all-groups
```

### Docker

```bash
docker pull ghcr.io/pvliesdonk/logodev-mcp:latest
```

To run the newest merged code instead of the newest release, use the rolling `edge` tag. It is rebuilt on every merge to `main` and carries no version identity. See [Image tags](docs/deployment/docker.md#image-tags) for the full tag list.

```bash
docker pull ghcr.io/pvliesdonk/logodev-mcp:edge
```

A `compose.yml` ships at the repo root as a starting point. Copy `.env.example` to `.env`, edit, and `docker compose up -d`.

To attach a remote Python debugger (development only; the protocol is unauthenticated), see [Remote debugging](docs/deployment/docker.md#remote-debugging).

### Linux packages (.deb / .rpm)

Download `.deb` or `.rpm` packages from the [GitHub Releases](https://github.com/pvliesdonk/logodev-mcp/releases) page. Both install a hardened systemd unit; env configuration is sourced from `/etc/logodev-mcp/env` (copy from the shipped `/etc/logodev-mcp/env.example`).

### Claude Desktop (.mcpb bundle)

Download the `.mcpb` bundle from the [GitHub Releases](https://github.com/pvliesdonk/logodev-mcp/releases) page and double-click to install, or run:

```bash
mcpb install logodev-mcp-<version>.mcpb
```

Claude Desktop prompts for required env vars via a GUI wizard, with no manual JSON editing needed.

For manual Claude Desktop configuration and setup options, see [Claude Desktop deployment](docs/deployment/claude-desktop.md).

## Release channels

Artifacts ship on three channels. Each row lists exactly what that channel publishes.

| Channel | Version identity | Artifacts |
|---|---|---|
| `edge` (rolling) | None; the commit is the identity | Docker image `:edge` rebuilt on every merge to `main`; `.mcpb` bundle as the `mcpb-bundle-edge` workflow artifact; rolling `unstable` docs version. It leaves no git tag, GitHub release, or PyPI entry behind. |
| Pre-release | `vX.Y.Z-rc.N`, cut from a `release/X.Y` branch | GitHub release with wheels, `sdist`, `.mcpb` bundle, and SBOM attached; Docker image under its immutable `vX.Y.Z-rc.N` tag only. Skips PyPI, `.deb`/`.rpm` packages, the plugin marketplace, the MCP registry, and the docs deploy. |
| Stable | `vX.Y.Z` | Everything: PyPI, Docker (version tag plus ordering-aware `latest` / `vX` / `vX.Y`), `.deb`/`.rpm`, GitHub release assets (wheels, `sdist`, `.mcpb` bundle, SBOM), plugin marketplace and MCP registry entries (when the release is the newest stable), versioned docs with an ordering-aware `latest` alias. |

The PyPI split is deliberate: `edge` and pre-release builds never reach PyPI, where every ordinary installer would see them. A pre-release's wheels are still attached to its GitHub release and installable by URL for anyone who opts in. Rolling pointers are ordering-aware, so a patch release cut from an old `release/X.Y` branch never moves `latest`-style tags back to older content. See [Release process](docs/deployment/release-process.md) for the full model.

## Quick start

```bash
logodev-mcp serve                                # stdio transport
logodev-mcp serve --transport http --port 8000   # streamable HTTP
```

For library usage (embedding the domain logic without the MCP transport), import from the `logodev_mcp` package directly. See the project's domain modules under `src/logodev_mcp/` for entry points.

### Server info

The server registers a built-in `get_server_info` tool (via `fastmcp_pvl_core.register_server_info_tool`) so operators can confirm the deployed version with a single MCP call. The default response carries `server_name`, `server_version`, and `core_version`. Servers that talk to a remote upstream wire upstream version reporting inside the `DOMAIN-UPSTREAM-START` / `DOMAIN-UPSTREAM-END` sentinel in `src/logodev_mcp/server.py`; see [`CLAUDE.md`](CLAUDE.md#server-info-tool-get_server_info) for the wiring pattern.

## Configuration

Core environment variables shared across all `fastmcp-pvl-core`-based services:

<!-- GENERATED-ENV-TABLE-CORE-START — generated by scripts/gen_config_surface.py; do not edit -->
| Variable | Default | Description |
|---|---|---|
| `LOGODEV_MCP_KV_STORE_URL` | `file:///data/state` | Persistent-state backend URL shared by every pvl-core subsystem that needs state. `memory://` is in-process and lost on restart; `file:///path` persists on one server; `redis://`, `dynamodb://` and `mongodb://` each need their matching extra. When unset, defaults to `file:///data/state` (the volume family Docker images mount), or to `memory://`; with a warning; on a host where that directory is not usable. |
| `FASTMCP_LOG_LEVEL` | `INFO` | Log level for FastMCP internals and app loggers (DEBUG / INFO / WARNING / ERROR / CRITICAL). The -v CLI flag overrides to DEBUG. |
| `FASTMCP_ENABLE_RICH_LOGGING` | `true` | Set false for plain or structured JSON log output. |
<!-- GENERATED-ENV-TABLE-CORE-END -->

Domain-specific variables go below under [Domain configuration](#domain-configuration).

## Authentication

Callers authenticate via a bearer token or OIDC (mutually exclusive). See the [Authentication guide](docs/guides/authentication.md) for setup, mapped multi-subject tokens, OIDC, and troubleshooting.

## Post-scaffold checklist

After `copier copy` and `gh repo create --push`:

1. **Fill in the DOMAIN blocks** (every section marked with a `DOMAIN` sentinel comment) in this README and in `CLAUDE.md`. The `GENERATED-ENV-TABLE-*` regions are not DOMAIN blocks; the config generator owns them and rewrites them on every run.
2. Configure GitHub secrets (see below).
3. Install dev + docs tooling: `uv sync --all-extras --all-groups`.
4. Install pre-commit hooks: `uv run pre-commit install`.
5. Run the gate locally: `uv run pytest -x -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy src/ tests/`.
6. Push the first commit. CI should be green.

## GitHub secrets

CI workflows reference three repository secrets. Configure them via **Settings → Secrets and variables → Actions** or with `gh secret set`:

| Secret | Used by | How to generate |
|---|---|---|
| `RELEASE_TOKEN` | `release.yml`, `release-notes.yml`, `copier-update.yml`, `renovate.yml`, `bootstrap.yml` | Fine-grained PAT at <https://github.com/settings/personal-access-tokens/new> with `contents: write`, `pull_requests: write`, and `administration: write` (bootstrap applies the repository rulesets + auto-merge). Must belong to a repository admin: the shipped rulesets grant bypass to the admin role, and the release workflow's direct pushes rely on it. Scoped to this repo. |
| `CODECOV_TOKEN` | `ci.yml` | <https://codecov.io>: sign in with GitHub and add the repo. The upload token is on its settings page. |
| `CLAUDE_CODE_OAUTH_TOKEN` | `claude.yml`, `claude-code-review.yml`, `release-notes.yml` | Run `claude setup-token` locally and paste the result. |

```bash
gh secret set RELEASE_TOKEN
gh secret set CODECOV_TOKEN
gh secret set CLAUDE_CODE_OAUTH_TOKEN
```

> Dependency updates are handled by **Renovate** (`renovate.yml`), which reuses
> `RELEASE_TOKEN`. It maintains `uv.lock` and auto-merges patch/minor bumps once
> the `CI Success` check is green; `bootstrap.yml` enables auto-merge and applies
> the repository rulesets (`.github/rulesets/`) on first push. See
> [Repository Protection](docs/deployment/repository-protection.md) for the
> per-branch posture and bypass model. GitHub Actions are updated in the copier
> template and arrive via `copier update`, not per-repo.

`GITHUB_TOKEN` is auto-provided; no action needed.

## Local development

The PR gate (matches CI):

```bash
uv run pytest -x -q                                  # tests
uv run ruff check --fix . && uv run ruff format .    # lint + format
uv run mypy src/ tests/                              # type-check
```

Pre-commit runs a subset of the gate on each commit; see `.pre-commit-config.yaml` for details, or [`CLAUDE.md`](CLAUDE.md) for the full Hard PR Acceptance Gates.

## Troubleshooting

### Moving a scaffolded project

`uv sync` creates `.venv/bin/*` scripts with absolute shebangs pointing at the venv Python. If you move the repo after scaffolding (`mv /old/path /new/path`), `uv run pytest` fails with `ModuleNotFoundError: No module named 'fastmcp'` because the stale shebang resolves to a different interpreter than the venv's site-packages.

**Fix:**

```bash
rm -rf .venv
uv sync --all-extras --all-groups
```

`uv run python -m pytest` also works as a one-shot workaround (bypasses the stale entry-script shim).

### `uv.lock` refresh after `copier update`

When `copier update` introduces new dependencies (such as a new extra added to `pyproject.toml.jinja`), the CI install step runs `uv sync --locked`, which fails against a stale lockfile. Run `uv lock` locally and commit the refreshed `uv.lock` alongside accepting the copier-update PR.

CI installs with `--locked` (and the review workflow with `--frozen`) so no job ever rewrites `uv.lock` in its own workspace: a job that re-locks hides the drift it just repaired, and a dirty workspace breaks any later `git checkout` in the same job. Lockfile drift then shows up as a red install step with a clear message, not as a silent mutation.

## Links

- [Documentation](https://pvliesdonk.github.io/logodev-mcp/)
- [llms.txt](https://pvliesdonk.github.io/logodev-mcp/llms.txt)
- [FastMCP](https://gofastmcp.com)
- [fastmcp-pvl-core](https://pypi.org/project/fastmcp-pvl-core/)

<!-- ===== TEMPLATE-OWNED SECTIONS END ===== -->

## Domain configuration

<<<<<<< before updating
<!-- DOMAIN-START -->
Domain environment variables use the `LOGODEV_MCP_` prefix:

| Variable | Default | Required | Description |
|---|---|---|---|
| `LOGODEV_MCP_PUBLISHABLE_KEY` | — | Conditional | logo.dev publishable key (`pk_…`). Enables the `get_logo` tool. Omit to hide that tool. |
| `LOGODEV_MCP_SECRET_KEY` | — | Conditional | logo.dev secret key (`sk_…`). Enables `search_brands`, `describe_company`, and `get_brand`. Omit to hide those tools. |
| `LOGODEV_MCP_DETECT_PLAN` | `true` | No | Probe `describe`/`brand` entitlement on startup and hide the tools the plan does not allow. Set `false` to skip probing and register every secret-key tool. |
| `LOGODEV_MCP_STATE_DIR` | `/data/state` | No | Directory for the cached plan-detection verdict (`entitlements.json`). |

At least one key must be set for any API tool to be registered. Both keys may be set simultaneously to enable all four tools.

Which tool each logo.dev plan unlocks (`get_logo`/`search_brands` on free, `describe_company` on any paid plan, `get_brand` on Pro/Enterprise) is documented in the [plans and capabilities matrix](docs/configuration.md#plans-and-capabilities).
<!-- DOMAIN-END -->
=======
Domain environment variables use the `LOGODEV_MCP_` prefix:

<!-- GENERATED-ENV-TABLE-DOMAIN-START — generated by scripts/gen_config_surface.py; do not edit -->
| Variable | Default | Required | Description |
|---|---|---|---|
<!-- GENERATED-ENV-TABLE-DOMAIN-END -->

Domain-config fields are composed inside `src/logodev_mcp/config.py` between the `CONFIG-FIELDS-START` / `CONFIG-FIELDS-END` sentinels; env reads go through `fastmcp_pvl_core.env(_ENV_PREFIX, "SUFFIX", default)` so naming stays consistent, and field invariants go in `__post_init__` between the `CONFIG-VALIDATE-START` / `CONFIG-VALIDATE-END` sentinels. Each field's `metadata` `help` and `tags` generate the table above directly, so keep them accurate and complete.
>>>>>>> after updating

## Key design decisions

<!-- DOMAIN-START -->
- **Two-key gating** — `LOGODEV_MCP_PUBLISHABLE_KEY` controls `get_logo`; `LOGODEV_MCP_SECRET_KEY` controls `search_brands`, `describe_company`, and `get_brand`. Tools for a missing key are never registered, not merely guarded at call time.
- **Plan detection hides unentitled tools** — `describe_company` needs a paid plan and `get_brand` needs Pro/Enterprise. logo.dev has no plan endpoint, so on startup the server probes each on `logo.dev` and disables the tool on a `401`/`403`. `search_brands` is never gated; any ambiguous probe result (timeout, `5xx`, `404`, `429`) fails open and keeps the tool enabled. The verdict is cached under `LOGODEV_MCP_STATE_DIR` for 7 days (re-probed on key rotation). Disable with `LOGODEV_MCP_DETECT_PLAN=false`.
- **Domain logic stays FastMCP-free** — `src/logodev_mcp/domain.py` contains the `Service` class and `LogoDevError` with no FastMCP imports; `src/logodev_mcp/tools.py` is the sole FastMCP layer.
- **Errors surface as strings** — `LogoDevError` raised in domain code is caught in each tool wrapper and returned as a plain text message so the MCP client sees a readable error, not a server exception.
- **Logo tool returns URL + image** — `get_logo` returns both the CDN URL (text) and the image bytes (image content block) unless `url_only=True`, in which case only the URL string is returned.
<!-- DOMAIN-END -->
