# Tavily API 详细整理

- 核对日期：2026-05-07
- 文档范围：围绕 Tavily 里最贴近 `search`、`fetch/extract`、`crawl` 的接口整理，补充认证、限流、示例、返回形状和使用建议。
- 官方文档入口：
  - Introduction: https://docs.tavily.com/documentation/api-reference/introduction
  - Search: https://docs.tavily.com/documentation/api-reference/endpoint/search
  - Extract: https://docs.tavily.com/documentation/api-reference/endpoint/extract
  - Crawl: https://docs.tavily.com/documentation/api-reference/endpoint/crawl
  - Map: https://docs.tavily.com/documentation/api-reference/endpoint/map
  - Credits: https://docs.tavily.com/documentation/api-credits
  - Rate Limits: https://docs.tavily.com/documentation/rate-limits
  - Docs index: https://docs.tavily.com/llms.txt

## 1. 基础信息

### 1.1 Base URL

```text
https://api.tavily.com
```

### 1.2 鉴权

所有 REST 请求都使用 Bearer Token：

```http
Authorization: Bearer tvly-YOUR_API_KEY
Content-Type: application/json
```

### 1.3 Tavily 在这类场景里的接口分工

- `POST /search`
  - 给自然语言查询做搜索。
  - 可直接返回结果摘要、可选答案、可选清洗后的正文片段。
- `POST /extract`
  - 给一个或多个 URL，抽取网页正文。
  - 这是 Tavily 体系里最接近“fetch URL then extract clean text”的接口。
- `POST /crawl`
  - 从一个入口 URL 出发做站点级抓取。
  - 直接返回每一页的抽取结果。
- `POST /map`
  - 只做链接发现，不做内容抽取。
  - 当你想先发现站点路径，再分批调用 `/extract` 时有用。

## 2. Search API

### 2.1 接口定义

```http
POST https://api.tavily.com/search
```

### 2.2 适合什么场景

- 给 Agent 或 RAG 先做联网检索。
- 一次请求直接拿搜索结果、正文片段、可选答案。
- 查新闻、金融、通用网页搜索。
- 需要 domain filter、时间范围过滤、图片结果时。

### 2.3 关键请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | `string` | 是 | 搜索问题或检索语句。 |
| `search_depth` | `string` | 否 | 相关性和时延折中。官方可选：`basic`、`fast`、`ultra-fast`、`advanced`。 |
| `chunks_per_source` | `integer` | 否 | 只在 `advanced` 时可用，范围 `1-3`。 |
| `max_results` | `integer` | 否 | 返回结果数，范围 `0-20`，默认 `5`。 |
| `topic` | `string` | 否 | `general`、`news`、`finance`。 |
| `time_range` | `string` | 否 | `day/week/month/year` 或缩写 `d/w/m/y`。 |
| `start_date` | `string` | 否 | `YYYY-MM-DD`。 |
| `end_date` | `string` | 否 | `YYYY-MM-DD`。 |
| `include_answer` | `boolean|string` | 否 | `true` 或 `basic` 返回简短答案，`advanced` 返回更详细答案。 |
| `include_raw_content` | `boolean|string` | 否 | `true` 或 `markdown` 返回 markdown 正文，`text` 返回纯文本。 |
| `include_images` | `boolean` | 否 | 返回顶层图片列表，以及每条结果内的图片列表。 |
| `include_image_descriptions` | `boolean` | 否 | 需要 `include_images=true`。 |
| `include_favicon` | `boolean` | 否 | 每条结果带 favicon。 |
| `include_domains` | `string[]` | 否 | 限定只从这些域名取结果，最多 300。 |
| `exclude_domains` | `string[]` | 否 | 排除这些域名，最多 150。 |
| `country` | `string` | 否 | 国家倾向增强，仅 `topic=general` 时可用。 |
| `auto_parameters` | `boolean` | 否 | 让 Tavily 自动推断部分搜索参数。 |
| `exact_match` | `boolean` | 否 | 对 query 中带引号的短语做严格匹配。 |
| `include_usage` | `boolean` | 否 | 返回 credit 消耗信息。 |
| `safe_search` | `boolean` | 否 | Enterprise only，不支持 `fast` / `ultra-fast`。 |

