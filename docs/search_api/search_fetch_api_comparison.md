# Search / Fetch API 对比整理

- 核对日期：2026-05-07
- 范围：只整理 4 家官方公开文档中和 `search`、`fetch/scrape/extract`、`crawl` 最相关的 HTTP API；不展开 SDK 封装细节。
- 厂商：Tavily、Exa、Firecrawl、TinyFish

## 1. 结论先看

| 厂商 | 基础定位 | Search | Fetch / Extract | Crawl | 适合的场景 |
| --- | --- | --- | --- | --- | --- |
| Tavily | 面向 AI/Agent 的搜索 API | 强，且可直接带答案与清洗内容 | `POST /extract` | `POST /crawl` | 想把“搜索 + 内容提取 + 站点抓取”放在一套 API 里 |
| Exa | 搜索优先，内容获取能力紧跟搜索 | 很强，`search` 可直接内联 `contents` | `POST /contents` | 无独立公开 crawl API | 先搜再读正文、研究类检索、需要结果质量和内容摘要 |
| Firecrawl | 采集能力最全，搜索只是其中一层 | 有，且可直接把结果 scrape 成正文 | `POST /v2/scrape`、`POST /v2/extract` | `POST /v2/crawl` | JS-heavy 页面、整站抓取、结构化抽取、异步大规模采集 |
| TinyFish | Search 与 Fetch 分工明确 | 有，且接口最轻 | `POST https://api.fetch.tinyfish.ai` | 无公开 standalone crawl | 想要轻量搜索 + 真实浏览器渲染抓取，且 Search/Fetch 不按 credits 计费 |

## 2. 总览对比

| 厂商 | Base URL / Canonical Endpoint | 鉴权 | Search 接口 | Fetch / Scrape 接口 | Crawl 现状 |
| --- | --- | --- | --- | --- | --- |
| Tavily | `https://api.tavily.com` | `Authorization: Bearer tvly-...` | `POST /search` | `POST /extract` | `POST /crawl` |
| Exa | `https://api.exa.ai` | `x-api-key` 或 `Authorization: Bearer ...` | `POST /search` | `POST /contents` | 文档里没有独立公开 crawl endpoint；最接近的是 `contents` 的 `livecrawl/maxAgeHours + subpages` |
| Firecrawl | `https://api.firecrawl.dev` | `Authorization: Bearer fc-...` | `POST /v2/search` | `POST /v2/scrape`，结构化抽取用 `POST /v2/extract` | `POST /v2/crawl`，异步任务式 |
| TinyFish | Search: `GET https://api.search.tinyfish.ai`；Fetch: `POST https://api.fetch.tinyfish.ai` | `X-API-Key` | `GET https://api.search.tinyfish.ai` | `POST https://api.fetch.tinyfish.ai` | 无公开 standalone crawl；更复杂网页流程转到 Agent / Browser API |

## 3. Tavily

### 3.1 Search

- 接口：`POST https://api.tavily.com/search`
- 典型特点：
  - 面向 AI 检索设计，Search 本身就能返回排序结果、可选答案、可选清洗后的正文。
  - 支持 `topic` 区分 `general`、`news`、`finance`。
  - 支持时间过滤：`time_range`、`start_date`、`end_date`。
  - 支持域名过滤：`include_domains`、`exclude_domains`。
  - 支持 `auto_parameters`，可自动决定一部分搜索策略。
- 常用参数：
  - `query`：必填。
  - `search_depth`：文档中可见 `basic`、`fast`、`advanced`。`advanced` 更偏高相关性，成本更高。
  - `max_results`：返回结果数，文档范围到 20。
  - `include_answer`：可直接返回 LLM 生成的答案。
  - `include_raw_content`：可直接带回清洗后的页面内容，支持 markdown / text 语义。
  - `include_images`、`include_image_descriptions`、`include_favicon`。
  - `country`：按国家增强结果倾向。
  - `exact_match`：对引号短语做更严格匹配。
  - `safe_search`：文档标明为 Enterprise 能力。
- 返回重点：
  - `query`
  - `results[]`
  - 可选 `answer`
  - 可选 `images`
  - `response_time`
  - 可选 `auto_parameters`
  - 可选 `usage`
  - `request_id`

### 3.2 Extract

- 接口：`POST https://api.tavily.com/extract`
- 作用：对给定 URL 列表做正文提取，属于 Tavily 体系下最接近“fetch”的接口。
- 常用参数：
  - `urls`：支持单个 URL 或 URL 数组。
  - `query`：可选，用来对抽取后的 chunk 重新排序。
  - `chunks_per_source`：`1-5`，只在带 `query` 时生效。
  - `extract_depth`：`basic` / `advanced`。
  - `format`：`markdown` / `text`。
  - `include_images`
  - `include_favicon`
  - `timeout`
  - `include_usage`
