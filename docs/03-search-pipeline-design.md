# Search Pipeline Design

## 1. Goal

Design a reusable search and retrieval subgraph that:

- calls multiple search channels and internal indexes
- normalizes heterogeneous results
- classifies and filters by result attributes
- preserves publish time and source metadata
- supports cache reuse
- provides stable downstream artifacts for later workflows

## 2. Core Principle

Search channels should not be hard-coded as domestic versus international workflows.

Instead, the system should:

1. retrieve from multiple sources
2. normalize result structure
3. enrich source metadata
4. resolve time attributes
5. classify by source and content properties
6. filter according to workflow policy

This is more flexible and much easier to extend.

## 3. Standard Search Subgraph

Recommended reusable subgraph:

```text
search_fanout
  -> provider_search_a
  -> provider_search_b
  -> provider_search_c
  -> es_recall
  -> merge_raw_hits
  -> normalize_hits
  -> enrich_source_metadata
  -> resolve_time_fields
  -> fetch_documents
  -> deduplicate_documents
  -> classify_source
  -> filter_by_policy
  -> build_retrieval_bundle
```

This subgraph should be reused in multiple business workflows.

## 4. Node Responsibilities

## 4.1 Search Provider Nodes

Examples:

- `provider_search_news_api`
- `provider_search_web_api`
- `provider_search_social_api`
- `provider_search_archive`
- `es_recall`

Responsibilities:

- call one provider
- persist raw provider response
- transform raw result into provider-level hit list
- emit raw hit artifact

These nodes should not perform deep classification or downstream filtering logic.

## 4.2 Merge Raw Hits

Responsibilities:

- combine hit lists from all source providers
- preserve provider origin
- preserve per-provider score and rank
- emit merged raw artifact

## 4.3 Normalize Hits

Responsibilities:

- convert merged hits into standard schema
- align field names
- record missing fields explicitly
- preserve raw provider payload reference

## 4.4 Enrich Source Metadata

Responsibilities:

- map domain to source dictionary
- infer source type
- infer publisher type
- infer region or country hints
- attach credibility baseline

Preferred data sources:

- curated source registry
- provider metadata
- domain rules
- content heuristics
- LLM fallback only when needed

## 4.5 Resolve Time Fields

Responsibilities:

- normalize publish time strings
- convert to UTC
- preserve original timestamp text
- identify fetched time and indexed time
- optionally extract event time later from document body

Time fields should not be collapsed into a single column.

## 4.6 Fetch Documents

Responsibilities:

- fetch full document content where needed
- store raw HTML or raw body
- produce cleaned text
- capture fetch status and fetch timestamp

This node can be skipped if downstream only needs snippets.

## 4.7 Deduplicate Documents

Responsibilities:

- deduplicate by canonical URL, title, publish time, and content hash
- group near-duplicates
- preserve duplicate-to-primary mapping

## 4.8 Classify Source

Responsibilities:

- classify by region
- classify by source type
- classify by language
- classify by official versus unofficial
- optionally classify by topic family

This step should output structured labels, not prose.

## 4.9 Filter by Policy

Responsibilities:

- apply workflow-specific criteria
- keep only relevant result subsets
- preserve filtered-out reasoning metadata

Examples:

- latest-only mode
- official-source-priority mode
- include-foreign-as-supplement mode
- last-7-days-only mode

## 4.10 Build Retrieval Bundle

Responsibilities:

- package the selected evidence set for downstream steps
- include source summaries, document references, and distribution stats
- emit a stable artifact that later workflows can reuse

## 5. Search Result Classification Strategy

Avoid classifying sources only with an LLM. Use layered classification.

### 5.1 Source Registry

Maintain a curated registry keyed by:

- source domain
- source name

Fields may include:

- country
- region
- language
- source type
- publisher type
- credibility tier
- official flag

### 5.2 Provider Metadata

If search provider returns attributes such as language or country, preserve them.

### 5.3 Rule-Based Heuristics

Useful signals:

- domain suffix
- page metadata
- language detection
- URL patterns

### 5.4 LLM Fallback

