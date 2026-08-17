# Installation

## From PyPI

```bash
pip install logodev-mcp
```

## From Docker

```bash
docker pull ghcr.io/pvliesdonk/logodev-mcp:latest
```

The `latest` tag is the newest stable release. The rolling `edge` tag tracks every merge to `main` and carries no version identity; see [Image tags](deployment/docker.md#image-tags) for the full list.

## From source

```bash
git clone https://github.com/pvliesdonk/logodev-mcp
cd logodev-mcp
uv sync --all-extras --all-groups
```

<!-- DOMAIN-INSTALL-EXTRA-START -->
<!-- Project-specific notes for installation go here; kept across copier
     update. (E.g. system dependencies, optional extras, custom configuration
     steps.) -->
<!-- DOMAIN-INSTALL-EXTRA-END -->