### 2.4 `search_depth` 怎么选

- `ultra-fast`
  - 最低时延优先。
  - 更适合强实时、对内容片段精度要求不高的场景。
- `fast`
  - 比 `basic` 更追求速度。
  - 仍然会返回语义相关片段。
- `basic`
  - 默认值。
  - 适合作为通用联网搜索起点。
- `advanced`
  - 最强调相关性。
  - 支持更丰富的片段返回和更高精度，但成本更高。

### 2.5 请求示例

#### 示例 1：通用搜索，直接返回答案和正文

```bash
curl -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer tvly-YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "OpenAI Responses API latest official docs",
    "search_depth": "advanced",
    "max_results": 5,
    "topic": "general",
    "include_answer": "advanced",
    "include_raw_content": "markdown",
    "include_favicon": true,
    "include_usage": true
  }'
```

#### 示例 2：新闻搜索 + 时间过滤 + 域名约束

```bash
curl -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer tvly-YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI infrastructure funding news",
    "topic": "news",
    "time_range": "week",
    "include_domains": ["techcrunch.com", "theinformation.com"],
    "max_results": 10
  }'
```

### 2.6 返回示例

下面是按官方字段整理的代表性返回，不是官方原样响应：

```json
{
  "query": "OpenAI Responses API latest official docs",
  "answer": "Responses API is the current unified API surface for text, tool use, and multimodal flows.",
  "images": [],
  "results": [
    {
      "title": "Introduction - OpenAI API",
      "url": "https://platform.openai.com/docs/introduction",
      "content": "The OpenAI API provides a simple interface for building assistants and tool-using applications...",
      "score": 0.92,
      "raw_content": "# Introduction\n\nThe OpenAI API provides...",
      "favicon": "https://platform.openai.com/favicon.ico",
      "images": [
        {
          "url": "https://platform.openai.com/og-image.png",
          "description": "OpenAI platform hero image"
        }
      ]
    }
  ],
  "response_time": 1.41,
  "auto_parameters": {
    "topic": "general",
    "search_depth": "advanced"
  },
  "usage": {
    "credits": 2
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174111"
}
```

### 2.7 返回字段说明

| 字段 | 说明 |
| --- | --- |
| `query` | 实际执行的 query。 |
| `answer` | 仅在 `include_answer` 打开时出现。 |
| `images` | 顶层图片搜索结果。 |
| `results[]` | 排序后的搜索结果列表。 |
| `results[].title` | 页面标题。 |
| `results[].url` | 页面 URL。 |
| `results[].content` | Tavily 生成的摘要或语义片段。 |
| `results[].score` | 相关性分数。 |
| `results[].raw_content` | 仅在 `include_raw_content` 打开时出现。 |
| `results[].favicon` | 仅在 `include_favicon` 打开时出现。 |
| `results[].images` | 仅在 `include_images` 打开时出现。 |
| `response_time` | 服务端处理时长，单位秒。 |
| `auto_parameters` | 仅在 `auto_parameters=true` 时出现。 |
| `usage` | 仅在 `include_usage=true` 时出现。 |
| `request_id` | 排查请求时最好保留。 |

## 3. Extract API

### 3.1 接口定义

```http
POST https://api.tavily.com/extract
```

### 3.2 适合什么场景

- 已经有 URL，想直接拿网页正文。
- 不需要整站爬，只想抽正文。
- 需要 query-aware extraction，只返回长文里最相关的片段。
- 需要批量抽取多个页面。

### 3.3 关键请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `urls` | `string|string[]` | 是 | 单个 URL 或 URL 数组。 |
| `query` | `string` | 否 | 给抽取结果做相关性重排。 |
| `chunks_per_source` | `integer` | 否 | 只在提供 `query` 时可用，范围 `1-5`。 |
| `extract_depth` | `string` | 否 | `basic` / `advanced`。 |
| `include_images` | `boolean` | 否 | 返回页面图片列表。 |
| `include_favicon` | `boolean` | 否 | 返回 favicon。 |
| `format` | `string` | 否 | `markdown` 或 `text`，默认 `markdown`。 |
| `timeout` | `number` | 否 | `1-60` 秒。未指定时，`basic` 默认 10 秒，`advanced` 默认 30 秒。 |
| `include_usage` | `boolean` | 否 | 返回 credit 消耗。 |

