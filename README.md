# LLM Scheduling Management System

A workflow-oriented platform for:

- centralized LLM invocation
- multi-source search and fetch
- MCP tool integration
- step-level persistence
- replay, resume, fork, and cache reuse
- local operator console and runtime inspection

This repository is no longer only a design scaffold. It already contains a runnable local MVP implementation with:

- task creation and execution APIs
- polling worker
- task control and inspection
- search hit and document persistence
- invocation logging for search, fetch, LLM, and tools
- artifact lineage and checkpoints
- provider configuration editing
- a local task console at `/console`

## What It Does

The platform is designed for workflows such as:

- public opinion analysis
- public opinion timeline generation
- event summary generation
- future workflow templates built on the same runtime model

Each task is represented as a workflow run with multiple step runs. Every meaningful step can produce:

- artifacts
- checkpoints
- invocation records
- task events

This makes the system suitable for:

- observability
- downstream reuse
- evidence tracking
- debugging and audit

## Current Capability Summary

The current implementation supports:

- workflow templates:
  - `event_summary_v1`
  - `public_opinion_analysis_v1`
  - `public_opinion_timeline_v1`
- task control:
  - create
  - list
  - run all
  - run next step
  - cancel
- task continuation:
  - resume from artifact
  - resume from checkpoint
  - fork from task and node
  - derive task from step
- runtime data views:
  - steps
  - artifacts
  - checkpoints
  - events
  - stats
  - graph
  - bundle
  - search hits
  - documents
  - search/fetch/llm/tool invocations
- provider catalog and source registry views
- configurable local provider setup through the console

## Current Real Provider Status

The system supports both simulated and real providers.

### Search

Real search has already been validated for:

- Tavily-compatible relay
- Exa search

### Fetch

Real fetch has already been validated for:

- Exa contents

Other fetch providers currently have request builders and parser skeletons, but may still be used in simulated mode unless configured otherwise.

### LLM

Real LLM execution has already been validated for:

- OpenAI-compatible gateway using:
  - `gpt-5.4`
  - `gpt-4o-mini`
- Grok relay:
  - validated model: `grok-4.20-beta`
- Claude relay:
  - validated model: `claude-opus-4-7`

### MCP

The repository includes a minimal working MCP chain:

- MCP config loading
- MCP registry
- MCP stdio/http client skeleton
- tool invocation persistence
- `mcp_lookup_context` executor
- a local stdio example MCP server that lists markdown files under `docs/`

The example MCP server is:

- [scripts/example_mcp_server.py](./scripts/example_mcp_server.py)

## Repository Structure

```text
apps/
  api/
  worker/

alembic/
config/
docs/
scripts/
src/
tests/
```

Key areas:

- `src/.../interfaces/http/`:
  API routes and console
- `src/.../execution/`:
  workflow step executors
- `src/.../providers/`:
  search, fetch, LLM, and provider client abstractions
- `src/.../mcp/`:
  MCP registry and client
- `src/.../repositories/`:
  persistence operations
- `src/.../services/`:
  task orchestration and worker logic

## Data Model

The current runtime model includes:

- `workflow_templates`
- `task_runs`
- `step_runs`
- `artifacts`
- `artifact_lineage`
- `checkpoints`
- `search_hits`
- `documents`
- `search_invocations`
- `fetch_invocations`
- `llm_invocations`
- `tool_invocations`
- `task_events`

## Local Setup

### Prerequisites

- Python 3.11+
- `uv`

### Install

```bash
uv sync
```

### Initialize Database

Preferred migration path:

```bash
uv run alembic upgrade head
```

Development reset path:

```bash
uv run python scripts/dev_reset_db.py
```

Use the reset path when you want a clean local rebuild.

### Database Backends

The current codebase supports:

- SQLite
- MySQL via `pymysql`
- PostgreSQL via `psycopg`

The runtime database is controlled by:

- `LSMS_DATABASE_URL`

Example DSNs:

```text
sqlite:///./data/app.db
mysql+pymysql://user:password@127.0.0.1:3306/llm_workflow?charset=utf8mb4
postgresql+psycopg://user:password@127.0.0.1:5432/llm_workflow
```

Current local runtime in this workspace has already been switched to MySQL through a local `.env` override.

## Running the System

### Run API

```bash
uv run python scripts/dev_run_api.py
```

Default local endpoints:

- API: `http://127.0.0.1:8000`
- Console: `http://127.0.0.1:8000/console`

### Run Worker

Run once:

```bash
uv run python scripts/dev_run_worker.py --mode once
```

Run until no runnable tasks remain:

```bash
uv run python scripts/dev_run_worker.py --mode until-idle
```

Run polling loop:

```bash
uv run python scripts/dev_run_worker.py --mode loop
```

### Export a Task Bundle

```bash
uv run python scripts/dev_export_task_bundle.py <task_id>
```

By default, it writes a JSON bundle under `artifacts/`.

## Configuration

Runtime config prefers local files first:

- `config/search.toml`
- `config/llm.toml`
- `config/source_registry.toml`
- `config/mcp.toml`

If a local file is missing, the system falls back to:

- `config/search.example.toml`
- `config/llm.example.toml`
- `config/source_registry.example.toml`
- `config/mcp.example.toml`

### Important Rule

Local config files are ignored by git and may contain real credentials.

Example config files are committed for structure only.

### Provider Flags

Provider configs support:

- `enabled`
- `simulate`
- `extra_headers`
- `default_options`

Use:

- `simulate = true`
  when you want stable local mock behavior
- `simulate = false`
  when you want real HTTP execution

## Console

The local console is served at:

```text
/console
```

It includes:

