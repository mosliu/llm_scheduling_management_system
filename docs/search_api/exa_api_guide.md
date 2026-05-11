# Exa API 详细整理

- 核对日期：2026-05-07
- 文档范围：围绕 Exa 的 `search` 与 `contents` 能力整理，并补充相关限制、费用、错误处理和返回示例。
- 官方文档入口：
  - Welcome: https://exa.ai/docs
  - Search: https://exa.ai/docs/reference/search
  - Contents: https://exa.ai/docs/reference/get-contents
  - Contents Retrieval: https://exa.ai/docs/reference/contents-retrieval
  - Error Codes: https://exa.ai/docs/reference/error-codes
  - Rate Limits: https://exa.ai/docs/reference/rate-limits
  - Pricing update: https://exa.ai/docs/changelog/pricing-update
  - Docs index: https://exa.ai/docs/llms.txt

## 1. 基础信息

### 1.1 Base URL

```text
https://api.exa.ai
```

### 1.2 鉴权

官方文档说明 API key 可以放在下面两种 header 之一：

```http
x-api-key: YOUR-EXA-API-KEY
```

或：

```http
Authorization: Bearer YOUR-EXA-API-KEY
```

大多数官方示例使用 `x-api-key`。

### 1.3 Exa 在搜索 / fetch 这条链路上的接口分工

- `POST /search`
  - 搜索网页。
  - 可直接在搜索阶段把正文、highlights、summary 一并带回。
- `POST /contents`
  - 已知 URL 或 Exa 文档 ID 时，取正文和相关元数据。
  - 这是 Exa 里最接近“fetch/extract content”的接口。

### 1.4 Exa 没有公开 standalone site crawl endpoint

截至 2026-05-07 的公开参考文档里，没有类似 Tavily `/crawl` 或 Firecrawl `/v2/crawl` 这种整站 crawl endpoint。

如果你需要：

- 搜一个入口后再补抓正文
- 控制内容新鲜度
- 顺着页面抓少量 `subpages`

通常用法是：

1. `POST /search`
2. `POST /contents`

## 2. Search API

### 2.1 接口定义

```http
POST https://api.exa.ai/search
```

### 2.2 这个接口的特点

- Search 本身就能带 `contents` 对象。
- 也就是说，很多场景下不需要“搜索一次，再 fetch 一次”。
- 对研究资料、文档、公司信息、人物资料、新闻检索很友好。
- 支持不同搜索类型，从低时延到深度综合输出都有。

### 2.3 关键请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | `string` | 是 | 搜索 query。 |
| `additionalQueries` | `string[]` | 否 | deep-search 变体可用，补充额外 query 变体。 |
| `stream` | `boolean` | 否 | `true` 时返回 SSE 流。 |
| `outputSchema` | `object` | 否 | 让 Exa 输出结构化综合结果。 |
| `systemPrompt` | `string` | 否 | 指导综合输出和深度搜索规划。 |
| `type` | `string` | 否 | `neural`、`fast`、`auto`、`deep-lite`、`deep`、`deep-reasoning`、`instant`。 |
| `category` | `string` | 否 | `company`、`research paper`、`news`、`personal site`、`financial report`、`people`。 |
| `userLocation` | `string` | 否 | 两位 ISO 国家码，例如 `US`。 |
| `numResults` | `integer` | 否 | 默认 `10`，不同搜索类型上限不同，常见上限是 `100`。 |
| `includeDomains` | `string[]` | 否 | 只在这些域名中找。 |
| `excludeDomains` | `string[]` | 否 | 排除这些域名。 |
| `startCrawlDate` | `string<date-time>` | 否 | 按抓取时间过滤。 |
| `endCrawlDate` | `string<date-time>` | 否 | 按抓取时间过滤。 |
| `startPublishedDate` | `string<date-time>` | 否 | 按发布时间过滤。 |
| `endPublishedDate` | `string<date-time>` | 否 | 按发布时间过滤。 |
| `moderation` | `boolean` | 否 | 打开安全过滤。 |
| `contents` | `object` | 否 | 直接返回正文 / highlights / summary / extras。 |

### 2.4 `type` 怎么理解

- `instant`
  - 最低时延，适合实时性很强的应用。
- `fast`
  - 比较偏速度。
- `auto`
  - 默认推荐值，自动选策略。
- `neural`
  - 语义检索导向。
- `deep-lite`
  - 轻量综合式深度搜索。
- `deep`
  - 更强的综合与多步推理式搜索。
- `deep-reasoning`
  - 比 `deep` 更重推理。

### 2.5 `category` 使用限制

官方文档明确说明：

- `company` 和 `people` 是受限类别。
- 这两类不支持：
  - `startPublishedDate`
  - `endPublishedDate`
  - `startCrawlDate`
  - `endCrawlDate`
  - `excludeDomains`
- `people` 类别下，`includeDomains` 只接受 LinkedIn 域名。
- 使用不支持的参数会返回 `400`。

### 2.6 `contents` 子对象常见用法

最常见的几个字段：

- `text`
  - `true` 时直接返回正文。
  - 也可传高级对象控制长度等选项。
