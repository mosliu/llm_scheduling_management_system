# TinyFish API 详细整理

- 核对日期：2026-05-07
- 文档范围：围绕 TinyFish 的 `Search API`、`Fetch API` 以及 `Fetch Usage API` 整理，补充限流、错误处理、返回示例和接入建议。
- 官方文档入口：
  - Docs home: https://docs.tinyfish.ai/
  - Search reference: https://docs.tinyfish.ai/search-api/reference
  - Fetch reference: https://docs.tinyfish.ai/fetch-api/reference
  - Docs index: https://docs.tinyfish.ai/llms.txt

## 1. 基础信息

### 1.1 两个公开 API 域名

Search 和 Fetch 是分开的：

```text
GET  https://api.search.tinyfish.ai
POST https://api.fetch.tinyfish.ai
```

### 1.2 鉴权

两类请求都需要：

```http
X-API-Key: YOUR_TINYFISH_API_KEY
```

### 1.3 TinyFish 的接口分工

- Search API
  - 负责搜索结果发现
  - 不顺带抓正文
- Fetch API
  - 负责真实浏览器渲染后抽正文
  - 更像“browser-backed fetch”

这套设计非常干净：

- 先搜到链接
- 再按需抓正文

## 2. Search API

### 2.1 接口定义

```http
GET https://api.search.tinyfish.ai
```

### 2.2 关键参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | `string` | 是 | 搜索 query。支持直接写搜索操作符。 |
| `location` | `string` | 否 | 国家代码，例如 `US`、`GB`、`FR`、`DE`。 |
| `language` | `string` | 否 | 语言代码，例如 `en`、`fr`、`de`。 |
| `page` | `number` | 否 | 从 `0` 开始，最大值 `10`。 |

### 2.3 `location` 和 `language` 的自动配对

官方文档明确说明：

- 只传 `location`，会自动推断主语言
- 只传 `language`，会自动推断主要国家
- 两者都不传时，默认：
  - `location=US`
  - `language=en`

示例：

- `location=BR`，若不传 `language`，会自动推成 `pt`
- `language=ja`，若不传 `location`，会自动推成 `JP`

### 2.4 支持的 query operator 写法

Search API 没有单独列一个 operator 表，但官方文档明确说明可以把搜索操作符直接写进 `query` 字符串。

例如：

- `python tutorial site:docs.python.org`
- `recipe ideas -site:facebook.com -site:youtube.com`

### 2.5 请求示例

```bash
curl -G "https://api.search.tinyfish.ai" \
  -H "X-API-Key: YOUR_TINYFISH_API_KEY" \
  --data-urlencode "query=browser automation tools site:github.com" \
  --data-urlencode "location=US" \
  --data-urlencode "language=en" \
  --data-urlencode "page=0"
```

### 2.6 返回示例

```json
{
  "query": "browser automation tools site:github.com",
  "results": [
    {
      "position": 1,
      "site_name": "github.com",
      "title": "microsoft/playwright",
      "snippet": "Playwright enables reliable end-to-end testing for modern web apps.",
      "url": "https://github.com/microsoft/playwright"
    },
    {
      "position": 2,
      "site_name": "github.com",
      "title": "puppeteer/puppeteer",
      "snippet": "Puppeteer is a JavaScript library to control Chrome or Firefox.",
      "url": "https://github.com/puppeteer/puppeteer"
    }
  ],
  "total_results": 10,
  "page": 0
}
```

### 2.7 返回字段说明

| 字段 | 说明 |
| --- | --- |
| `query` | 实际执行的 query。 |
| `results[]` | 搜索结果数组。 |
| `results[].position` | 搜索位置，1 起始。 |
| `results[].site_name` | 域名。 |
| `results[].title` | 标题。 |
| `results[].snippet` | 摘要片段。 |
| `results[].url` | 结果 URL。 |
| `total_results` | 总返回条数。 |
| `page` | 当前页码，从 `0` 开始。 |

### 2.8 Search API 错误码

官方文档列出的 HTTP 错误：

- `400`：缺少 `query` 或参数值非法
- `401`：缺少或无效 API key
- `402`：需要有效订阅
- `403`：当前账户未启用 Search API
- `404`：Search API 不可用
- `429`：限流
- `500`：内部错误
- `503`：搜索服务暂不可用，建议 backoff

