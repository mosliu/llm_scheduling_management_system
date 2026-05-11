# Grok 4.20 搜索能力使用说明

- 核对日期：2026-05-07
- 适用范围：xAI 官方 API 中，使用 Grok 4.20 的联网搜索能力
- 主要官方文档：
  - Docs 首页：https://docs.x.ai/docs
  - Grok 4 模型页：https://docs.x.ai/developers/models/grok-4
  - Quickstart：https://docs.x.ai/docs/tutorial
  - Generate Text / Responses API：https://docs.x.ai/developers/model-capabilities/text/generate-text
  - Web Search：https://docs.x.ai/developers/tools/web-search
  - X Search：https://docs.x.ai/developers/tools/x-search
  - Citations：https://docs.x.ai/developers/tools/citations
  - Tools Overview：https://docs.x.ai/docs/guides/tools/overview
  - Comparison with Chat Completions：https://docs.x.ai/docs/guides/chat/comparison

## 1. 先说结论

如果你要用 Grok 4.20 的“搜索能力”，不是调用一个独立的 `search` HTTP API。

正确方式是：

1. 调用 xAI 的 `Responses API`
2. 选择 `grok-4.20-reasoning` 或 `grok-4.20-non-reasoning`
3. 在 `tools` 里打开：
   - `web_search`：搜网页
   - `x_search`：搜 X

也就是说，Grok 的搜索能力是模型内置工具，不是 Tavily / Exa / Firecrawl 那种单独的 Search REST 端点。

## 2. 当前推荐模型名

截至 2026-05-07，xAI 官方文档中常见的 Grok 4.20 API 模型名包括：

- `grok-4.20-reasoning`
- `grok-4.20-non-reasoning`
- `grok-4.20-multi-agent`

如果你的目标是“联网搜索 + 阅读来源 + 整理答案”，默认推荐：

- `grok-4.20-reasoning`

原因：

- 更适合搜索后归纳
- 更适合多来源汇总
- 更适合带引用回答

补充：

- `reasoning_effort` 不适用于 `grok-4.20` 或 `grok-4-1-fast`
- 如果给这些模型传 `reasoning_effort`，官方文档说明会报错
- `grok-4.20-multi-agent` 的 `reasoning` 参数也不是“思考深度”，而是 agent 数量配置

## 3. Base URL 和鉴权

### 3.1 Base URL

```text
https://api.x.ai/v1
```

### 3.2 鉴权

```http
Authorization: Bearer YOUR_XAI_API_KEY
Content-Type: application/json
```

### 3.3 最重要的端点

```http
POST /responses
```

Grok 搜索能力的主要入口就是：

```http
POST https://api.x.ai/v1/responses
```

## 4. 最小可用调用

### 4.1 `curl`：网页搜索

```bash
curl https://api.x.ai/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -d '{
    "model": "grok-4.20-reasoning",
    "input": [
      {
        "role": "user",
        "content": "搜索最近一周关于 OpenAI Responses API 的官方更新，并用中文总结"
      }
    ],
    "tools": [
      {
        "type": "web_search"
      }
    ]
  }'
```

### 4.2 最小返回怎么理解

响应里你最常用的是：

- `id`
- `output`
- `output_text`
- `citations`

一个代表性返回形状可以理解成：

```json
{
  "id": "resp_01jt5c2m9z1f2x4h0n5a8a1cde",
  "object": "response",
  "model": "grok-4.20-reasoning",
  "status": "completed",
  "output": [
    {
      "id": "msg_01jt5c2s7f0jtwj6n8x8v8n7pn",
      "type": "message",
      "role": "assistant",
      "status": "completed",
      "content": [
        {
          "type": "output_text",
          "text": "最近一周官方更新主要集中在 Responses API 的工具调用和多模态支持……",
          "annotations": []
        }
      ]
    }
  ],
  "output_text": "最近一周官方更新主要集中在 Responses API 的工具调用和多模态支持……",
  "citations": [
    {
      "url": "https://platform.openai.com/docs/introduction",
      "title": "Introduction - OpenAI API"
    }
  ]
}
```

