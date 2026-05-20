# 柳州地震任务执行记录与二次开发说明

## 1. 目的

本文档记录一次真实的生产任务调用与跟踪过程，目标是为后续开发者提供：

- 如何通过 API 创建任务
- 如何在运行中轮询任务状态
- 如何获取搜索统计、文档统计、LLM 调用链和最终报告
- `search_limit` 参数在系统里的真实语义
- 当前系统在真实 provider 场景下的典型行为与限制

本次样例主题：

- `5月柳州地震`

本次样例服务端：

- `root@172.23.16.175`
- API 基地址：`http://172.23.16.175:8000`
- 服务工作目录：`/home/llm_scheduling_management_system`

## 2. 鉴权说明

本次调用统一使用密码头：

- Header 名称：`X-LSMS-Password`

示例里统一使用占位符，不写入真实密码：

```http
X-LSMS-Password: <ACCESS_PASSWORD>
```

说明：

- 当前 `175` 服务器上 `config/access.toml` 实际缺失，因此服务端当前处于“未启用鉴权”的状态。
- 为了让调用方式对未来启用鉴权的场景保持兼容，本文档中的所有 API 示例仍然统一带 `X-LSMS-Password`。
- 如果后续在服务器上手工创建 `config/access.toml` 并启用鉴权，这批调用方式无需再改。

## 3. 搜索上限参数能否通过 API 传递

可以。

本系统的搜索上限参数是：

- `options.search_limit`

它的语义是：

- “单个 search provider 的请求结果上限”

不是：

- 所有 provider 的总结果上限

执行逻辑位于 `SearchFanoutExecutor.execute`，核心行为是：

- 从 `task.options_payload["search_limit"]` 读取上限
- 把同一个 `limit` 传给每一个被选中的 provider

因此：

- 如果你传 `search_limit = 50`
- 且启用了 4 个搜索渠道
- 那么系统会尝试向 4 个渠道分别请求最多 50 条结果

但要注意，最终每个渠道是否真的返回 50 条以上，取决于：

- provider 自身接口能返回多少
- 主题本身可检索结果数量
- provider 配额或限流状态
- 下游去重逻辑

本次实测中，虽然我们把 `search_limit` 设成了 `60`，但最终每个渠道的实际返回数仍然明显不同。

## 4. 本次调用前的预检查

### 4.1 查询搜索 provider 列表

作用：

- 确认当前服务端启用了哪些搜索渠道
- 为后续任务创建准备 `search_provider_names`

调用：

```bash
curl -H "X-LSMS-Password: <ACCESS_PASSWORD>" \
  http://172.23.16.175:8000/api/v1/provider-catalog/search
```

结果摘要：

- `exa_search`
- `tavily_search`
- `grok_search`
- `gpt_search`

### 4.2 查询 provider 健康状态

作用：

- 在正式创建任务前，检查 provider 当前是否可用

调用：

```bash
curl -H "X-LSMS-Password: <ACCESS_PASSWORD>" \
  http://172.23.16.175:8000/api/v1/provider-catalog/health
```

结果摘要：

- 本次在 `175` 上调用该接口时，60 秒超时
- 这说明 provider 健康检查适合作为运维辅助，不适合阻塞正式任务创建

开发建议：

- 如果做控制台或自动化任务创建页面，不建议把 `/provider-catalog/health` 作为“必过前置”
- 更合理的方式是异步展示健康检查结果，不阻断任务发起

### 4.3 查询系统状态

作用：

- 记录调用时的系统基线

调用：

```bash
curl -H "X-LSMS-Password: <ACCESS_PASSWORD>" \
  http://172.23.16.175:8000/api/v1/system/status
```

结果摘要：

- 模板数：`4`
- 搜索 provider 数：`4`
- 抓取 provider 数：`2`
- LLM provider 数：`3`
- LLM profile 数：`4`
- 任务总数（调用前）：`8`

## 5. 正式创建任务

本次使用通用接口：

- `POST /api/v1/tasks`

而不是快捷接口：

- `POST /api/v1/reports/public-opinion`

原因：

- `POST /api/v1/tasks` 更适合做二次开发样例
- 可以完整展示 `template_id / input / options / tenant_id`
- 后续做前端、SDK、自动化编排时复用价值更高

### 5.1 请求体