### 2.9 Search API 限流与计费

截至 2026-05-07，官方文档写的是：

| Plan | Requests / minute |
| --- | --- |
| Free | 5 |
| Pay As You Go | 10 |
| Starter | 20 |
| Pro | 50 |

计费规则：

- Search 不使用 credits

## 3. Fetch API

### 3.1 接口定义

```http
POST https://api.fetch.tinyfish.ai
```

### 3.2 核心特点

- 文档明确说明会用真实浏览器渲染页面后提取内容。
- 不是简单的原始 HTTP fetch。
- 返回格式可选 `markdown`、`html`、`json`。
- 单次最多 10 个 URL。
- 单个 URL 失败不会拖垮整个 batch。

### 3.3 请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `urls` | `string[]` | 是 | 要抓取的 URL 列表，最多 10 个。 |
| `format` | `string` | 否 | `markdown`、`html`、`json`，默认 `markdown`。 |
| `links` | `boolean` | 否 | 是否返回页面内所有链接。 |
| `image_links` | `boolean` | 否 | 是否返回页面内所有图片链接。 |

### 3.4 URL 输入限制

官方文档明确限制：

- 只接受 `http` / `https`
- 私网 IP 不允许
- `localhost` 不允许
- 云元数据地址不允许

### 3.5 `format` 的区别

- `markdown`
  - 最适合 LLM 消费
  - 默认值
- `html`
  - 返回语义化 HTML
- `json`
  - 返回结构化文档树

### 3.6 请求示例

#### 示例 1：默认 markdown 抓正文

```bash
curl -X POST "https://api.fetch.tinyfish.ai" \
  -H "X-API-Key: YOUR_TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://platform.openai.com/docs/introduction"],
    "format": "markdown"
  }'
```

#### 示例 2：同时抓链接和图片链接

```bash
curl -X POST "https://api.fetch.tinyfish.ai" \
  -H "X-API-Key: YOUR_TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://docs.tinyfish.ai/",
      "https://platform.openai.com/docs/introduction"
    ],
    "format": "html",
    "links": true,
    "image_links": true
  }'
```

### 3.7 返回示例

```json
{
  "results": [
    {
      "url": "https://platform.openai.com/docs/introduction",
      "final_url": "https://platform.openai.com/docs/introduction",
      "title": "Introduction - OpenAI API",
      "description": "Overview of the OpenAI platform and APIs.",
      "language": "en",
      "author": "OpenAI",
      "published_date": "2026-04-30T12:00:00Z",
      "text": "# Introduction\n\nThe OpenAI API provides...",
      "links": [
        "https://platform.openai.com/docs/api-reference/responses"
      ],
      "image_links": [
        "https://platform.openai.com/og-image.png"
      ],
      "latency_ms": 1845,
      "format": "markdown"
    }
  ],
  "errors": []
}
```

### 3.8 `results[]` 字段说明

| 字段 | 说明 |
| --- | --- |
| `url` | 原始请求 URL。 |
| `final_url` | 跳转后的最终 URL。 |
| `title` | 标题，优先 `og:title`。 |
| `description` | 描述，优先 `og:description`。 |
| `language` | 检测出的页面语言。 |
| `author` | 元数据里的作者。 |
| `published_date` | 检测出的发布时间。 |
| `text` | 页面正文。`markdown/html` 时是字符串，`json` 时是对象。 |
| `links` | 仅在 `links=true` 时返回。 |
| `image_links` | 仅在 `image_links=true` 时返回。 |
| `latency_ms` | 单页面耗时。 |
| `format` | 返回内容格式。 |

官方文档还特别说明：

- 若 `title`、`description`、`language`、`author`、`published_date` 这些字段无法提取，响应里通常会直接省略，而不是显式返回 `null`。

### 3.9 `errors[]` 字段说明

即使 HTTP 返回 `200`，也可能有逐 URL 失败项：

```json
{
  "results": [],
  "errors": [
    {
      "url": "https://example.com/private",
      "error": "bot_blocked"
    }
  ]
}
```