实际接入时，优先读取：

```text
response.output_text
```

如果你还要展示来源，再读取：

```text
response.citations
```

## 5. Python 调用

### 5.1 用 OpenAI Python SDK 直连 xAI

xAI 官方文档明确支持用 OpenAI 兼容 SDK，只需要改 `base_url`。

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

response = client.responses.create(
    model="grok-4.20-reasoning",
    input=[
        {
            "role": "user",
            "content": "搜索最近一周 AI agent 相关的官方发布，并用中文列出 5 条结论",
        }
    ],
    tools=[
        {
            "type": "web_search",
        }
    ],
)

print(response.output_text)

if hasattr(response, "citations"):
    print(response.citations)
```

### 5.2 用 xAI SDK

```python
import os
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import web_search

client = Client(api_key=os.getenv("XAI_API_KEY"))

chat = client.chat.create(
    model="grok-4.20-reasoning",
    tools=[web_search()],
)

chat.append(user("搜索最近的 API 搜索工具更新，并总结要点"))

response = chat.sample()
print(response.content)
print(response.citations)
```

## 6. JavaScript 调用

### 6.1 用 OpenAI JS SDK

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.XAI_API_KEY,
  baseURL: "https://api.x.ai/v1",
});

const response = await client.responses.create({
  model: "grok-4.20-reasoning",
  input: [
    {
      role: "user",
      content: "搜索最近的 browser automation API 变化，并用中文总结",
    },
  ],
  tools: [
    {
      type: "web_search",
    },
  ],
});

console.log(response.output_text);
console.log(response.citations);
```

### 6.2 用 Vercel AI SDK

```javascript
import { xai } from "@ai-sdk/xai";
import { generateText } from "ai";

const { text, sources } = await generateText({
  model: xai.responses("grok-4.20-reasoning"),
  prompt: "搜索最近的 API 搜索工具更新，并总结要点",
  tools: {
    web_search: xai.tools.webSearch(),
  },
});

console.log(text);
console.log(sources);
```

## 7. `web_search` 的参数

截至 2026-05-07，xAI 官方 Web Search 文档列出的主要参数是：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `allowed_domains` | `string[]` | 只允许搜索这些域名，最多 5 个 |
| `excluded_domains` | `string[]` | 排除这些域名，最多 5 个 |
| `enable_image_understanding` | `boolean` | 允许分析搜索过程中看到的图片 |

约束：

- `allowed_domains` 和 `excluded_domains` 不能同时设置

### 7.1 只允许搜索指定域名

```python
response = client.responses.create(
    model="grok-4.20-reasoning",
    input=[
        {
            "role": "user",
            "content": "搜索 Responses API 的最新官方说明，并整理成中文摘要"
        }
    ],
    tools=[
        {
            "type": "web_search",
            "filters": {
                "allowed_domains": ["platform.openai.com"]
            }
        }
    ],
)
```

### 7.2 排除某些域名

```python
response = client.responses.create(
    model="grok-4.20-reasoning",
    input=[
        {
            "role": "user",
            "content": "搜索最新的 agent framework 讨论"
        }
    ],
    tools=[
        {
            "type": "web_search",
            "filters": {
                "excluded_domains": ["reddit.com", "medium.com"]
            }
        }
    ],
)
```

### 7.3 开启图片理解

```python
response = client.responses.create(
    model="grok-4.20-reasoning",
    input=[
        {
            "role": "user",
            "content": "搜索最近发布的 AI agent 架构图，并解释图里的主要组件"
        }
    ],
    tools=[
        {
            "type": "web_search",
            "filters": {
                "enable_image_understanding": true
            }
        }
    ],
)
```

注意：