- 返回重点：
  - `results[]`
  - `failed_results[]`
  - `response_time`
  - 可选 `usage`
  - `request_id`

### 3.3 Crawl

- 接口：`POST https://api.tavily.com/crawl`
- 作用：从根 URL 出发做站点级遍历，并直接返回每一页的抽取结果。
- 常用参数：
  - `url`：必填。
  - `instructions`：自然语言告诉 crawler 要找什么。
  - `max_depth`：文档范围 `1-5`。
  - `max_breadth`：每层跟进链接上限。
  - `limit`：总抓取页数上限，默认 50。
  - `select_paths` / `exclude_paths`
  - `select_domains` / `exclude_domains`
  - `allow_external`
  - `extract_depth`
  - `format`：`markdown` / `text`
  - `include_images`
  - `include_favicon`
  - `timeout`
  - `include_usage`
- 返回重点：
  - `base_url`
  - `results[]`
  - `response_time`
  - 可选 `usage`
  - `request_id`

### 3.4 计费和使用感知

- Search：
  - `basic` 每次 1 credit。
  - `advanced` 每次 2 credits。
- Extract：
  - `basic` 每 5 个成功 URL 抽取消耗 1 credit。
  - `advanced` 每 5 个成功 URL 抽取消耗 2 credits。
- Crawl：
  - 文档明确说明总成本 = `mapping cost + extraction cost`。
  - 如果带 `instructions`，mapping 部分会比普通 map 更贵。

### 3.5 适用判断

- 如果你想要“一次请求直接拿搜索结果 + 摘要/答案 + 正文片段”，Tavily 很顺手。
- 如果你还要做整站文档入库，`/crawl` 也比较直接。

## 4. Exa

### 4.1 Search

- 接口：`POST https://api.exa.ai/search`
- 核心特点：
  - Search 可以直接带 `contents` 对象，所以很多场景下不用第二次 fetch。
  - 更偏“高质量检索 + 内容读取”的组合，而不是单独做网页采集。
- 常用参数：
  - `query`：必填。
  - `type`：文档可见 `neural`、`fast`、`auto`、`deep-lite`、`deep`、`deep-reasoning`、`instant`。
  - `category`：可聚焦 `company`、`people`、`research paper`、`news`、`financial report` 等。
  - `userLocation`：两位 ISO 国家码，例如 `US`。
  - `numResults`：默认 10，文档最大 100。
  - `includeDomains` / `excludeDomains`
  - `startCrawlDate` / `endCrawlDate`
  - `startPublishedDate` / `endPublishedDate`
  - `contents`：可内联请求正文、highlights、summary、extras。
- `contents` 常见用法：
  - `text: true`：直接返回页面正文。
  - `highlights: true`：返回与 query 最相关的摘录。
  - `summary`：返回摘要。
  - `extras`：可补充链接等内容。
- 返回重点：
  - `requestId`
  - `results[]`
  - `searchType`
  - 兼容字段 `context`（文档已标 deprecated）
  - 可选 `output`
  - `costDollars`

### 4.2 Contents

- 接口：`POST https://api.exa.ai/contents`
- 作用：当你已经有 URL 或 Exa 文档 ID 时，用它做正文获取最合适；这是 Exa 体系里最接近“fetch”的接口。
- 常用参数：
  - `urls` 或 `ids`
  - `text`
  - `highlights`
  - `summary`
  - `maxAgeHours`
  - `livecrawl`：文档标为 deprecated，建议优先看 `maxAgeHours`
  - `livecrawlTimeout`
  - `subpages`
  - `subpageTarget`
  - `extras`
  - `context`：deprecated
- 关键行为：
  - 缓存命中时直接返回。
  - 未命中时自动 live crawl 兜底。
  - `text` 返回的是整理过的 markdown 正文，不是原始 HTML。
- 返回重点：
  - `requestId`
  - `results[]`
  - `statuses[]`：逐 URL 状态，包含成功/失败及 crawl 错误标签。
  - `costDollars`

### 4.3 关于 Crawl

- Exa 官方公开文档里没有像 Tavily / Firecrawl 那样独立的站点级 crawl endpoint。
- 如果你只是想“顺着一个结果多取几层内容”，最接近的办法是：
  - 用 `POST /search` 先找入口。
  - 再用 `POST /contents` 的 `subpages` / `subpageTarget` 和新鲜度控制能力补取内容。

### 4.4 适用判断

- 如果你的主任务是“检索质量优先”，而且希望搜索阶段就拿到正文/摘要，Exa 很合适。
- 如果你的任务是“整站采集、JS 渲染、复杂交互”，Exa 不是最完整的那类产品。

## 5. Firecrawl