官方列出的 per-URL error code：

- `timeout`
- `bot_blocked`
- `empty_content`
- `invalid_url`
- `proxy_error`
- `fetch_error`

### 3.10 HTTP 错误码

Fetch API 的整个请求级错误：

- `400`：缺 `urls`、URL 太多、参数非法
- `401`：缺少或无效 API key
- `429`：限流
- `500`：内部错误

### 3.11 超时语义

官方文档明确说明：

- 单个 URL 后端超时：110 秒
- 整个批次还受 120 秒 CDN ceiling 约束
- 客户端超时建议至少 150 秒

这意味着：

- 批量抓取最好不要一次把 10 个特别慢的 JS 页面塞满
- 客户端不要把 timeout 设成 30 秒，否则会在你自己的侧提前断

### 3.12 支持的内容类型

官方文档写明：

| Content Type | 行为 |
| --- | --- |
| HTML | 提取完整文本并保留格式 |
| PDF | 提取文本内容 |
| JSON | 原始 JSON 作为文本返回 |
| Plain text | 原样返回全文 |
| Images (PNG/JPG) | 不支持，会返回没有可提取内容的错误 |

### 3.13 Fetch API 限流与计费

截至 2026-05-07，官方文档写的是：

| Plan | URLs / minute |
| --- | --- |
| Free | 25 |
| Pay As You Go | 50 |
| Starter | 100 |
| Pro | 250 |

计费规则：

- Fetch 不使用 credits

## 4. Fetch Usage API

### 4.1 接口定义

```http
GET https://api.fetch.tinyfish.ai/usage
```

### 4.2 这个接口是做什么的

- 查 Fetch 历史
- 按时间、状态、分页过滤
- 不返回完整正文，只返回元数据和计数

### 4.3 Query 参数

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `start_after` | `string` | ISO 8601 起始时间，例如 `2026-01-01T00:00:00Z` |
| `end_before` | `string` | ISO 8601 截止时间 |
| `status` | `string` | `completed` 或 `failed` |
| `limit` | `integer` | 默认 100，范围 1-1000 |
| `page` | `integer` | 默认 1 |

### 4.4 请求示例

```bash
curl -G "https://api.fetch.tinyfish.ai/usage" \
  -H "X-API-Key: YOUR_TINYFISH_API_KEY" \
  --data-urlencode "status=completed" \
  --data-urlencode "limit=50" \
  --data-urlencode "page=1"
```

### 4.5 返回示例

```json
{
  "items": [
    {
      "id": "fetch_01jt3zw1q4d4ewh37n3k5w7gqf",
      "url": "https://platform.openai.com/docs/introduction",
      "final_url": "https://platform.openai.com/docs/introduction",
      "title": "Introduction - OpenAI API",
      "description": "Overview of the OpenAI platform and APIs.",
      "language": "en",
      "author": "OpenAI",
      "published_date": "2026-04-30T12:00:00Z",
      "format": "markdown",
      "status": "completed",
      "request_origin": "api",
      "request_id": "req_01jt3zq0z7svf0b2n7j1j0r2me",
      "text_length": 18342,
      "links_count": 25,
      "image_links_count": 4,
      "latency_ms": 1845,
      "created_at": "2026-05-07T08:30:12Z",
      "error": null
    }
  ],
  "total": 42,
  "limit": 50,
  "page": 1,
  "total_pages": 1,
  "has_more": false
}
```

## 5. TinyFish 在 crawl 场景下的边界

TinyFish 当前公开 Search / Fetch 文档并没有单独的整站 crawl API。

如果你需要：

- 多页导航
- 登录态流程
- 表单交互
- 更复杂的浏览器自动化

应该转到 TinyFish 的：

- Agent API
- Browser API

而不是继续堆 Search / Fetch。

## 6. 实战建议

- “搜到链接，再抓正文”是 TinyFish 最自然的使用方式。
- Search 便宜且简单，适合做 URL 发现层。
- Fetch 更像带真实浏览器的抽取器，适合 JS-heavy 页面。
- 如果只要 LLM 可消费文本，优先用 `format=markdown`。
- 批量抓取时一定要处理 `errors[]`，不要只看 HTTP 200。