Only use LLM for unresolved or ambiguous cases.

## 6. Time Model

Search results and documents should preserve multiple time fields.

### 6.1 Required Time Fields

- `published_at_original`
- `published_at_utc`
- `discovered_at_utc`
- `fetched_at_utc`
- `indexed_at_utc`

### 6.2 Optional Event Time Fields

For timeline use cases, it is often necessary to extract:

- `event_time_start`
- `event_time_end`

Important distinction:

- article publish time is not the same as event occurrence time

## 7. Standard Hit Schema

Recommended normalized search hit shape:

```json
{
  "hit_id": "hit_xxx",
  "provider": "search_api_a",
  "query": "keyword",
  "source_name": "Reuters",
  "source_domain": "reuters.com",
  "source_url": "https://example.com/path",
  "title": "headline",
  "snippet": "summary text",
  "language": "en",
  "country_hint": "US",
  "region_hint": "overseas",
  "source_type": "news",
  "publisher_type": "media",
  "published_at_original": "Fri, 09 May 2026 10:12:00 GMT",
  "published_at_utc": "2026-05-09T10:12:00Z",
  "discovered_at_utc": "2026-05-09T10:13:21Z",
  "raw_score": 0.82,
  "normalized_score": 0.75,
  "raw_payload_ref": "obj://..."
}
```

## 8. Search Cache Strategy

Search should support layered cache instead of one global cache.

### 8.1 Raw Search Hit Cache

Cache key inputs:

- provider
- query
- time window
- provider params

### 8.2 Normalized Hit Cache

Cache based on:

- raw hit artifact hash
- normalization version

### 8.3 Source Classification Cache

Cache based on:

- source domain
- title
- snippet
- metadata hash

### 8.4 Document Parse Cache

Cache based on:

- canonical URL
- content hash

### 8.5 Retrieval Bundle Cache

Cache based on:

- filtered result set hash
- policy version

## 9. Search Outputs for Downstream Use

The search subgraph should emit at least these artifacts:

- raw hit bundle
- normalized hit bundle
- fetched document bundle
- deduplicated document bundle
- classified document bundle
- filtered retrieval bundle

The filtered retrieval bundle is the most useful downstream reuse boundary.

## 10. Relationship to ES

ES can play two different roles:

### 10.1 ES as Business Data Source

The workflow queries ES as one search channel among others.

### 10.2 ES as Platform Infrastructure

The platform stores indexed documents to support its own retrieval needs.

Do not mix these two roles conceptually.

## 11. Provider Strategy Based on Current Research

The repository already contains provider research notes under `docs/search_api/`.

Those notes should be treated as platform input for provider strategy, not as standalone implementation notes.

Current referenced providers include:

- Exa
- Firecrawl
- Tavily
- TinyFish
- Grok web search and X search

## 11.1 Provider Role Categories

Search-related providers in this platform should be grouped by role rather than by vendor.

Recommended role categories:

- `search_only`
- `search_with_inline_content`
- `fetch_only`
- `structured_extract`
- `site_crawl`
- `model_embedded_search`

This avoids coupling workflow design to specific vendors.

## 11.2 Recommended Role Mapping

### Exa

Recommended roles:

- `search_with_inline_content`
- `fetch_only`

Key strengths from current notes:

- search can directly return text, highlights, and summary
- contents API supports freshness control through `maxAgeHours`
- cost is returned directly in the response
- useful for research-oriented retrieval and high-quality result selection

Recommended use:

- high-quality search for article and research retrieval
- search-plus-content workflows where one provider call can reduce round trips
- freshness-aware content retrieval

Important limits:

- no standalone public crawl endpoint
- some categories have parameter restrictions
- per-URL content fetch status must still be checked

### Firecrawl

Recommended roles:

- `search_with_inline_content`
- `fetch_only`
- `structured_extract`
- `site_crawl`

Key strengths from current notes:

- strongest coverage across search, scrape, extract, and crawl
- good fit for JS-heavy pages
- supports asynchronous crawl workflows
- supports structure-oriented extraction

Recommended use:

- full-page fetching
- site ingestion
- crawl-based corpus building
- difficult pages that need browser-grade handling

Important limits:

- more operational complexity than lightweight search-only providers
- crawl should be treated as explicit asynchronous work, not a cheap fetch substitute

### Tavily

Recommended roles:

- `search_with_inline_content`
- `fetch_only`
- `site_crawl`

Key strengths from current notes:

- unified AI-friendly API family
- search, extract, crawl, and map fit naturally together
- query-aware extraction is useful when only relevant page chunks are needed

Recommended use:

- fast AI-oriented retrieval
- batch URL extraction
- focused crawl when you want API consistency

Important limits:

- cost semantics differ by endpoint and extraction depth
- crawl with instructions changes cost behavior

### TinyFish

Recommended roles:

- `search_only`
- `fetch_only`

Key strengths from current notes:

- clean split between search and fetch
- fetch uses real browser rendering
- search and fetch are not credit-based in the same style as some other providers

Recommended use:

- lightweight URL discovery
- browser-backed content fetch for dynamic pages
- provider diversity as a fallback fetch channel

Important limits:

- no standalone public crawl endpoint in current docs
- batch fetch limits and per-URL errors must be handled explicitly

### Grok Search

Recommended roles:

- `model_embedded_search`

Key strengths from current notes:

- search is exposed as a model tool rather than a standalone search endpoint
- supports web search and X search
- returns citations
- useful when answer generation and search are tightly coupled

Recommended use:

- search-enhanced answer nodes
- X platform retrieval when needed
- workflows that want inline citations from the model execution itself

Important limits:

- not a substitute for independent search-hit persistence
- should not replace the general multi-provider retrieval layer
- should be treated as an LLM tool path, not a standard search provider node

## 11.3 Platform Integration Guidance

These providers should not all be wired the same way.

Recommended platform-level integration pattern:

- search providers expose a normalized hit contract
- fetch providers expose a normalized document contract
- crawl providers expose asynchronous crawl jobs and crawl artifacts
- model-embedded search is surfaced through the LLM routing layer

In practice:

- Exa, Tavily, Firecrawl search endpoints map to `search_executor`
- Exa contents, Firecrawl scrape, Tavily extract, TinyFish fetch map to `document_fetch_executor`
- Firecrawl crawl and Tavily crawl map to `crawl_executor`
- Grok web search and X search map to LLM tool-enabled invocation policies

## 11.4 Provider Selection Policy

The workflow engine should support selecting providers based on capability and workload type.

Example policy:

- fast evidence discovery: Tavily or Exa search
- high-quality search plus inline content: Exa search with contents
- difficult dynamic page fetch: Firecrawl scrape or TinyFish fetch
- structured page extraction: Firecrawl extract
- large site crawl: Firecrawl crawl
- answer-with-citations in one reasoning step: Grok tool-enabled LLM step

## 11.5 Provider-Specific Metadata to Preserve

The current provider notes suggest preserving more than generic search fields.

The platform should preserve, when available:

- provider request ID
- per-provider cost field
- per-provider result rank
- per-provider result score
- provider-specific content freshness parameters
- per-item success or error status for batch fetch endpoints
- citations for model-embedded search flows

These should be persisted in invocation metadata and artifact metadata rather than discarded during normalization.

## 11.6 Search Versus Fetch Versus Crawl

Do not flatten all retrieval behavior into one generic "search" node.

Recommended distinctions:

- `search_*` nodes discover candidate URLs or snippets
- `fetch_*` nodes retrieve full content for known URLs
- `crawl_*` nodes perform multi-page site discovery and extraction
- `extract_*` nodes derive structured content from fetched or crawled pages

This separation is required for:

- accurate caching
- cost control
- better retries
- downstream reuse

## 12. Recommended Provider Matrix for the First Version

For the first implementation phase, a practical initial matrix would be:

- primary discovery provider: Exa or Tavily
- primary fetch provider: Firecrawl or TinyFish
- optional archive recall: Elasticsearch
- optional answer-centric search: Grok with web search tool

This keeps the initial provider matrix broad enough to be useful but limited enough to implement and test.