```json
{
  "template_id": "public_opinion_report_v1",
  "tenant_id": "default",
  "input": {
    "topic": "5月柳州地震"
  },
  "options": {
    "disable_cache": true,
    "search_provider_names": [
      "exa_search",
      "tavily_search",
      "grok_search",
      "gpt_search"
    ],
    "search_limit": 60,
    "fetch_provider_name": "exa_contents",
    "llm_profile_name": "advanced_reasoning_cn",
    "report_retry_count": 2,
    "llm_model_retry_count": 2,
    "report_fallback_profile_names": [
      "grok_reasoning_optional",
      "claude_opus_web_search_optional",
      "cheap_structured_cn"
    ],
    "execution_engine": "langgraph"
  }
}
```

### 5.2 字段作用

- `template_id`
  - 选择工作流模板
  - 本次使用 `public_opinion_report_v1`

- `tenant_id`
  - 多租户隔离标识
  - 当前样例使用 `default`

- `input.topic`
  - 任务主题

- `options.disable_cache`
  - 关闭缓存，保证这次是一次真实的新执行

- `options.search_provider_names`
  - 显式指定使用哪些搜索渠道

- `options.search_limit`
  - 每个搜索渠道请求的结果上限
  - 本次设为 `60`
  - 目的是尽量接近“每渠道 50+ 篇”的目标

- `options.fetch_provider_name`
  - 指定正文抓取渠道

- `options.llm_profile_name`
  - 指定主 LLM profile

- `options.report_retry_count`
  - 报告生成阶段允许重试次数

- `options.llm_model_retry_count`
  - 单模型调用允许重试次数

- `options.report_fallback_profile_names`
  - 主 profile 失败后允许回退的 profile 链

- `options.execution_engine`
  - 指定执行引擎
  - 本次使用 `langgraph`

### 5.3 创建调用

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-LSMS-Password: <ACCESS_PASSWORD>" \
  http://172.23.16.175:8000/api/v1/tasks \
  -d '{
    "template_id":"public_opinion_report_v1",
    "tenant_id":"default",
    "input":{"topic":"5月柳州地震"},
    "options":{
      "disable_cache":true,
      "search_provider_names":["exa_search","tavily_search","grok_search","gpt_search"],
      "search_limit":60,
      "fetch_provider_name":"exa_contents",
      "llm_profile_name":"advanced_reasoning_cn",
      "report_retry_count":2,
      "llm_model_retry_count":2,
      "report_fallback_profile_names":["grok_reasoning_optional","claude_opus_web_search_optional","cheap_structured_cn"],
      "execution_engine":"langgraph"
    }
  }'
```

### 5.4 创建响应

```json
{
  "task_id": "run_e9bb4f83eae145edad3e86fe",
  "status": "queued",
  "progress": 5.0,
  "query_url": "/api/v1/tasks/run_e9bb4f83eae145edad3e86fe"
}
```

本次任务 ID：

- `run_e9bb4f83eae145edad3e86fe`

## 6. 运行过程轮询

轮询接口：

- `GET /api/v1/tasks/{task_id}`

作用：

- 获取任务总体状态
- 查看当前步骤 `current_step`
- 查看总进度 `progress`
- 查看已完成步骤数

轮询示例：

```bash
curl -H "X-LSMS-Password: <ACCESS_PASSWORD>" \
  http://172.23.16.175:8000/api/v1/tasks/run_e9bb4f83eae145edad3e86fe