### 5.1 Search

- 接口：`POST https://api.firecrawl.dev/v2/search`
- 核心特点：
  - Search 不只是 SERP；加上 `scrapeOptions` 之后，可以把搜索结果直接抓成正文。
  - 同一接口支持 `web`、`images`、`news` 等 source。
- 常用参数：
  - `query`：必填。
  - `limit`：默认 10，范围 `1-100`。
  - `sources`：默认 `["web"]`，也可用 `images`、`news`。
  - `categories`：`github`、`research`、`pdf`。
  - `includeDomains` / `excludeDomains`：互斥。
  - `tbs`：时间过滤，支持 `qdr:h/d/w/m/y`、自定义日期范围、按时间排序。
  - `location`
  - `country`
  - `timeout`
  - `scrapeOptions`
- 一个关键差异：
  - 如果不传 `scrapeOptions.formats`，Search 更像返回 SERP 结果。
  - 如果带上 `formats: ["markdown"]` 之类的 scrape 选项，结果里可以直接返回 `markdown`、`html`、`rawHtml` 等正文内容。
- 返回重点：
  - `success`
  - `data.web[]` / `data.images[]` / `data.news[]`
  - `warning`
  - `id`
  - `creditsUsed`

### 5.2 Scrape

- 接口：`POST https://api.firecrawl.dev/v2/scrape`
- 作用：单 URL 抓取，是 Firecrawl 体系里最直接的“fetch”。
- 常用参数：
  - `url`
  - `formats`
  - `onlyMainContent`
  - `includeTags` / `excludeTags`
  - `maxAge` / `minAge`
  - `headers`
  - `waitFor`
  - `mobile`
  - `timeout`
  - `parsers`
  - `actions`
  - `location`
  - `proxy`
  - `storeInCache`
  - `zeroDataRetention`
- 适合的页面类型：
  - Firecrawl 文档明确写了支持动态网站、JS 渲染页面、PDF、图像等多类输入。

### 5.3 Extract

- 接口：`POST https://api.firecrawl.dev/v2/extract`
- 作用：针对一批 URL 或一个站点范围，按 `prompt` 或 `schema` 做结构化抽取。
- 常用参数：
  - `urls`
  - `prompt`
  - `schema`
  - `enableWebSearch`
  - `ignoreSitemap`
  - `includeSubdomains`
  - `showSources`
  - `scrapeOptions`
  - `ignoreInvalidURLs`
- 适合的场景：
  - 你要的不是正文，而是“从页面中抽出结构化字段”。
  - 例如：商品信息、公司资料、文档字段、联系人信息。

### 5.4 Crawl

- 接口：`POST https://api.firecrawl.dev/v2/crawl`
- 作用：整站递归抓取，返回异步任务 ID，再通过状态接口、Webhook 或 WebSocket 取结果。
- 常用参数：
  - `url`
  - `prompt`
  - `includePaths` / `excludePaths`
  - `maxDiscoveryDepth`
  - `sitemap`
  - `ignoreQueryParameters`
  - `regexOnFullURL`
  - `limit`
  - `crawlEntireDomain`
  - `allowExternalLinks`
  - `allowSubdomains`
  - `ignoreRobotsTxt`
  - `robotsUserAgent`
  - `delay`
  - `maxConcurrency`
  - `scrapeOptions`
  - `zeroDataRetention`
- 文档里的运维特征：
  - 默认 crawl `limit` 是 10,000 页。
  - Feature 文档说明每个 crawled page 消耗 1 credit。
  - 返回方式支持 polling、WebSocket、Webhook。

### 5.5 适用判断

- 如果你关心“抓网页这件事本身”，Firecrawl 是这 4 家里能力面最宽的一家。
- 搜索、单页抓取、整站 crawl、结构化抽取是分层设计的，边界清楚，适合做采集管线。

## 6. TinyFish

### 6.1 Search

- 接口：`GET https://api.search.tinyfish.ai`
- 核心特点：
  - Search 和 Fetch 拆得很明确。
  - Search 本身只做结构化搜索结果返回，不顺带抓正文。
  - 官方首页明确说明 Search / Fetch 为公开 API 面。
- 常用参数：
  - `query`：必填。
  - `location`：国家代码，例如 `US`、`GB`、`FR`、`DE`。
  - `language`：语言代码，例如 `en`、`fr`、`de`。
  - `page`：从 `0` 开始，最大 `10`。
- 其他特点：
  - 支持把搜索操作符直接写进 `query`，比如 `site:` 排除/限定站点。
  - 只传 `location` 或只传 `language` 时，另一项会自动补齐。
- 返回重点：
  - `query`
  - `results[]`
  - `total_results`
  - `page`