### 3.4 请求示例

#### 示例 1：单 URL 提取正文

```bash
curl -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer tvly-YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": "https://docs.python.org/3/library/asyncio.html",
    "format": "markdown",
    "extract_depth": "basic",
    "include_favicon": true
  }'
```

#### 示例 2：按 query 只取最相关片段

```bash
curl -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer tvly-YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://docs.python.org/3/library/asyncio.html",
      "https://docs.python.org/3/library/contextvars.html"
    ],
    "query": "event loop and task scheduling",
    "chunks_per_source": 3,
    "extract_depth": "advanced",
    "format": "markdown",
    "include_usage": true
  }'
```

### 3.5 返回示例

```json
{
  "results": [
    {
      "url": "https://docs.python.org/3/library/asyncio.html",
      "raw_content": "# asyncio\n\nasyncio is a library to write concurrent code...",
      "images": [],
      "favicon": "https://docs.python.org/3/favicon.ico"
    }
  ],
  "failed_results": [],
  "response_time": 0.63,
  "usage": {
    "credits": 1
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174111"
}
```

### 3.6 返回字段说明

| 字段 | 说明 |
| --- | --- |
| `results[]` | 成功提取的页面。 |
| `results[].url` | 请求 URL。 |
| `results[].raw_content` | 提取后的正文内容。 |
| `results[].images` | 页面图片列表，需显式打开。 |
| `results[].favicon` | 页面 favicon，需显式打开。 |
| `failed_results[]` | 提取失败的 URL 列表。 |
| `response_time` | 请求耗时，单位秒。 |
| `usage` | credit 消耗。 |
| `request_id` | 请求追踪 ID。 |

## 4. Crawl API

### 4.1 接口定义

```http
POST https://api.tavily.com/crawl
```

### 4.2 适合什么场景

- 抓取一个站点或某个文档目录。
- 给知识库建库，直接拿每页内容。
- 通过路径筛选控制爬取范围。
- 用自然语言 `instructions` 限定 crawler 优先找什么。

### 4.3 关键请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `url` | `string` | 是 | 爬取入口 URL。 |
| `instructions` | `string` | 否 | 给 crawler 的自然语言指令。 |
| `chunks_per_source` | `integer` | 否 | 仅在提供 `instructions` 时可用，范围 `1-5`。 |
| `max_depth` | `integer` | 否 | 最大深度，范围 `1-5`。 |
| `max_breadth` | `integer` | 否 | 每层最多跟进多少链接，范围 `1-500`。 |
| `limit` | `integer` | 否 | 总处理页数上限，默认 `50`。 |
| `select_paths` | `string[]` | 否 | 用正则筛出特定路径。 |
| `select_domains` | `string[]` | 否 | 用正则筛出特定域名或子域。 |
| `exclude_paths` | `string[]` | 否 | 排除路径。 |
| `exclude_domains` | `string[]` | 否 | 排除域名。 |
| `allow_external` | `boolean` | 否 | 是否把外部域名链接也放进结果。默认 `true`。 |
| `include_images` | `boolean` | 否 | 返回页面图片。 |
| `extract_depth` | `string` | 否 | `basic` / `advanced`。 |
| `format` | `string` | 否 | `markdown` / `text`。 |
| `include_favicon` | `boolean` | 否 | 返回 favicon。 |
| `timeout` | `number` | 否 | `10-150` 秒，默认 `150`。 |
| `include_usage` | `boolean` | 否 | 返回 credit 消耗。 |

### 4.4 请求示例

```bash
curl -X POST "https://api.tavily.com/crawl" \
  -H "Authorization: Bearer tvly-YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://docs.tavily.com",
    "instructions": "Find pages about the Python SDK and API reference",
    "max_depth": 2,
    "max_breadth": 25,
    "limit": 30,
    "select_paths": ["/sdk/.*", "/documentation/api-reference/.*"],
    "extract_depth": "advanced",
    "format": "markdown",
    "include_favicon": true,
    "include_usage": true
  }'
```

