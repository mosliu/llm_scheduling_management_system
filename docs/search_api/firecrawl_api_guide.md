# Firecrawl API 详细整理

- 核对日期：2026-05-07
- 文档范围：围绕 Firecrawl 的 `search`、`scrape`、`batch scrape`、`extract`、`crawl` 与状态查询接口整理。
- 官方文档入口：
  - API intro: https://docs.firecrawl.dev/api-reference/v2-introduction
  - Search: https://docs.firecrawl.dev/api-reference/v2-endpoint/search
  - Scrape: https://docs.firecrawl.dev/api-reference/v2-endpoint/scrape
  - Batch Scrape: https://docs.firecrawl.dev/api-reference/endpoint/batch-scrape
  - Batch Scrape Status: https://docs.firecrawl.dev/api-reference/endpoint/batch-scrape-get
  - Extract: https://docs.firecrawl.dev/api-reference/v2-endpoint/extract
  - Crawl: https://docs.firecrawl.dev/api-reference/v2-endpoint/crawl-post
  - Crawl Status: https://docs.firecrawl.dev/api-reference/v2-endpoint/crawl-get
  - Crawl Errors: https://docs.firecrawl.dev/api-reference/endpoint/crawl-get-errors
  - Crawl feature guide: https://docs.firecrawl.dev/features/crawl
  - Errors: https://docs.firecrawl.dev/api-reference/errors
  - Rate limits: https://docs.firecrawl.dev/rate-limits
  - Docs index: https://docs.firecrawl.dev/llms.txt

## 1. 基础信息

### 1.1 Base URL

```text
https://api.firecrawl.dev
```

### 1.2 鉴权

```http
Authorization: Bearer fc-YOUR_API_KEY
Content-Type: application/json
```

### 1.3 Firecrawl 的接口分工

- `POST /v2/search`
  - 搜索网页。
  - 可选地直接 scrape 搜索结果内容。
- `POST /v2/scrape`
  - 抓单个 URL。
  - 这是最直接的“fetch one page”接口。
- `POST /v2/batch/scrape`
  - 给一组显式 URL 做批量抓取。
- `POST /v2/extract`
  - 从 URL 或站点范围里抽结构化数据。
- `POST /v2/crawl`
  - 整站异步 crawl。
- `GET /v2/crawl/{id}`
  - 查询 crawl 状态和结果。
- `GET /v2/crawl/{id}/errors`
  - 单独拉取 crawl 失败项和 robots 拦截项。

## 2. Search API

### 2.1 接口定义

```http
POST https://api.firecrawl.dev/v2/search
```

### 2.2 核心特点

- Search 和 Scrape 是打通的。
- 如果你只想要 SERP，直接 search。
- 如果你希望搜索结果里直接带 markdown/html，可以给 `scrapeOptions`。
- 支持 `web`、`images`、`news` 三类 source。

### 2.3 关键请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | `string` | 是 | 搜索 query，最大长度 500。 |
| `limit` | `integer` | 否 | 默认 10，范围 `1-100`。 |
| `sources` | `array` | 否 | 默认 `["web"]`，支持 `web`、`images`、`news`。 |
| `categories` | `array` | 否 | 过滤类别，支持 `github`、`research`、`pdf`。 |
| `includeDomains` | `string[]` | 否 | 限定域名，不能和 `excludeDomains` 同时用。 |
| `excludeDomains` | `string[]` | 否 | 排除域名。 |
| `tbs` | `string` | 否 | 时间过滤，支持 `qdr:h/d/w/m/y`、自定义日期范围、`sbd:1` 排序。 |
| `location` | `string` | 否 | 地理位置字符串，例如 `Germany` 或 `San Francisco,California,United States`。 |
| `country` | `string` | 否 | ISO 国家码，默认 `US`。 |
| `timeout` | `integer` | 否 | 毫秒，默认 `60000`。 |
| `ignoreInvalidURLs` | `boolean` | 否 | 排掉后续 Firecrawl 端点不可用的 URL。 |
| `enterprise` | `string[]` | 否 | 企业版 ZDR 选项，`anon` 或 `zdr`。 |
| `scrapeOptions` | `object` | 否 | 让搜索结果直接带 scrape 内容。 |

### 2.4 支持的 query operator

官方文档列出的常见 operator：

