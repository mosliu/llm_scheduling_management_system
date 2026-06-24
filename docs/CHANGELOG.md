# Project Changelog

## 2026-06-24

### Service Operations

- Stopped the local API service that was listening on `127.0.0.1:8000`.
- The stopped process was `python.exe scripts/dev_run_api.py`.

### Briefing UI

- Added an explicit search result limit control on `/briefing`.
- The default search result limit is `20`.
- Added completed-step metrics for parallel search progress.
- Search progress now records per-provider result counts after search fanout completes.
- Fetch progress now records the fetch method, fetch call count, fetched document count, inline document count, and skipped fetch count.

### Search Providers

- Added Bocha Web Search as a configured search provider.
- Bocha uses `POST https://api.bochaai.com/v1/web-search`.
- Bocha requests use `Authorization: Bearer <BOCHA_API_KEY>`.
- Bocha responses are normalized from `data.webPages.value[]` into standard search hits.
- Added Firecrawl search as a visible local search channel through `firecrawl_search`.
- Firecrawl search uses `POST https://api.firecrawl.dev/v2/search`.
- Firecrawl search can run without an API key when the configured endpoint allows keyless access.
- Firecrawl search omits the `Authorization` header when no key is configured.
- Firecrawl search drops blank `Authorization` headers such as `Bearer ` from user-provided extra headers.
- Firecrawl search extracts inline content from fields such as `markdown`, `content`, `raw_content`, `text`, and `html`.

### Provider Testing

- Console/provider search tests no longer return virtual search results.
- Providers configured with `simulate = true` now return an explicit test error instead of simulated hits.
- Providers that require keys now fail fast when the key is missing or left as a placeholder.
- Search provider HTTP responses with status `4xx` or `5xx` now surface as explicit errors instead of being parsed as successful empty results.

### Fetch Pipeline

- Firecrawl search results that include inline content now bypass the separate fetch provider call.
- Inline search content is converted directly into a fetched document during `fetch_documents`.
- Inline documents are marked with:
  - `inline_content = true`
  - `fetch_skipped = true`
- The fetch artifact now reports:
  - `inline_document_count`
  - `fetch_skipped_count`

### Configuration

- Added Bocha provider examples to `config/search.example.toml`.
- Added Firecrawl search and Bocha search blocks to local `config/search.toml`.
- Local `firecrawl_search` is configured with `api_key = ""` and `simulate = false`.
- Local `bocha_search` is configured with `simulate = false`; it requires a real key before testing.

### Documentation

- Added `docs/11-search-provider-configuration.md`.
- Documented Bocha key configuration.
- Documented Firecrawl keyless search behavior.
- Documented Console/provider test behavior for simulated providers.
- Documented Firecrawl inline-content handling and fetch skipping.

### Validation

- Ran provider, catalog, config, and targeted task tests:

```powershell
uv run pytest tests/test_provider_adapters.py tests/test_provider_factory.py tests/test_provider_catalog_api.py tests/test_config_loader.py tests/test_tasks_api.py::test_fetch_documents_uses_inline_content_without_fetching tests/test_tasks_api.py::test_fetch_documents_deduplicates_documents_by_canonical_url -q
```

- Result: `33 passed`.

- Ran full task API tests:

```powershell
uv run pytest tests/test_tasks_api.py -q
```

- Result: `54 passed`.

- Ran the final Firecrawl header regression test set:

```powershell
uv run pytest tests/test_provider_adapters.py tests/test_tasks_api.py::test_fetch_documents_uses_inline_content_without_fetching tests/test_provider_catalog_api.py::test_provider_catalog_search_test_endpoint_rejects_simulated_provider -q
```

- Result: `23 passed`.

### Notes

- The project worktree already contained unrelated uncommitted changes before these updates.
- Real API keys must remain in local ignored configuration files such as `config/search.toml`.
- Do not commit real provider keys to checked-in examples, docs, tests, or source code.