- 上面这个 JSON 风格参数结构是按官方文档写法整理的
- 如果你用的是 Python 字典，布尔值要写 `True`，不是 `true`

正确 Python 写法：

```python
response = client.responses.create(
    model="grok-4.20-reasoning",
    input=[{"role": "user", "content": "搜索最近发布的 AI agent 架构图，并解释图里的主要组件"}],
    tools=[
        {
            "type": "web_search",
            "filters": {
                "enable_image_understanding": True
            }
        }
    ],
)
```

## 8. `x_search` 的参数

如果你还想让 Grok 搜 X 平台，可以同时开 `x_search`。

官方文档列出的常用参数包括：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `allowed_x_handles` | `string[]` | 只允许这些账号，最多 10 个 |
| `excluded_x_handles` | `string[]` | 排除这些账号，最多 10 个 |
| `from_date` | `string` | 开始日期，ISO 8601 |
| `to_date` | `string` | 结束日期，ISO 8601 |
| `enable_image_understanding` | `boolean` | 分析 X 帖子中的图片 |
| `enable_video_understanding` | `boolean` | 分析 X 帖子中的视频 |

### 8.1 只搜 `@xai`

```python
response = client.responses.create(
    model="grok-4.20-reasoning",
    input=[
        {
            "role": "user",
            "content": "总结 xAI 最近一周的重要公开动态"
        }
    ],
    tools=[
        {
            "type": "x_search",
            "allowed_x_handles": ["xai"],
            "from_date": "2026-05-01",
            "to_date": "2026-05-07"
        }
    ],
)
```

### 8.2 网页搜索和 X 搜索一起开

```python
response = client.responses.create(
    model="grok-4.20-reasoning",
    input=[
        {
            "role": "user",
            "content": "总结 xAI 最近发布的产品更新，优先官方网页和官方 X 账号"
        }
    ],
    tools=[
        {"type": "web_search"},
        {
            "type": "x_search",
            "allowed_x_handles": ["xai"]
        }
    ],
)
```

## 9. Citations 怎么处理

xAI 官方文档说明，搜索类工具支持 citations。

你通常会遇到两种形式：

- `response.citations`
- 输出正文里的 inline citations

### 9.1 默认用途

- `output_text` 给最终答案
- `citations` 给来源展示

### 9.2 不想要正文里的内联引用

官方文档说明，可以通过 `include=["no_inline_citations"]` 关闭 inline citations。

```python
response = client.responses.create(
    model="grok-4.20-reasoning",
    input=[
        {
            "role": "user",
            "content": "搜索最近的 API 搜索工具变化，并用中文总结"
        }
    ],
    tools=[{"type": "web_search"}],
    include=["no_inline_citations"],
)
```

## 10. 多轮对话怎么继续

Responses API 是官方推荐方式，一个重要原因是它支持延续上一次响应。

你可以在下一轮请求里传：

- `previous_response_id`

这样不需要把完整历史都重新发一遍。

### 10.1 示例

```python
first = client.responses.create(
    model="grok-4.20-reasoning",
    input=[
        {
            "role": "user",
            "content": "搜索最近一周 AI 搜索 API 的主要更新"
        }
    ],
    tools=[{"type": "web_search"}],
)

second = client.responses.create(
    model="grok-4.20-reasoning",
    previous_response_id=first.id,
    input=[
        {
            "role": "user",
            "content": "把刚才结果整理成适合产品评审会的 5 条 bullet"
        }
    ],
)

print(second.output_text)
```

## 11. `store` 要不要关

xAI 官方文档说明，Responses API 支持服务端存储会话。

常见做法：

- 默认情况：不显式关闭，便于用 `previous_response_id`
- 隐私敏感：设置 `store=False`

### 11.1 示例

```python
response = client.responses.create(
    model="grok-4.20-reasoning",
    store=False,
    input=[
        {
            "role": "user",
            "content": "搜索最近的 AI 搜索 API 更新"
        }
    ],
    tools=[{"type": "web_search"}],
)
```