- `""`
- `-`
- `site:`
- `filetype:`
- `inurl:`
- `allinurl:`
- `intitle:`
- `allintitle:`
- `related:`
- `imagesize:`
- `larger:`

### 2.5 `tbs` 参数

官方明确支持：

- 预定义时间窗口：
  - `qdr:h`
  - `qdr:d`
  - `qdr:w`
  - `qdr:m`
  - `qdr:y`
- 自定义日期范围：
  - `cdr:1,cd_min:MM/DD/YYYY,cd_max:MM/DD/YYYY`
- 按日期排序：
  - `sbd:1`
- 组合写法：
  - `sbd:1,qdr:w`

### 2.6 请求示例

#### 示例 1：只要 web 搜索结果

```bash
curl --request POST \
  --url https://api.firecrawl.dev/v2/search \
  --header "Authorization: Bearer fc-YOUR_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "query": "openai responses api docs",
    "limit": 5,
    "sources": ["web"],
    "includeDomains": ["platform.openai.com"]
  }'
```

#### 示例 2：搜索并直接带 markdown 正文

```bash
curl --request POST \
  --url https://api.firecrawl.dev/v2/search \
  --header "Authorization: Bearer fc-YOUR_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "query": "browser automation anti-bot guide",
    "limit": 3,
    "categories": ["research"],
    "scrapeOptions": {
      "formats": ["markdown"],
      "onlyMainContent": true
    }
  }'
```

### 2.7 返回示例

```json
{
  "success": true,
  "data": {
    "web": [
      {
        "title": "OpenAI API Introduction",
        "description": "Overview of the OpenAI platform and APIs.",
        "url": "https://platform.openai.com/docs/introduction",
        "markdown": "# Introduction\n\nThe OpenAI API provides...",
        "html": "<html>...</html>",
        "rawHtml": "<html>...</html>",
        "links": [
          "https://platform.openai.com/docs/api-reference/responses"
        ],
        "metadata": {
          "title": "Introduction",
          "description": "Overview of the OpenAI platform and APIs.",
          "sourceURL": "https://platform.openai.com/docs/introduction",
          "url": "https://platform.openai.com/docs/introduction",
          "statusCode": 200,
          "error": null
        }
      }
    ]
  },
  "warning": null,
  "id": "6fa9758c-d48a-4a11-ae5a-9f3ab7448b70",
  "creditsUsed": 3
}
```

## 3. Scrape API

### 3.1 接口定义

```http
POST https://api.firecrawl.dev/v2/scrape
```

### 3.2 核心特点

- 单 URL 抓取。
- 支持动态网页、JS 渲染、PDF。
- 可返回 markdown、html、rawHtml、json、summary、links、images、screenshot、audio、highlights 等多种格式。
- 可做简单浏览器动作；复杂交互官方更建议走 Interact endpoint。

### 3.3 关键请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `url` | `string` | 是 | 要抓的 URL。 |
| `formats` | `array` | 否 | 返回格式数组。可传字符串，也可传对象格式。 |
| `onlyMainContent` | `boolean` | 否 | 默认 `true`。只保留主体内容。 |
| `onlyCleanContent` | `boolean` | 否 | 进一步清洗输出。 |
| `includeTags` | `string[]` | 否 | 只保留某些 DOM 标签。 |
| `excludeTags` | `string[]` | 否 | 排除某些 DOM 标签。 |
| `maxAge` | `integer` | 否 | 缓存允许的最大年龄。 |
| `minAge` | `integer` | 否 | 内容最小年龄限制。 |
| `headers` | `object` | 否 | 自定义请求头。 |
| `waitFor` | `integer` | 否 | 额外等待毫秒数。 |
| `mobile` | `boolean` | 否 | 使用移动端视角。 |
| `skipTlsVerification` | `boolean` | 否 | 跳过 TLS 校验。 |
| `timeout` | `integer` | 否 | 默认 `60000` 毫秒。 |
| `parsers` | `string[]` | 否 | 例如 `pdf`。 |
| `actions` | `array` | 否 | 抓取前执行动作。 |
| `location` | `object` | 否 | 国家和语言环境。 |
| `removeBase64Images` | `boolean` | 否 | 去掉 base64 图片。 |
| `blockAds` | `boolean` | 否 | 广告拦截。 |
| `proxy` | `string` | 否 | `basic`、`enhanced`、`auto`。 |
| `storeInCache` | `boolean` | 否 | 是否进入 Firecrawl 缓存。 |
| `lockdown` | `boolean` | 否 | 锁定更严格的执行环境。 |
| `zeroDataRetention` | `boolean` | 否 | 零数据保留。 |