- `highlights`
  - 让 Exa 返回与 query 最相关的片段。
- `summary`
  - 返回页面摘要。
- `extras`
  - 返回补充字段，例如链接集合。

### 2.7 请求示例

#### 示例 1：搜索时直接把 highlights 带回来

```bash
curl -X POST "https://api.exa.ai/search" \
  -H "x-api-key: YOUR-EXA-API-KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest research in llm agents",
    "type": "auto",
    "numResults": 5,
    "contents": {
      "highlights": true
    }
  }'
```

#### 示例 2：按论文类别 + 时间过滤 + 直接拿正文

```bash
curl -X POST "https://api.exa.ai/search" \
  -H "x-api-key: YOUR-EXA-API-KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "multimodal reasoning benchmark",
    "type": "deep-lite",
    "category": "research paper",
    "startPublishedDate": "2025-01-01T00:00:00.000Z",
    "numResults": 8,
    "contents": {
      "text": true,
      "summary": {}
    }
  }'
```

### 2.8 返回示例

```json
{
  "requestId": "b5947044c4b78efa9552a7c89b306d95",
  "results": [
    {
      "title": "Reasoning Language Models: A Survey",
      "url": "https://arxiv.org/abs/2501.01234",
      "publishedDate": "2025-01-10T00:00:00.000Z",
      "author": "Example Authors",
      "id": "https://arxiv.org/abs/2501.01234",
      "image": "https://arxiv.org/example.png",
      "favicon": "https://arxiv.org/favicon.ico",
      "text": "This survey reviews reasoning-focused language models...",
      "highlights": [
        "The paper compares chain-of-thought, verifier-based, and tool-using approaches."
      ],
      "highlightScores": [
        0.71
      ],
      "summary": "A survey of reasoning-oriented LLM approaches and evaluation methods.",
      "subpages": [],
      "extras": {
        "links": []
      }
    }
  ],
  "searchType": "auto",
  "output": null,
  "costDollars": {
    "total": 0.007,
    "breakDown": [
      {
        "search": 0.007,
        "contents": 0.0,
        "breakdown": {
          "neuralSearch": 0.007,
          "deepSearch": 0.012,
          "contentText": 0.0,
          "contentHighlight": 0.0,
          "contentSummary": 0.0
        }
      }
    ]
  }
}
```

### 2.9 返回字段说明

| 字段 | 说明 |
| --- | --- |
| `requestId` | 请求追踪 ID。 |
| `results[]` | 搜索结果。 |
| `results[].id` | Exa 结果 ID，可直接拿去调 `/contents`。 |
| `results[].text` | 当 `contents.text` 打开时出现。 |
| `results[].highlights` | 当 `contents.highlights` 打开时出现。 |
| `results[].summary` | 当 `contents.summary` 打开时出现。 |
| `results[].subpages` | 某些内容抓取模式下出现。 |
| `searchType` | `auto` 模式实际选择的搜索类型。 |
| `output` | 提供 `outputSchema` 时的综合输出。 |
| `costDollars` | 本次请求成本明细。 |

## 3. Contents API

### 3.1 接口定义

```http
POST https://api.exa.ai/contents
```

### 3.2 这个接口的特点

- 输入 URL 或 Exa 结果 ID。
- 优先从缓存返回。
- 缓存没有时会自动触发 live crawl 兜底。
- 更适合“给我这个页面的正文和摘要”。

### 3.3 关键请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `urls` | `string[]` | 条件必填 | URL 数组。 |
| `ids` | `string[]` | 条件必填 | 搜索结果里拿到的文档 ID。 |
| `text` | `boolean|object` | 否 | 返回正文。 |
| `highlights` | `object` | 否 | 返回与 query 相关的片段。 |
| `summary` | `object` | 否 | 返回页面摘要。 |
| `livecrawl` | `string` | 否 | 已 deprecated。 |
| `livecrawlTimeout` | `integer` | 否 | live crawl 超时，单位毫秒。 |
| `maxAgeHours` | `integer` | 否 | 控制缓存新鲜度和何时触发 live crawl。 |
| `subpages` | `integer` | 否 | 要抓多少子页面。 |
| `subpageTarget` | `string|string[]` | 否 | 希望找哪些子页面，例如 `api`、`reference`。 |
| `extras` | `object` | 否 | 返回额外字段。 |
| `context` | `boolean|object` | 否 | deprecated。 |

### 3.4 `maxAgeHours` 的含义

这是 `/contents` 很关键的一个参数：

- `24`
  - 如果缓存内容在 24 小时内，就直接用缓存；否则 live crawl。
- `0`
  - 永远 live crawl，不用缓存。
- `-1`
  - 永远只读缓存，不触发 live crawl。
- 不传
  - 只在没有缓存时 live crawl。

### 3.5 请求示例

#### 示例 1：按 URL 获取正文

```bash
curl -X POST "https://api.exa.ai/contents" \
  -H "x-api-key: YOUR-EXA-API-KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://arxiv.org/abs/2307.06435"],
    "text": true
  }'
```

#### 示例 2：要求内容新鲜，并抓相关子页面

