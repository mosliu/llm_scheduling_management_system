# API Design

## 1. Goal

Expose a stable external API for:

- task creation
- task query
- task control
- step inspection
- artifact inspection
- checkpoint resume
- artifact-based fork
- workflow template discovery
- provider catalog inspection
- runtime lineage and invocation inspection

The same API should support both external integrators and internal UI pages.

## 2. API Style

Recommended style:

- REST for command and query APIs
- optional SSE for progress updates

## 3. Core Endpoints

## 3.1 Create Task

`POST /api/v1/tasks`

Purpose:

- create one asynchronous workflow task

Request example:

```json
{
  "template_id": "public_opinion_analysis_v1",
  "input": {
    "topic": "example topic",
    "time_range": {
      "start": "2026-05-01T00:00:00Z",
      "end": "2026-05-09T00:00:00Z"
    }
  },
  "options": {
    "priority": "normal",
    "source_policy": {
      "include_foreign_as_supplement": true,
      "time_window_days": 7
    },
    "llm_profile_overrides": {
      "final_report_generate": "advanced_reasoning_cn"
    }
  },
  "idempotency_key": "biz-key-001"
}
```

Response example:

```json
{
  "task_id": "run_01JXXX",
  "status": "queued",
  "progress": 0,
  "query_url": "/api/v1/tasks/run_01JXXX"
}
```

## 3.2 Query Task

`GET /api/v1/tasks/{task_id}`

Suggested query flags:

- `include=steps`
- `include=artifacts`
- `include=checkpoints`

Response example:

```json
{
  "task_id": "run_01JXXX",
  "template_id": "public_opinion_analysis_v1",
  "status": "running",
  "progress": 46,
  "current_step": "merge_search_results",
  "started_at": "2026-05-09T01:00:00Z",
  "updated_at": "2026-05-09T01:03:20Z",
  "steps": [
    {
      "step_run_id": "step_001",
      "node_key": "provider_search_news_api",
      "title": "Search provider A",
      "status": "succeeded",
      "progress": 100,
      "artifact_ids": ["art_001"],
      "cache_hit": false
    }
  ],
  "available_checkpoints": [
    {
      "checkpoint_id": "cp_001",
      "based_on_step_run_id": "step_005",
      "artifact_ids": ["art_010"]
    }
  ]
}
```

## 3.3 List Task Steps

`GET /api/v1/tasks/{task_id}/steps`

Purpose:

- fetch step timeline without full task envelope

## 3.3A Task Control

The current implementation supports:

- `POST /api/v1/tasks/{task_id}/run`
- `POST /api/v1/tasks/{task_id}/run-next-step`
- `POST /api/v1/tasks/{task_id}/cancel`

Purpose:

- run the remaining workflow
- advance one pending step at a time
- cancel a queued or running task

## 3.3B Task Runtime Views

The current implementation supports:

- `GET /api/v1/tasks/{task_id}/artifacts`
- `GET /api/v1/tasks/{task_id}/checkpoints`
- `GET /api/v1/tasks/{task_id}/events`
- `GET /api/v1/tasks/{task_id}/stats`
- `GET /api/v1/tasks/{task_id}/search-hits`
- `GET /api/v1/tasks/{task_id}/search-invocations`
- `GET /api/v1/tasks/{task_id}/fetch-invocations`
- `GET /api/v1/tasks/{task_id}/llm-invocations`

These are intended for:

- polling-friendly UI updates
- task dashboard summaries
- evidence inspection
- provider audit views

## 3.4 Get Step Details

`GET /api/v1/steps/{step_run_id}`

Purpose:

- inspect one step in detail

Suggested response fields:

- input snapshot summary
- output summary
- status
- retry attempts
- cache hit
- provider info
- artifact list
- error info

Current step-level auxiliary endpoints:

- `POST /api/v1/steps/{step_run_id}/derive-task`
- `GET /api/v1/steps/{step_run_id}/search-hits`
- `GET /api/v1/steps/{step_run_id}/search-invocations`
- `GET /api/v1/steps/{step_run_id}/fetch-invocations`
- `GET /api/v1/steps/{step_run_id}/llm-invocations`

## 3.5 Get Artifact

`GET /api/v1/artifacts/{artifact_id}`

Purpose:

- inspect one artifact metadata
- optionally fetch its content or content reference

Optional modes:

- metadata only
- inline JSON content
- signed URL or object reference

Current artifact lineage endpoint:

- `GET /api/v1/artifacts/{artifact_id}/lineage`

## 3.6 List Task Artifacts

`GET /api/v1/tasks/{task_id}/artifacts`

Suggested filters:

- `artifact_type`
- `artifact_level`
- `step_run_id`

## 3.7 Resume from Checkpoint

`POST /api/v1/tasks`

Resume request example:

```json
{
  "template_id": "public_opinion_analysis_v1",
  "resume_from": {
    "checkpoint_id": "cp_009"
  }
}
```

## 3.8 Fork from Artifact

`POST /api/v1/tasks`

Fork request example:

```json
{
  "template_id": "event_summary_v1",
  "resume_from": {
    "artifact_id": "art_dedup_001"
  }
}
```

## 3.9 Fork from Existing Task

`POST /api/v1/tasks`

Fork request example:

```json
{
  "template_id": "public_opinion_analysis_v1",
  "fork_from": {
    "task_id": "run_01JXXX",
    "start_node_key": "classify_source"
  }
}
```

## 3.10 List Workflow Templates

`GET /api/v1/workflow-templates`

Purpose:

- allow external callers and UI to discover available templates

Current template detail endpoint:

- `GET /api/v1/workflow-templates/{template_id}`

This returns the ordered step blueprint for the template.

## 3.11 Provider Catalog

Current provider catalog endpoints:

- `GET /api/v1/provider-catalog/search`
- `GET /api/v1/provider-catalog/fetch`
- `GET /api/v1/provider-catalog/crawl`
- `GET /api/v1/provider-catalog/llm/providers`
- `GET /api/v1/provider-catalog/llm/profiles`
- `GET /api/v1/provider-catalog/source-registry`

Purpose:

- show configured platform capabilities
- power admin and console UI
- support integration validation

## 3.12 Console

Current local operator console:

- `GET /console`

Purpose:

- edit runtime config files
- create and control tasks
- inspect task bundle, graph, stats, hits, documents, and invocations
- launch continuation flows from step, artifact, and checkpoint

## 4. API Semantics

## 4.1 Asynchronous by Default

Task creation should return immediately after task registration and queue submission.

## 4.2 Stable Identifiers

External consumers should interact with:

- `task_id`
- `step_run_id`
- `artifact_id`
- `checkpoint_id`

Avoid exposing internal assumptions based on step numbering.

## 4.3 Pagination

Artifacts and steps can become large. Support standard pagination:

- `page`
- `page_size`
- `cursor`

## 4.4 Partial Response Control

Large task responses should allow selective expansion:

- `include=steps`
- `include=artifacts`
- `include=invocations`

## 5. Progress Push

Persisted event timeline endpoint:

`GET /api/v1/tasks/{task_id}/events`

It returns durable event records such as:

- task status change
- step started
- step completed
- step cached
- task cancelled

An SSE layer can be added later on top of the same event model.

## 6. Error Model

Standard API error envelope should include:

- `code`
- `message`
- `request_id`
- optional `details`

For task failures, detailed failure information should live in task and step query responses rather than only synchronous API error responses.