### 3.4 `formats` 常见选项

官方文档列出的可选格式包括：

- `markdown`
- `summary`
- `html`
- `rawHtml`
- `links`
- `images`
- `screenshot`
- `json`
- `changeTracking`
- `branding`
- `audio`
- `question`
- `highlights`

其中 `json` 可以带 schema 配置。

### 3.5 `actions` 能做什么

`actions` 可以做的事情包括：

- wait
- wait for element
- screenshot
- click
- write text
- press key
- scroll
- scrape
- execute javascript
- generate pdf

但官方文档明确建议：复杂交互优先用 Interact endpoint，而不是把复杂脚本塞进 `actions`。

### 3.6 请求示例

```bash
curl --request POST \
  --url https://api.firecrawl.dev/v2/scrape \
  --header "Authorization: Bearer fc-YOUR_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "url": "https://docs.firecrawl.dev",
    "formats": ["markdown", "html", "links"],
    "onlyMainContent": true,
    "blockAds": true,
    "timeout": 60000
  }'
```

### 3.7 返回示例

```json
{
  "success": true,
  "data": {
    "markdown": "# Firecrawl Docs\n\nFirecrawl turns websites into LLM-ready data...",
    "summary": "Developer documentation for Firecrawl APIs.",
    "html": "<main>...</main>",
    "rawHtml": "<html>...</html>",
    "links": [
      "https://docs.firecrawl.dev/api-reference/v2-endpoint/scrape"
    ],
    "metadata": {
      "title": "Firecrawl Docs",
      "description": "Developer docs for Firecrawl",
      "language": "en",
      "sourceURL": "https://docs.firecrawl.dev",
      "url": "https://docs.firecrawl.dev",
      "keywords": "firecrawl, api, scrape",
      "statusCode": 200,
      "contentType": "text/html",
      "error": null
    },
    "warning": null
  }
}
```

## 4. Batch Scrape API

### 4.1 为什么这个接口很重要

如果你手里已经有一批明确 URL，`POST /v2/batch/scrape` 往往比 `crawl` 更合适。

- 它不是“站点发现”
- 它是“对给定 URL 列表并发抓取”

### 4.2 接口定义

```http
POST https://api.firecrawl.dev/v2/batch/scrape
GET  https://api.firecrawl.dev/v2/batch/scrape/{id}
```

### 4.3 启动作业示例

```bash
curl --request POST \
  --url https://api.firecrawl.dev/v2/batch/scrape \
  --header "Authorization: Bearer fc-YOUR_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "urls": [
      "https://docs.firecrawl.dev",
      "https://platform.openai.com/docs/introduction"
    ],
    "formats": ["markdown"],
    "maxConcurrency": 5,
    "ignoreInvalidURLs": true
  }'
```

### 4.4 启动作业返回示例

```json
{
  "success": true,
  "id": "15b58e5e-730c-4b10-bf3e-6b87ef4f2498",
  "url": "https://api.firecrawl.dev/v2/batch/scrape/15b58e5e-730c-4b10-bf3e-6b87ef4f2498",
  "invalidURLs": []
}
```

### 4.5 查询状态返回示例

```json
{
  "status": "completed",
  "total": 2,
  "completed": 2,
  "creditsUsed": 2,
  "expiresAt": "2026-05-08T09:15:00Z",
  "next": null,
  "data": [
    {
      "markdown": "# Firecrawl Docs\n\n...",
      "metadata": {
        "url": "https://docs.firecrawl.dev",
        "statusCode": 200
      }
    }
  ]
}
```

## 5. Extract API

### 5.1 接口定义

```http
POST https://api.firecrawl.dev/v2/extract
```

### 5.2 核心特点

- 目标不是“拿正文”，而是“按 prompt/schema 抽结构化数据”。
- 适合商品、公司资料、联系信息、文档字段抽取。
- 可以结合 `scrapeOptions` 控制底层抓取方式。