```bash
curl -X POST "https://api.exa.ai/contents" \
  -H "x-api-key: YOUR-EXA-API-KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://platform.openai.com/docs/introduction"],
    "text": true,
    "summary": {},
    "maxAgeHours": 6,
    "subpages": 3,
    "subpageTarget": ["responses", "tools", "streaming"]
  }'
```

### 3.6 返回示例

```json
{
  "requestId": "e492118ccdedcba5088bfc4357a8a125",
  "results": [
    {
      "title": "Introduction - OpenAI API",
      "url": "https://platform.openai.com/docs/introduction",
      "publishedDate": "2026-04-30T12:00:00.000Z",
      "author": null,
      "id": "https://platform.openai.com/docs/introduction",
      "image": null,
      "favicon": "https://platform.openai.com/favicon.ico",
      "text": "# Introduction\n\nThe OpenAI API provides...",
      "summary": "Overview of the OpenAI platform and its API surfaces.",
      "subpages": [
        {
          "id": "https://platform.openai.com/docs/api-reference/responses",
          "url": "https://platform.openai.com/docs/api-reference/responses",
          "title": "Responses API",
          "text": "# Responses API\n\nCreate model responses..."
        }
      ],
      "extras": {
        "links": []
      }
    }
  ],
  "statuses": [
    {
      "id": "https://platform.openai.com/docs/introduction",
      "status": "success"
    }
  ],
  "costDollars": {
    "total": 0.001,
    "breakDown": [
      {
        "search": 0.0,
        "contents": 0.001,
        "breakdown": {
          "contentText": 0.001,
          "contentHighlight": 0.0,
          "contentSummary": 0.0
        }
      }
    ]
  }
}
```

### 3.7 `statuses[]` 很重要

`/contents` 和很多抓取类接口不同，常见的逐 URL 失败不会直接把整个 HTTP 请求打成错误，而是放在 `statuses[]` 里逐项返回。

也就是说：

- 顶层 HTTP 200
- 不代表每个 URL 都成功

你需要逐项检查：

- `statuses[].status`
- `statuses[].error.tag`
- `statuses[].error.httpStatusCode`

### 3.8 常见内容状态标签

官方文档中列出的 `/contents` per-URL 错误标签包括：

- `CRAWL_NOT_FOUND`
- `CRAWL_TIMEOUT`
- `CRAWL_LIVECRAWL_TIMEOUT`
- `SOURCE_NOT_AVAILABLE`
- `UNSUPPORTED_URL`
- `CRAWL_UNKNOWN_ERROR`

## 4. 费用与限流

### 4.1 Search / Contents 响应里会回传成本

Exa 的一个特点是响应体自带：

```json
{
  "costDollars": {
    "total": 0.007
  }
}
```

这使得你可以直接把单次请求成本记入日志或计费统计。

### 4.2 2026-03-03 官方价格更新

Exa 在 2026-03-03 的公开 changelog 写明：

- Search with contents：
  - 10 条结果以内的 text 和 highlights 已包含在基础请求里
  - 基础价约 `$7 / 1000 requests`
  - 超过 10 条的额外结果按增量计费
- Summaries：
  - `$1 / 1000 summaries`
- Deep：
  - `$12 / 1000 requests`
- Deep Reasoning：
  - `$15 / 1000 requests`
- `POST /contents`：
  - 仍按内容类型和页面数计费

接入代码里不要硬编码价格，优先使用响应里的 `costDollars`。

### 4.3 默认 rate limit

截至 2026-05-07，官方 rate limits 页面写的是：

- `/search`：10 QPS
- `/findSimilar`：10 QPS
- `/contents`：100 QPS
- `/answer`：10 QPS
- `/research`：15 个并发任务

## 5. 常见错误

官方 Error Codes 文档列出的典型 HTTP 错误包括：

- `400 Bad Request`
- `401 Unauthorized`
- `402 Payment Required`
- `403 Forbidden`
- `404 Not Found`
- `409 Conflict`
- `422 Unprocessable Entity`
- `429 Too Many Requests`
- `500 / 502 / 503`
- `501 Not Implemented`，只在 `/answer` 和 `/research` 更常见

### 5.1 错误返回形状

```json
{
  "requestId": "67207943fab9832d162b5317f4cca830",
  "error": "Invalid request body",
  "tag": "INVALID_REQUEST_BODY"
}
```

### 5.2 `429` 的返回形状较简单

```json
{
  "error": "You've exceeded your Exa rate limit of 10 requests per second."
}
```

## 6. 实战建议

- 只要你最终还是要看页面正文，优先在 `/search` 里直接开 `contents`，少一次往返。
- 需要控制内容新鲜度时，用 `/contents` 的 `maxAgeHours`，不要继续依赖 deprecated `livecrawl`。
- 对公司 / 人物垂直检索，不要混用不支持的时间和域名过滤参数。
- 如果你要自己做失败重试，优先检查 `/contents` 的 `statuses[]`，而不是只看 HTTP code。
- 需要真正的站点级 crawl 时，Exa 不是这四家里最完整的一类产品。