- system overview
- task creation
- task list
- task detail inspection
- task control
- graph / events / invocations / documents / hits / bundle
- continuation tools
- config editors for search, llm, source registry, and MCP
- provider health checks
- runtime provider/profile selection per task

### Grok Note

The console includes a Grok compatibility note.

Current validated Grok relay model:

- `grok-4.20-beta`

Recommended architecture:

- Grok should be treated as `model_embedded_search`
  or as an LLM profile/tool path, not as a standalone search provider.

## API Overview

Main task endpoints:

- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/run`
- `POST /api/v1/tasks/{task_id}/run-next-step`
- `POST /api/v1/tasks/{task_id}/cancel`

Task detail views:

- `GET /api/v1/tasks/{task_id}/steps`
- `GET /api/v1/tasks/{task_id}/artifacts`
- `GET /api/v1/tasks/{task_id}/checkpoints`
- `GET /api/v1/tasks/{task_id}/events`
- `GET /api/v1/tasks/{task_id}/stats`
- `GET /api/v1/tasks/{task_id}/graph`
- `GET /api/v1/tasks/{task_id}/bundle`
- `GET /api/v1/tasks/{task_id}/search-hits`
- `GET /api/v1/tasks/{task_id}/documents`
- `GET /api/v1/tasks/{task_id}/search-invocations`
- `GET /api/v1/tasks/{task_id}/fetch-invocations`
- `GET /api/v1/tasks/{task_id}/llm-invocations`
- `GET /api/v1/tasks/{task_id}/tool-invocations`

Step and artifact endpoints:

- `GET /api/v1/steps/{step_run_id}`
- `POST /api/v1/steps/{step_run_id}/derive-task`
- `GET /api/v1/steps/{step_run_id}/search-hits`
- `GET /api/v1/steps/{step_run_id}/documents`
- `GET /api/v1/steps/{step_run_id}/search-invocations`
- `GET /api/v1/steps/{step_run_id}/fetch-invocations`
- `GET /api/v1/steps/{step_run_id}/llm-invocations`
- `GET /api/v1/steps/{step_run_id}/tool-invocations`
- `GET /api/v1/artifacts/{artifact_id}`
- `GET /api/v1/artifacts/{artifact_id}/lineage`
- `GET /api/v1/checkpoints/{checkpoint_id}`

Template and catalog endpoints:

- `GET /api/v1/workflow-templates`
- `GET /api/v1/workflow-templates/{template_id}`
- `GET /api/v1/provider-catalog/search`
- `GET /api/v1/provider-catalog/fetch`
- `GET /api/v1/provider-catalog/crawl`
- `GET /api/v1/provider-catalog/llm/providers`
- `GET /api/v1/provider-catalog/llm/profiles`
- `GET /api/v1/provider-catalog/source-registry`
- `GET /api/v1/provider-catalog/mcp/servers`
- `GET /api/v1/provider-catalog/health`
- `GET /api/v1/system/status`

Config endpoints:

- `GET /api/v1/config/search`
- `POST /api/v1/config/search`
- `GET /api/v1/config/llm`
- `POST /api/v1/config/llm`
- `GET /api/v1/config/source-registry`
- `POST /api/v1/config/source-registry`
- `GET /api/v1/config/mcp`
- `POST /api/v1/config/mcp`
- `POST /api/v1/config/search/test`
- `POST /api/v1/config/llm/test`
- `POST /api/v1/config/mcp/test`
- `GET /api/v1/config/notes/grok-search`
- `GET /api/v1/config/notes/claude-models`

## Workflow Semantics

### Task Model

Each external request creates a `task_run`.

Each task contains ordered `step_run` records.

Each step can:

- execute normally
- be skipped
- be cached
- fail and enter retry flow
- terminate the task in partial-failed or failed state

### Continuation

Supported continuation modes:

- resume from artifact
- resume from checkpoint
- fork from task and start node
- derive task from step

### Cache

The system supports deterministic step cache for repeated tasks.

You can bypass cache using task options:

```json
{
  "disable_cache": true
}
```

or:

```json
{
  "disable_cache_nodes": ["search_fanout", "fetch_documents"]
}
```

## MCP Usage

MCP is treated as a tool integration layer, not as a replacement for search or LLM providers.

Current minimal MCP example:

- server name: `internal_tools`
- transport: `stdio`
- tool: `list_docs`

This example lists markdown files under `docs/`.

Current workflow integration:

- `public_opinion_analysis_v1`
  contains `mcp_lookup_context`

The MCP result is:

- persisted as `tool_invocation`
- persisted as a `tool.mcp_result` artifact
- fed into downstream merge/classification flow

## Testing

Run all tests:

```bash
uv run pytest
```

The test environment forces example/mock config paths so local real credentials do not affect test stability.

## Current Implementation Status

The repository currently provides:

- complete backend MVP runtime scaffold
- complete local task console
- real provider integration start
- real search / fetch / llm validation paths
- local MCP example chain

This includes:

- real Tavily search integration
- real Exa search integration
- real Exa contents integration
- real OpenAI-compatible gateway integration
- validated Grok relay profile
- validated Claude relay profile

Still pending for production-grade readiness:

- full auth and multi-tenant enforcement
- distributed queue / lock / worker coordination
- full LangGraph orchestration integration
- richer response normalization across all providers
- advanced retry / rate-limit policies
- production deployment hardening
- frontend asset pipeline separation

## Recommended Next Implementation Directions

The most valuable next steps are:

1. expand real provider integrations and normalize their outputs more deeply
2. enrich downstream analysis executors using real document semantics
3. add auth and tenant isolation
4. replace polling worker with stronger queue-backed execution
5. integrate LangGraph as the orchestration owner