### 5.3 关键请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `urls` | `string[]` | 是 | 要处理的 URL 列表。 |
| `prompt` | `string` | 否 | 告诉模型抽什么。 |
| `schema` | `object` | 否 | 结构化输出 schema。 |
| `enableWebSearch` | `boolean` | 否 | 允许模型做额外 web search。 |
| `ignoreSitemap` | `boolean` | 否 | 忽略 sitemap。 |
| `includeSubdomains` | `boolean` | 否 | 是否包含子域。 |
| `showSources` | `boolean` | 否 | 返回 `sources`。 |
| `scrapeOptions` | `object` | 否 | 控制底层抓取。 |
| `ignoreInvalidURLs` | `boolean` | 否 | 默认 `true`。 |

### 5.4 请求示例

```bash
curl --request POST \
  --url https://api.firecrawl.dev/v2/extract \
  --header "Authorization: Bearer fc-YOUR_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "urls": [
      "https://example.com/company/acme"
    ],
    "prompt": "Extract company name, founding year, headquarters, and pricing page URL",
    "schema": {
      "type": "object",
      "properties": {
        "company_name": { "type": "string" },
        "founded_year": { "type": "integer" },
        "hq": { "type": "string" },
        "pricing_url": { "type": "string" }
      },
      "required": ["company_name"]
    },
    "showSources": true,
    "scrapeOptions": {
      "formats": ["markdown"],
      "onlyMainContent": true
    }
  }'
```

### 5.5 启动作业返回示例

```json
{
  "success": true,
  "id": "abf09b49-c2a6-49e1-aa9c-b8d366bdf55d",
  "invalidURLs": []
}
```

## 6. Crawl API

### 6.1 接口定义

```http
POST https://api.firecrawl.dev/v2/crawl
GET  https://api.firecrawl.dev/v2/crawl/{id}
GET  https://api.firecrawl.dev/v2/crawl/{id}/errors
```

### 6.2 核心特点

- 异步任务式。
- 适合整站抓取、文档库导入、RAG 建库。
- 结果分页返回，响应过大时用 `next` 继续取。
- 失败页面与成功页面分开看。

### 6.3 启动 crawl 的关键参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `url` | `string` | 是 | 根 URL。 |
| `prompt` | `string` | 否 | 告诉 crawl 应优先抓什么。 |
| `excludePaths` | `string[]` | 否 | 排除路径。 |
| `includePaths` | `string[]` | 否 | 包含路径。 |
| `maxDiscoveryDepth` | `integer` | 否 | 发现深度。 |
| `sitemap` | `string` | 否 | sitemap 处理模式。 |
| `ignoreQueryParameters` | `boolean` | 否 | 忽略 query string 差异。 |
| `regexOnFullURL` | `boolean` | 否 | 路径匹配是否针对完整 URL。 |
| `limit` | `integer` | 否 | 默认 `10000` 页。 |
| `crawlEntireDomain` | `boolean` | 否 | 扩展到整个域。 |
| `allowExternalLinks` | `boolean` | 否 | 是否抓外链。 |
| `allowSubdomains` | `boolean` | 否 | 是否抓子域。 |
| `ignoreRobotsTxt` | `boolean` | 否 | 是否忽略 robots。 |
| `robotsUserAgent` | `string` | 否 | 自定义 robots user-agent。 |
| `delay` | `integer` | 否 | 访问间隔。 |
| `maxConcurrency` | `integer` | 否 | crawl 并发度。 |
| `scrapeOptions` | `object` | 否 | 每个页面如何抓。 |
| `zeroDataRetention` | `boolean` | 否 | 零数据保留。 |

### 6.4 启动请求示例

```bash
curl --request POST \
  --url https://api.firecrawl.dev/v2/crawl \
  --header "Authorization: Bearer fc-YOUR_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "url": "https://docs.firecrawl.dev",
    "prompt": "Only crawl API reference and feature guides",
    "includePaths": ["/api-reference/", "/features/"],
    "maxDiscoveryDepth": 2,
    "limit": 100,
    "allowSubdomains": false,
    "scrapeOptions": {
      "formats": ["markdown"],
      "onlyMainContent": true
    }
  }'
```

### 6.5 启动返回示例

```json
{
  "success": true,
  "id": "dd1c9f17-2d78-4663-91c5-0f0c60dcb60a",
  "url": "https://api.firecrawl.dev/v2/crawl/dd1c9f17-2d78-4663-91c5-0f0c60dcb60a"
}
```

### 6.6 查询状态返回示例

