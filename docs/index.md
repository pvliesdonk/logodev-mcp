# Logo.dev MCP

Look up company logos and brand data via the logo.dev API.

## Getting started

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Tools](tools/index.md)

<!-- DOMAIN-INDEX-FEATURES-START -->
## Features

- **Logo retrieval** (`get_logo`): fetch a company logo by domain, ticker,
  ISIN, crypto symbol, or brand name. Requires the publishable key.
- **Brand search** (`search_brands`): resolve a name to candidate domains.
  Requires the secret key.
- **Company data** (`describe_company`): structured company info for a domain.
  Requires the secret key.
- **Brand profile** (`get_brand`): the full brand kit for a domain. Requires
  the secret key.
- **Graceful degradation**: each tool is registered only when its API key is
  configured, so missing-key tools are hidden.
<!-- DOMAIN-INDEX-FEATURES-END -->

<!-- DOMAIN-INDEX-USE-CASES-START -->
## What you can do

- "Get the logo for a given company domain." (`get_logo`)
- "What domain is behind this brand name?" (`search_brands`)
- "What brand colors does this company use?" (`describe_company`)
- "Show me the full brand profile for this domain." (`get_brand`)
<!-- DOMAIN-INDEX-USE-CASES-END -->