```

### 6.1 关键轮询快照

| 轮询序号 | 状态 | 进度 | 当前步骤 | 已完成/总步骤 | updated_at |
| --- | --- | --- | --- | --- | --- |
| 1 | running | 5.0 | search_fanout | 1/9 | 2026-05-20T08:12:35 |
| 2 | running | 5.0 | search_fanout | 1/9 | 2026-05-20T08:12:35 |
| 3 | running | 22.22 | fetch_documents | 2/9 | 2026-05-20T08:13:52 |
| 4 | running | 22.22 | fetch_documents | 2/9 | 2026-05-20T08:13:52 |
| 5 | running | 22.22 | fetch_documents | 2/9 | 2026-05-20T08:13:52 |
| 6 | running | 22.22 | fetch_documents | 2/9 | 2026-05-20T08:13:52 |
| 7 | running | 22.22 | fetch_documents | 2/9 | 2026-05-20T08:13:52 |
| 8 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 9 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 10 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 11 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 12 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 13 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 14 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 15 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 16 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 17 | running | 88.89 | generate_public_opinion_report | 8/9 | 2026-05-20T08:16:04 |
| 18 | succeeded | 100.0 | generate_public_opinion_report | 9/9 | 2026-05-20T08:19:44 |

### 6.2 过程解读

- `search_fanout`
  - 执行多渠道检索
  - 这一阶段结束后会写入搜索调用记录和检索命中 artifact

- `fetch_documents`
  - 按命中文章 URL 拉取正文
  - 本次任务在这个阶段耗时明显最长

- `generate_public_opinion_report`
  - 使用聚合后的正文、时间线、官方回应和观点分段生成最终报告
  - 本次任务在最后阶段也有明显耗时

## 7. 完成后的结果采集

### 7.1 任务总体结果

- `task_id`: `run_e9bb4f83eae145edad3e86fe`
- `status`: `succeeded`
- `progress`: `100.0`
- `created_at`: `2026-05-20T08:12:34`
- `started_at`: `2026-05-20T08:12:35`
- `ended_at`: `2026-05-20T08:19:43`
- `template_id`: `public_opinion_report_v1`

说明：

- 任务端到端耗时约 7 分 8 秒

### 7.2 任务统计

来自：

- `GET /api/v1/tasks/{task_id}/stats`

关键统计：

- `planned_step_count`: `9`
- `completed_step_count`: `9`
- `artifact_count`: `9`
- `document_count`: `76`
- `search_hit_count`: `76`
- `search_invocation_count`: `4`
- `fetch_invocation_count`: `76`
- `llm_invocation_count`: `4`
- `event_count`: `27`

### 7.3 搜索调用统计

来自：

- `GET /api/v1/tasks/{task_id}/search-invocations`

本次各 provider 的原始返回条数：

| Provider | 请求 limit | 实际 result_count | 备注 |
| --- | --- | --- | --- |
| `exa_search` | 60 | 60 | 正常返回满额 |
| `gpt_search` | 60 | 12 | 实际只返回 12 条 |
| `tavily_search` | 60 | 8 | 实际只返回 8 条 |
| `grok_search` | 60 | 0 | 请求返回 `429` |

关键信息：

- 系统确实把 `search_limit=60` 传给了所有 provider
- 但是否返回 60 条，完全取决于 provider 自身能力和状态
- `grok_search` 在本次执行中因为 `429` 没有返回任何结果

### 7.4 去重后的命中文章数

来自：

- `GET /api/v1/tasks/{task_id}/search-hits`

去重后按 `provider_name` 统计：

| Provider | 去重后命中数 |
| --- | --- |
| `exa_search` | 60 |
| `gpt_search` | 11 |
| `tavily_search` | 5 |

说明：

- 原始搜索调用返回总数：`60 + 12 + 8 + 0 = 80`
- 去重后保留下来的总命中数：`76`
- 差异来自跨 provider URL 重复

### 7.5 正文抓取统计

来自：

- `GET /api/v1/tasks/{task_id}/documents`

本次全部由：

- `exa_contents`

完成正文抓取。

抓取成功文档总数：

- `76`

### 7.6 LLM 调用链

来自：

- `GET /api/v1/tasks/{task_id}/llm-invocations`

本次调用链：

| 调用序号 | profile_name | model_name |
| --- | --- | --- |
| 1 | `advanced_reasoning_cn` | `gpt-5.4` |
| 2 | `advanced_reasoning_cn` | `gpt-5.4` |
| 3 | `advanced_reasoning_cn` | `gpt-5.4` |
| 4 | `cheap_structured_cn` | `gpt-4o-mini` |

说明：

- 主 profile `advanced_reasoning_cn` 并没有直接完成最终输出
- 最终成功落在 fallback profile：
  - `cheap_structured_cn`
  - `gpt-4o-mini`

开发启示：

- 如果后续要做“执行观测台”或“失败归因”，LLM fallback 链必须显式展示
- 仅看任务最终成功状态，无法知道中间曾发生了多少次模型重试或回退

## 8. 最终报告

最终报告接口：

- `GET /api/v1/tasks/{task_id}/final-report`

关键字段：

- `ready`: `true`
- `report_state`: `ready`
- `artifact_id`: `art_2961f6bc75534865bd9e9c6b`
- `step_run_id`: `step_c10852dddb9c4c8ab7d173f8`
- `generated_at`: `2026-05-20T08:19:43`
- `llm_profile_name`: `cheap_structured_cn`
- `llm_model_name`: `gpt-4o-mini`
- `timeline_count`: `76`
- `official_response_count`: `75`
- `media_viewpoint_count`: `10`
- `public_viewpoint_count`: `1`

### 8.1 报告内容摘要

最终报告的核心结论包括：

- 事件主体为 `2026-05-18` 柳州市柳南区两次 `5.2` 级地震
- 报告梳理了：
  - 事件脉络
  - 官方回应
  - 媒体观点
  - 网民观点
  - 舆情启示
  - 深度舆情结论
- 最终报告认为：
  - 本次事件整体属于“权威信息主导下较平稳演进的突发舆情案例”
  - 官方信息发布较快，科学解读和协同响应有效压制了恐慌和谣言扩散

### 8.2 一个重要观察

本次最终报告中的网民观点部分，明确写到：

- “原生社交媒体样本不足”

这说明：

- 即使总命中文章数已经较多
- 如果搜索源仍以新闻站点为主
- 最终“网民观点”类分析仍然可能样本不足

开发启示：

- 如果后续要强化“公众观点”分析质量，需要补充更强的社交媒体或论坛型数据源

## 9. 对“每渠道 50 篇以上”的真实结论

本次任务中我们已经把：

- `search_limit` 设为 `60`

但真实结果是：

- `exa_search` 返回 `60`
- `gpt_search` 返回 `12`
- `tavily_search` 返回 `8`
- `grok_search` 返回 `0`，且是 `429`

结论：

- **可以通过 API 传递“每渠道请求 50+ 条”的意图**
- **不能保证每个渠道都真的返回 50+ 条**

如果业务上必须要“每渠道最终有效文章 >= 50”，则需要新增更严格的控制逻辑，例如：

- 在任务执行层增加 provider 最低结果数校验
- 结果不足时自动补搜
- 当某 provider 返回 `429` 时自动降级或切换备用 provider
- 把“原始返回数”和“去重后保留数”分开持久化并展示

## 10. 推荐给后续开发者的 API 调用顺序

建议的调用顺序如下：

1. `GET /api/v1/provider-catalog/search`
   - 确认可用搜索渠道

2. `GET /api/v1/system/status`
   - 获取系统基线

3. `POST /api/v1/tasks`
   - 发起任务

4. `GET /api/v1/tasks/{task_id}`
   - 轮询状态、当前步骤、进度

5. `GET /api/v1/tasks/{task_id}/search-invocations`
   - 统计各 provider 原始返回量

6. `GET /api/v1/tasks/{task_id}/search-hits`
   - 获取去重后的检索命中

7. `GET /api/v1/tasks/{task_id}/documents`
   - 获取已抓取正文

8. `GET /api/v1/tasks/{task_id}/llm-invocations`
   - 获取模型调用链与回退情况

9. `GET /api/v1/tasks/{task_id}/final-report`
   - 获取最终结果

## 11. 推荐的最小调用示例

### 11.1 创建任务

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-LSMS-Password: <ACCESS_PASSWORD>" \
  http://172.23.16.175:8000/api/v1/tasks \
  -d '{
    "template_id":"public_opinion_report_v1",
    "tenant_id":"default",
    "input":{"topic":"5月柳州地震"},
    "options":{
      "disable_cache":true,
      "search_provider_names":["exa_search","tavily_search","grok_search","gpt_search"],
      "search_limit":60,
      "fetch_provider_name":"exa_contents",
      "llm_profile_name":"advanced_reasoning_cn",
      "report_retry_count":2,
      "llm_model_retry_count":2,
      "report_fallback_profile_names":["grok_reasoning_optional","claude_opus_web_search_optional","cheap_structured_cn"],
      "execution_engine":"langgraph"
    }
  }'
```

### 11.2 轮询任务

```bash
curl -H "X-LSMS-Password: <ACCESS_PASSWORD>" \
  http://172.23.16.175:8000/api/v1/tasks/run_e9bb4f83eae145edad3e86fe
```

### 11.3 拉取最终报告

```bash
curl -H "X-LSMS-Password: <ACCESS_PASSWORD>" \
  http://172.23.16.175:8000/api/v1/tasks/run_e9bb4f83eae145edad3e86fe/final-report
```

## 12. 本次执行的结论

本次真实执行证明了以下几点：

- 系统已经可以支撑完整的“创建任务 -> 多源检索 -> 正文抓取 -> 结构化分析 -> 最终报告”闭环
- `search_limit` 可以通过 API 传递，并且是按 provider 生效
- 真实 provider 返回量差异很大，不能把“请求上限”误当成“结果保证”
- `grok_search` 这类 provider 在真实环境下可能出现 `429`
- 最终报告有可能通过 fallback profile 才成功产出
- 如果后续要做面向业务方的“稳定结果承诺”，需要对 provider 配额、最小结果数、补搜和重试链做更强控制

