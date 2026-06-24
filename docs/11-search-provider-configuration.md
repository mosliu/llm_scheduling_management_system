# Search Provider Configuration

## 1. Purpose

This document records how to enable and operate the configurable search channels used by `/briefing`, the provider catalog, and workflow search fanout.

Current provider configuration is loaded from:

```text
config/search.toml
```

If that file does not exist, the application falls back to:

```text
config/search.example.toml
```

Real keys must stay in `config/search.toml`. Do not put real API keys in `config/search.example.toml`, docs, tests, or committed code.

## 2. Runtime Behavior

Search providers are declared under `[[providers]]`.

Important fields:

| Field | Meaning |
| --- | --- |
| `name` | Internal provider name selected by UI or workflow options. |
| `vendor` | Adapter vendor used by `SearchProviderFactory`. |
| `base_url` | Provider API base URL. |
| `api_key` | Provider API key. Keep this local. |
| `enabled` | Whether the provider appears as an available channel. |
| `simulate` | Whether to return simulated results instead of calling the real API. |
| `default_options` | Provider-specific request options merged into each search request. |

The `/briefing` page reads `/api/v1/provider-catalog/search` and shows enabled search providers. When the page starts with no manual selection, it selects all enabled providers.

For real provider testing:

1. Set `enabled = true`.
2. Set the real `api_key` when the provider requires one.
3. Set `simulate = false`.
4. Restart or reload the API process.
5. Refresh `/briefing`.

Console/provider tests do not treat `simulate = true` as success. If a provider is in simulation mode, the test endpoint returns an explicit error instead of virtual search hits.

## 3. Bocha Search

Provider name:

```text
bocha_search
```

Vendor:

```text
bocha
```

Adapter endpoint:

```http
POST https://api.bochaai.com/v1/web-search
```

Authentication:

```http
Authorization: Bearer <BOCHA_API_KEY>
```

Configured request shape:

```json
{
  "query": "search keywords",
  "count": 20,
  "freshness": "noLimit",
  "summary": true
}
```

Local configuration:

```toml
[[providers]]
name = "bocha_search"
provider_type = "search_with_inline_content"
vendor = "bocha"
base_url = "https://api.bochaai.com"
api_key = "replace-me"
timeout_seconds = 180
enabled = true
simulate = true

[providers.extra_headers]

[providers.default_options]
freshness = "noLimit"
summary = true
```

To enable real Bocha search:

```toml
api_key = "your-bocha-api-key"
enabled = true
simulate = false
```

Bocha key source:

- Bocha Open Platform: `https://open.bochaai.com/`

Parsed response fields:

| Bocha field | Internal field |
| --- | --- |
| `data.webPages.value[].name` | `SearchHit.title` |
| `data.webPages.value[].url` | `SearchHit.url` |
| `data.webPages.value[].summary` or `snippet` | `SearchHit.snippet` |
| `data.webPages.value[].datePublished` | `SearchHit.published_at_utc` |
| `data.webPages.totalEstimatedMatches` | `request_metadata.total_estimated_matches` |

## 4. Firecrawl Search

The user-facing wording may say "Firecrawler", but the project adapter and official service name are Firecrawl. Use the provider name `firecrawl_search` and vendor `firecrawl`.

Provider name:

```text
firecrawl_search
```

Vendor:

```text
firecrawl
```

Adapter endpoint:

```http
POST https://api.firecrawl.dev/v2/search
```

Authentication:

```http
Authorization: Bearer <FIRECRAWL_API_KEY>
```

The Firecrawl search adapter also supports keyless endpoints. If `api_key` is empty or left as `replace-me`, the request is sent without an `Authorization` header.

Configured request shape:

```json
{
  "query": "search keywords",
  "limit": 20,
  "sources": ["web"],
  "scrapeOptions": {
    "formats": ["markdown"],
    "onlyMainContent": true
  }
}
```

Local configuration:

```toml
[[providers]]
name = "firecrawl_search"
provider_type = "search_with_inline_content"
vendor = "firecrawl"
base_url = "https://api.firecrawl.dev"
api_key = "replace-me"
timeout_seconds = 180
enabled = true
simulate = true

[providers.extra_headers]

[providers.default_options]
sources = ["web"]

[providers.default_options.scrapeOptions]
formats = ["markdown"]
onlyMainContent = true
```

To enable real Firecrawl search:

```toml
api_key = ""
enabled = true
simulate = false
```

If your Firecrawl endpoint requires a key, use:

```toml
api_key = "your-firecrawl-api-key"
enabled = true
simulate = false
```

Firecrawl key source:

- Firecrawl dashboard/API docs: `https://docs.firecrawl.dev/`

Parsed response sections:

| Firecrawl response section | Internal handling |
| --- | --- |
| `data.web[]` | Parsed as normal web search hits. |
| `data.news[]` | Parsed as news hits when returned. |
| `data.images[]` | Parsed as image hits when returned. |
| `metadata.statusCode` | Stored under hit metadata. |
| top-level `creditsUsed` | Stored under bundle request metadata. |

When Firecrawl search returns inline content, such as `markdown`, the search hit stores it as `inline_content_text`. The `fetch_documents` step then converts that hit directly into a document and skips the separate fetch provider call for that URL.

## 5. Default Provider Policy

The policy block controls providers used when a workflow does not explicitly pass `search_provider_names`:

```toml
[policy]
default_search_providers = [
    "tavily_search",
    "grok_search",
    "gpt_search",
    "exa_search",
]
```

To include Bocha or Firecrawl in implicit default workflow searches, add their provider names:

```toml
default_search_providers = [
    "tavily_search",
    "grok_search",
    "gpt_search",
    "exa_search",
    "bocha_search",
    "firecrawl_search",
]
```

Do this only after the real key is configured and `simulate = false`, unless simulated hits are acceptable for local development.

## 6. Verification

List configured search providers:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/provider-catalog/search
```

Test Bocha:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/provider-catalog/search/test `
  -ContentType 'application/json' `
  -Body '{"provider_name":"bocha_search","query":"sanity check","limit":3}'
```

Test Firecrawl:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/provider-catalog/search/test `
  -ContentType 'application/json' `
  -Body '{"provider_name":"firecrawl_search","query":"sanity check","limit":3}'
```

Run adapter tests:

```powershell
uv run pytest tests/test_provider_adapters.py tests/test_provider_factory.py tests/test_provider_catalog_api.py tests/test_config_loader.py -q
```

## 7. Operational Notes

- `config/search.toml` is gitignored and is the correct place for real keys.
- `config/search.example.toml` should only contain placeholders and safe defaults.
- Keep `simulate = true` while preparing a provider block without a real key.
- Console/provider tests return an error for `simulate = true`; they do not return virtual search hits.
- Set `simulate = false` before validating real provider connectivity.
- Restart the API process after changing local config when running a long-lived server.
- `/briefing` uses task-level `search_provider_names`, so selected channels on the page override the policy default list.