### 4.5 返回示例

```json
{
  "base_url": "docs.tavily.com",
  "results": [
    {
      "url": "https://docs.tavily.com/sdk/python/quick-start",
      "raw_content": "# Python Quick Start\n\nInstall the SDK and initialize TavilyClient...",
      "images": [],
      "favicon": "https://docs.tavily.com/favicon.ico"
    },
    {
      "url": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
      "raw_content": "# Tavily Search\n\nExecute a search query using Tavily...",
      "images": [],
      "favicon": "https://docs.tavily.com/favicon.ico"
    }
  ],
  "response_time": 11.8,
  "usage": {
    "credits": 9
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174111"
}
```

### 4.6 关于 `instructions`

- `instructions` 会改变 crawl 的发现策略。
- 官方明确说明：带 `instructions` 时，mapping 成本会变成每 10 个成功页面 2 credits；不带时是每 10 个成功页面 1 credit。
- 如果你只想“尽量全量抓某个路径”，可以先不加 `instructions`。
- 如果你想“只找 SDK / API / pricing 页面”，加 `instructions` 往往更有效。

## 5. Map API

### 5.1 接口定义

```http
POST https://api.tavily.com/map
```

### 5.2 什么时候用

- 先只发现站点 URL，不要正文。
- 想先做 sitemap-like 枚举，再分批 `/extract`。
- 想减少不必要的正文提取成本。

### 5.3 返回形状

代表性返回：

```json
{
  "base_url": "docs.tavily.com",
  "results": [
    "https://docs.tavily.com/welcome",
    "https://docs.tavily.com/documentation/api-reference/endpoint/search",
    "https://docs.tavily.com/sdk/python/quick-start"
  ],
  "response_time": 1.23,
  "usage": {
    "credits": 1
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174111"
}
```

## 6. 计费与限流

### 6.1 Search credits

- `basic`、`fast`、`ultra-fast`：每次 1 credit
- `advanced`：每次 2 credits

### 6.2 Extract credits

- `basic`：每 5 个成功 URL 抽取 1 credit
- `advanced`：每 5 个成功 URL 抽取 2 credits

### 6.3 Crawl credits

- 总成本 = `mapping cost + extraction cost`
- 不带 `instructions` 时，mapping 是每 10 页 1 credit
- 带 `instructions` 时，mapping 是每 10 页 2 credits
- extraction 部分按 `extract_depth` 计费

### 6.4 官方默认 rate limit

截至 2026-05-07，官方文档写的是：

- 默认 API：
  - Development key：100 RPM
  - Production key：1000 RPM
- Crawl endpoint：
  - Development：100 RPM
  - Production：100 RPM
- Research endpoint：
  - Development：20 RPM
  - Production：20 RPM
- Usage endpoint：
  - Development：每 10 分钟 10 次
  - Production：每 10 分钟 10 次

### 6.5 429 处理

Tavily 会返回 `429 Too Many Requests`，并带 `retry-after` header。接入时应优先遵守这个 header，而不是自己硬编码重试间隔。

## 7. 错误与返回约定

官方接口页里常见状态码包括：

- `200`
- `400`
- `401`
- `403`
- `429`
- `432`
- `433`
- `500`

其中：

- `429` 是频率限制。
- `400` 常见于参数格式问题。
- `401` 常见于 API key 问题。
- 文档列出了 `432`、`433`，但在当前公开参考页中没有给出完整逐码解释；生产接入时建议保留原始响应体和 `request_id` 以便排查。

## 8. 实战建议

- 要“联网搜索并让 LLM 直接使用结果”，首选 `/search`。
- 要“给一批 URL 拉正文”，首选 `/extract`。
- 要“整站抓文档库”，首选 `/crawl`。
- 要“只发现链接，不急着抓正文”，先用 `/map`。
- 长页面做聚焦抽取时，优先给 `/extract` 加 `query`，避免把整页都塞进上下文。
- 对 Crawl，先收窄 `select_paths` 和 `limit`，再逐步放开，能明显降低成本。