```json
{
  "status": "completed",
  "total": 42,
  "completed": 42,
  "creditsUsed": 42,
  "expiresAt": "2026-05-08T10:00:00Z",
  "next": null,
  "data": [
    {
      "markdown": "# Search\n\nSearch and optionally scrape search results...",
      "html": "<html>...</html>",
      "rawHtml": "<html>...</html>",
      "links": [
        "https://docs.firecrawl.dev/api-reference/v2-endpoint/scrape"
      ],
      "metadata": {
        "title": "Search - Firecrawl Docs",
        "description": "Search endpoint reference",
        "language": "en",
        "sourceURL": "https://docs.firecrawl.dev/api-reference/v2-endpoint/search",
        "url": "https://docs.firecrawl.dev/api-reference/v2-endpoint/search",
        "statusCode": 200,
        "error": null
      }
    }
  ]
}
```

### 6.7 查询失败项返回示例

```json
{
  "errors": [
    {
      "id": "2a9d8bd7-5ec0-4f1d-a45e-58c5adcf00b3",
      "timestamp": "2026-05-07T10:30:12Z",
      "url": "https://docs.example.com/private",
      "error": "Request Timeout"
    }
  ],
  "robotsBlocked": [
    "https://docs.example.com/internal"
  ]
}
```

## 7. 费用、限流和队列

### 7.1 Crawl credits

官方 feature 文档明确说明：

- 每抓到 1 页，消耗 1 credit
- 默认 crawl `limit` 是 10,000 页
- 如果账户剩余 credits 覆盖不了 `limit`，会先返回 `402`

额外成本：

- JSON mode：每页额外 4 credits
- Enhanced proxy：每页额外 4 credits
- PDF parsing：每个 PDF 页额外 1 credit

### 7.2 结果保留时间

官方文档说明 crawl job 结果通过 API 保留 24 小时。之后仍可在 activity logs 查看，但不保证还能继续通过同一 API 直接拉取。

### 7.3 并发浏览器限制

Firecrawl 的真实瓶颈很多时候不是 RPM，而是 concurrent browsers。当前官方文档给出的部分档位：

- Free：2
- Hobby：5
- Standard：50
- Growth：100
- Scale / Enterprise：150+

### 7.4 当前官方 RPM 限流

截至 2026-05-07，官方 rate limits 页给出的 current plans 里，常见端点是：

| Plan | `/scrape` | `/crawl` | `/search` | `/crawl/status` |
| --- | --- | --- | --- | --- |
| Free | 10/min | 1/min | 5/min | 1500/min |
| Hobby | 100/min | 15/min | 50/min | 1500/min |
| Standard | 500/min | 50/min | 250/min | 1500/min |
| Growth | 5000/min | 250/min | 2500/min | 1500/min |
| Scale | 7500/min | 750/min | 7500/min | 25000/min |

补充说明：

- Extract endpoints 与 `/agent` 共用相应限流。
- Batch scrape 与 `/crawl` 共用相应限流。
- 所有限流按 team 计，不是按单 key 独立计。

## 8. 错误处理

### 8.1 Firecrawl 的统一错误形状

所有非 2xx 响应使用类似结构：

```json
{
  "success": false,
  "error": "Unauthorized: Invalid token",
  "details": {
    "field": "url"
  }
}
```

### 8.2 常见 HTTP 错误

官方 Errors 文档列出的高频错误包括：

- `400 Bad Request`
- `401 Unauthorized`
- `402 Payment Required`
- `403 Forbidden`
- `404 Not Found`
- `408 Request Timeout`
- `409 Conflict`
- `413 Payload Too Large`
- `422 Unprocessable Entity`
- `429 Rate limit exceeded`
- `500 Internal Server Error`
- `502 Bad Gateway`
- `503 Service Unavailable`
- `504 Gateway Timeout`

### 8.3 重试建议

官方文档建议可重试的典型状态：

- `408`
- `429`
- `500`
- `502`
- `503`
- `504`

并优先尊重 `Retry-After`。

## 9. 实战建议

- 明确 URL 列表时，优先 `batch scrape`，不要滥用 `crawl`。
- 只要单页面时，直接用 `/v2/scrape`。
- 想拿结构化字段时，直接用 `/v2/extract`，不要先 scrape 再自己让 LLM 重解析。
- 整站入库时，必须把 `limit`、`includePaths`、`excludePaths` 收窄，否则很容易成本失控。
- 要调试 crawl，除了看 `GET /v2/crawl/{id}`，还要看 `GET /v2/crawl/{id}/errors`，否则只看成功页会误判。