- 计费和限流：
  - 文档写明 Search 不使用 credits。
  - 限流按请求数/分钟：Free 5、Pay As You Go 10、Starter 20、Pro 50。

### 6.2 Fetch

- 接口：`POST https://api.fetch.tinyfish.ai`
- 核心特点：
  - 文档明确说明会用真实浏览器渲染页面后再提取内容。
  - 非常像“浏览器版 fetch + extract”。
- 常用参数：
  - `urls`：必填，单次最多 10 个 URL。
  - `format`：`markdown` / `html` / `json`，默认 `markdown`。
  - `links`
  - `image_links`
- 输入限制：
  - 只接受 `http/https`。
  - 私网 IP、`localhost`、云元数据地址会被拒绝。
- 返回重点：
  - `results[]`：成功的 URL。
  - `errors[]`：失败的 URL；单个 URL 失败不会拖垮整个批次。
  - 成功项里常见字段：
    - `url`
    - `final_url`
    - `title`
    - `description`
    - `language`
    - `author`
    - `published_date`
    - `text`
    - 可选 `links`
    - 可选 `image_links`
    - `latency_ms`
    - `format`
- 失败行为：
  - `errors[]` 里的错误码包括 `timeout`、`bot_blocked`、`empty_content`、`invalid_url`、`proxy_error`、`fetch_error`。
  - 文档写明单 URL 后端超时 110 秒，整批次还有 120 秒 CDN 上限，建议客户端超时至少 150 秒。
- 支持内容类型：
  - HTML、PDF、JSON、纯文本可处理。
  - 图片类内容不支持，文档明确会返回无可提取内容错误。
- 限流和计费：
  - 限流按 URL 数/分钟：Free 25、Pay As You Go 50、Starter 100、Pro 250。
  - 文档写明 Fetch 不使用 credits。

### 6.3 关于 Crawl

- TinyFish 当前公开文档没有单独的站点级 crawl API。
- 如果你需要多页导航、登录态、表单交互、有状态浏览器流程，或者更像 agent 的网页自动化，
- 官方文档建议转向 Agent API 或 Browser API，而不是 Search / Fetch。

### 6.4 适用判断

- 如果你需要一个极轻的搜索接口，再配一个真实浏览器 fetch，这个组合很干净。
- 如果你的目标是“整站 crawl 平台”，TinyFish 的公开能力重心不在这里。

## 7. 选型建议

### 7.1 想要“一次请求把搜索和内容都拿回来”

- 优先看 Tavily `POST /search`
- 其次看 Exa `POST /search` + `contents`
- Firecrawl `POST /v2/search` 也能做到，但更像“Search + Scrape 组合器”

### 7.2 想要“给定 URL，稳定拿正文”

- JS-heavy 或动态页面优先：Firecrawl `POST /v2/scrape`、TinyFish Fetch
- 更偏正文/研究资料：Exa `POST /contents`
- 想和搜索统一在一套 API：Tavily `POST /extract`

### 7.3 想要“整站 crawl / 文档入库 / RAG 建库”

- 首选：Firecrawl `POST /v2/crawl`
- 次选：Tavily `POST /crawl`
- Exa / TinyFish 公开文档都不是以 standalone site crawl 为主

### 7.4 想要“结构化字段抽取”

- 首选：Firecrawl `POST /v2/extract`
- Tavily / Exa 更像正文和检索导向，不是最典型的 schema-first 抽取接口

## 8. 官方文档来源

### Tavily

- Introduction: https://docs.tavily.com/documentation/api-reference/introduction
- Search: https://docs.tavily.com/documentation/api-reference/endpoint/search
- Extract: https://docs.tavily.com/documentation/api-reference/endpoint/extract
- Crawl: https://docs.tavily.com/documentation/api-reference/endpoint/crawl
- Credits & Pricing: https://docs.tavily.com/documentation/api-credits

### Exa

- Search: https://exa.ai/docs/reference/search
- Contents endpoint: https://exa.ai/docs/reference/get-contents
- Contents retrieval guide: https://exa.ai/docs/reference/contents-retrieval

### Firecrawl

- API introduction: https://docs.firecrawl.dev/api-reference/introduction
- Search: https://docs.firecrawl.dev/api-reference/v2-endpoint/search
- Scrape: https://docs.firecrawl.dev/api-reference/v2-endpoint/scrape
- Extract: https://docs.firecrawl.dev/api-reference/v2-endpoint/extract
- Crawl: https://docs.firecrawl.dev/api-reference/v2-endpoint/crawl
- Crawl feature guide: https://docs.firecrawl.dev/features/crawl

### TinyFish

- Docs home: https://docs.tinyfish.ai/
- Search reference: https://docs.tinyfish.ai/search-api/reference
- Fetch reference: https://docs.tinyfish.ai/fetch-api/reference