注意：

- 如果你设置了 `store=False`
- 后续继续会话时，不能依赖服务端长期持久化的 `previous_response_id`
- 你就需要自己管理上下文，或者使用文档里提到的 encrypted reasoning/content 机制

## 12. 超时和稳定性建议

搜索 + reasoning 往往比普通问答更慢，尤其是：

- 查询范围很大
- 来源很多
- 还要生成长总结

建议：

- 客户端 timeout 适当放大
- 对长任务优先用 streaming
- 结果展示时保留 `response.id`
- 错误日志里保留请求参数和 citations

一个较稳妥的 Python timeout 例子：

```python
import httpx
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_XAI_API_KEY",
    base_url="https://api.x.ai/v1",
    timeout=httpx.Timeout(3600.0),
)
```

## 13. 和 Tavily / Exa / Firecrawl 的本质差异

如果你已经在看别家的 Search API，这里要明确区分：

- Tavily / Exa / Firecrawl：
  - 更像“把搜索或抓取能力直接作为 API 服务暴露”
  - 你自己控制搜索、抓取、提取流程
- Grok 4.20：
  - 更像“模型在回答时自动调用搜索工具”
  - 你得到的是搜索增强后的最终答案和引用

所以 Grok 更适合：

- 直接问答
- 搜索后整理
- 带引用总结
- Agent 类任务

而不太像：

- 自己搭可控 crawler pipeline
- 单独拉取结构化 SERP 数据
- 自己精细控制网页抓取链路

## 14. 什么时候适合用 Grok 搜索

适合：

- 你要“问问题，然后联网总结”
- 你要“给用户一个带引用答案”
- 你要“网页搜索 + X 搜索一起做”
- 你要“搜索结果直接进入模型推理”

不太适合：

- 你只想要原始搜索结果列表，不要模型总结
- 你要独立的 crawl / fetch / extract 数据管线
- 你要严格控制每个搜索步骤和抓取步骤

## 15. 推荐接入方式

如果你要把 Grok 4.20 加进你现有的搜索系统，建议按这个思路：

1. 把 Grok 当作“搜索增强问答模型”，不是单独 Search API
2. 默认模型用 `grok-4.20-reasoning`
3. 默认工具开 `web_search`
4. 如果你业务很依赖 X，再加 `x_search`
5. 如果只允许官方站点，务必用 `allowed_domains`
6. 输出里同时保留：
   - `output_text`
   - `citations`
   - `response.id`

## 16. 一个完整 Python 示例

这个例子适合直接抄进项目里做最小接入：

```python
import os
import httpx
from openai import OpenAI


def ask_grok_with_web_search(prompt: str) -> dict:
    client = OpenAI(
        api_key=os.getenv("XAI_API_KEY"),
        base_url="https://api.x.ai/v1",
        timeout=httpx.Timeout(300.0),
    )

    response = client.responses.create(
        model="grok-4.20-reasoning",
        input=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        tools=[
            {
                "type": "web_search",
            }
        ],
        include=["no_inline_citations"],
    )

    return {
        "response_id": response.id,
        "text": getattr(response, "output_text", ""),
        "citations": getattr(response, "citations", []),
        "raw_response": response.model_dump() if hasattr(response, "model_dump") else response,
    }


if __name__ == "__main__":
    result = ask_grok_with_web_search(
        "搜索最近一周关于 Responses API 的官方更新，并整理成中文摘要"
    )
    print(result["response_id"])
    print(result["text"])
    print(result["citations"])
```

## 17. 最后一句话

如果你问“Grok 4.20 的搜索怎么调用”，标准答案就是：

- 调 `POST /v1/responses`
- 选 `grok-4.20-reasoning`
- 在 `tools` 里加 `{"type": "web_search"}`

如果你要搜 X，再加：

- `{"type": "x_search"}`

