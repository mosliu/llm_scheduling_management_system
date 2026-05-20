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
- final report retrieval endpoint
- LLM retry and fallback chain for report generation

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
  - `public_opinion_report_v1`
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
- specialized report entrypoint:
  - `POST /api/v1/reports/public-opinion`
- provider catalog and source registry views
- configurable local provider setup through the console
- console graph visualization and provider health inspection
- config test actions for search, LLM, and MCP profiles
- multi-provider search fanout with parallel execution
- configurable `search_limit` per task, defaulting to `30` results per provider
- final-report polling endpoint for external systems

## Current Real Provider Status

The system supports both simulated and real providers.

### Search

Real search has already been validated for:

- Tavily-compatible relay
- Exa search
- Grok relay as model-embedded web search
- OpenAI-compatible web search via `responses` API

As of `2026-05-12`, this workspace has successfully tested:

- `grok-4.20-beta` web search through `https://api.aabao.top/v1/chat/completions`
- `gpt-5.5` web search through `https://api.aabao.top/v1/responses`
- `gpt-5.4` web search through `https://api.aabao.top/v1/responses`

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
- Health: `http://127.0.0.1:8000/healthz`

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

The worker is what advances queued tasks asynchronously. If you only create a task through `POST /api/v1/tasks` or `POST /api/v1/reports/public-opinion`, keep the worker running if you want the task to continue automatically.

If you want synchronous/manual execution instead, call `POST /api/v1/tasks/{task_id}/run`.

### Linux Service Scripts

Linux deployment scripts are provided under:

- `scripts/services/deploy.sh`
- `scripts/services/run-api.sh`
- `scripts/services/run-worker.sh`
- `scripts/services/llms-api.service.example`
- `scripts/services/llms-worker.service.example`

Recommended production deployment target:

- `systemd`

Example flow on Linux:

1. copy the repo to a stable path such as `/opt/llm-scheduling-management-system`
2. prepare `.env` and local `config/*.toml`
   - if you want to protect `/console`, `/docs`, and the API, also create `config/access.toml`
3. run `uv sync`
4. run `uv run alembic upgrade head`
5. copy:
   - `scripts/services/llms-api.service.example`
   - `scripts/services/llms-worker.service.example`
   into `/etc/systemd/system/`
6. adjust `User`, `Group`, and `WorkingDirectory`
7. enable and start both services

Example commands:

```bash
sudo cp scripts/services/llms-api.service.example /etc/systemd/system/llms-api.service
sudo cp scripts/services/llms-worker.service.example /etc/systemd/system/llms-worker.service
sudo systemctl daemon-reload
sudo systemctl enable --now llms-api.service
sudo systemctl enable --now llms-worker.service
sudo systemctl status llms-api.service
sudo systemctl status llms-worker.service
```

One-shot deployment command:

```bash
sudo bash scripts/services/deploy.sh
```

Supported environment overrides for `deploy.sh`:

- `LSMS_SERVICE_USER`
- `LSMS_SERVICE_GROUP`
- `LSMS_API_SERVICE_NAME`
- `LSMS_WORKER_SERVICE_NAME`
- `LSMS_API_HOST`
- `LSMS_API_PORT`
- `LSMS_WORKER_POLL_INTERVAL`
- `LSMS_WORKER_LIMIT`
- `LSMS_INSTALL_SYSTEM_USER`
- `LSMS_CHOWN_REPO`

### Windows Service Scripts

Windows deployment helpers are also provided under:

- `scripts/services/run-api.ps1`
- `scripts/services/run-worker.ps1`
- `scripts/services/install-windows-tasks.ps1`
- `scripts/services/uninstall-windows-tasks.ps1`
- `scripts/services/start-windows-tasks.ps1`
- `scripts/services/stop-windows-tasks.ps1`
- `scripts/services/status-windows-tasks.ps1`

These scripts install the API and worker as startup-managed Windows scheduled tasks. They are useful for Windows environments, but if your target is Linux, prefer the `systemd` path above.

Example installation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/services/install-windows-tasks.ps1 -Force
```

Check status:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/services/status-windows-tasks.ps1
```

### Export a Task Bundle

```bash
uv run python scripts/dev_export_task_bundle.py <task_id>
```

By default, it writes a JSON bundle under `artifacts/`.

## Configuration

Runtime config prefers local files first:

- `config/access.toml`
- `config/search.toml`
- `config/llm.toml`
- `config/source_registry.toml`
- `config/mcp.toml`
- `.env`

If a local file is missing, the system falls back to:

- `config/access.example.toml`
- `config/search.example.toml`
- `config/llm.example.toml`
- `config/source_registry.example.toml`
- `config/mcp.example.toml`

Additional checked-in example files document the wider operational shape of the system:

- `config/app.example.toml`
- `config/observability.example.toml`
- `config/storage.example.toml`

### Manual-Only Access Control

HTTP access control is configured through:

- `config/access.toml`

This file is intentionally manual-only:

- it is not exposed through `/api/v1/config/*`
- it is not writable from the console
- it should be kept local and out of git

Example:

```toml
enabled = true
password_header_name = "X-LSMS-Password"
basic_auth_realm = "llm-scheduling-management-system"

[[credentials]]
user = "admin"
password = "replace-with-a-strong-password"

[[credentials]]
user = "operator"
password = "replace-with-another-strong-password"
```

When access control is enabled:

- browser access to `/console`, `/docs`, and `/redoc` uses HTTP Basic Auth
- script and service calls can send the configured password in the `X-LSMS-Password` header
- every authenticated request is logged with the mapped configured user

At the moment, the runtime directly loads search, LLM, source registry, MCP, and environment settings. The extra example files are still useful as deployment-oriented templates and future extension points.

### Important Rule

Local config files are ignored by git and may contain real credentials.

Example config files are committed for structure only.

### Provider Flags

Provider configs support:

- `enabled`
- `simulate`
- `extra_headers`
- `default_options`

Task-level retrieval options can also override runtime behavior:

- `search_provider_names`
- `search_limit`
- `search_parallelism`

Use:

- `simulate = true`
  when you want stable local mock behavior
- `simulate = false`
  when you want real HTTP execution

### Minimum Real-Run Config

For a real end-to-end public opinion report, the minimum practical setup is:

- `.env`
  with `LSMS_DATABASE_URL`
- `config/search.toml`
  with at least one real search provider and optionally one real fetch provider
- `config/llm.toml`
  with at least one real LLM provider and one runnable profile
- `config/source_registry.toml`
  if you want source classification and region/publisher enrichment
- `config/mcp.toml`
  only when you want MCP tools enabled for a workflow

All local config files above are git-ignored by design.

## Observability

The runtime uses Loguru and writes logs to:

- console stdout
- `logs/app.log`

Current log behavior:

- daily rotation at `00:00`
- retention of `14 days`
- log level controlled by `LSMS_LOG_LEVEL`

Task observability is also exposed through persisted runtime entities:

- `task_events`
- `step_runs`
- `artifacts`
- `checkpoints`
- invocation records for search, fetch, LLM, and MCP/tool calls

For worker stability on long-lived MySQL deployments, `scripts/run_worker_service.py` uses a fresh SQLAlchemy session per processing cycle instead of holding one session forever.

## Console

The local console is served at:

```text
/console
```

If `config/access.toml` has `enabled = true`, the console page is protected by the same password check as the API. Browser visits will receive an HTTP Basic Auth prompt.

It includes:

- system overview
- task creation
- task list
- task detail inspection
- task control
- graph / events / invocations / documents / hits / bundle
- continuation tools
- config editors for search, llm, source registry, and MCP
- config test actions for search, llm, and MCP
- provider health checks
- runtime provider/profile selection per task
- multi-select search providers and task-level search limit input

### Grok Note

The console includes a Grok compatibility note.

Current validated Grok relay model:

- `grok-4.20-beta`

Recommended architecture:

- Grok should be treated as `model_embedded_search`
  or as an LLM profile/tool path, not as a standalone search provider.

## API Overview

Health and utility endpoints:

- `GET /healthz`
- `GET /api/v1/system/status`

If access control is enabled, these endpoints also require a valid password.

Main task endpoints:

- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/run`
- `POST /api/v1/tasks/{task_id}/run-next-step`
- `POST /api/v1/tasks/{task_id}/cancel`
- `GET /api/v1/tasks/{task_id}/final-report`

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

Specialized report endpoint:

- `POST /api/v1/reports/public-opinion`
- `GET /api/v1/reports/public-opinion/{task_id}/final-report`

## Quick Start: Public Opinion Report

If your external system only wants to submit a topic and let the platform run the full workflow, use the specialized report API:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/reports/public-opinion" \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"2026年5月浏阳大爆炸\",\"disable_cache\":true,\"llm_profile_name\":\"advanced_reasoning_cn\",\"execution_engine\":\"langgraph\"}"
```

The response contains a `task_id`. After that:

1. keep the worker running with `uv run python scripts/dev_run_worker.py --mode loop`, or call `POST /api/v1/tasks/{task_id}/run` yourself
2. poll `GET /api/v1/tasks/{task_id}` for top-level progress
3. inspect `GET /api/v1/tasks/{task_id}/events` for the live execution trail
4. inspect `GET /api/v1/tasks/{task_id}/bundle` for a one-shot JSON view of task, steps, artifacts, hits, documents, and invocations
5. inspect `GET /api/v1/tasks/{task_id}/graph` for the step/artifact graph shown in the console

The specialized report route currently creates a task using:

- template: `public_opinion_report_v1`
- default search providers: `tavily_search`, `grok_search`, `gpt_search`, `exa_search`
- default search limit: `30` per provider
- default fetch provider: `exa_contents`
- default execution engine: `langgraph`
- default report retry count: `2`
- default per-model retry count: `2`
- default fallback profiles: `grok_reasoning_optional`, `claude_opus_web_search_optional`, `cheap_structured_cn`

The route is only a convenience wrapper. The same flow can still be created through `POST /api/v1/tasks`. If your local config uses different provider names, use the generic task API and pass explicit `options`.

### Final Report Polling

External systems can poll a dedicated endpoint instead of scanning artifacts:

```text
GET /api/v1/tasks/{task_id}/final-report
```

Response behavior:

- `ready = false`
  when the final report is not available yet
- `ready = true`
  when the report text is available

Status semantics:

- `report_state = "not_generated"`
  when the report step has not finished yet
- `report_state = "empty"`
  when a final report artifact exists but the text payload is empty
- `report_state = "ready"`
  when report text is available

The response includes:

- `report_text`
- `artifact_id`
- `generated_at`
- `llm_profile_name`
- `llm_model_name`
- `llm_invocation_id`
- `timeline`
- `timeline_count`
- `official_responses`
- `official_response_count`
- `media_viewpoints`
- `media_viewpoint_count`
- `public_viewpoints`
- `public_viewpoint_count`

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

### Search Fanout

The `search_fanout` step supports selecting multiple providers in one task.

Those providers are executed in parallel and each provider receives its own per-provider limit.

Example task options:

```json
{
  "search_provider_names": ["tavily_search", "grok_search", "gpt_search", "exa_search"],
  "search_limit": 30
}
```

### Report Retry and Fallback

Final report generation now supports:

- automatic end-to-end retry
- per-model retry
- model/profile fallback chain
- deterministic structured fallback text if all configured LLM attempts still fail

Relevant task options:

```json
{
  "report_retry_count": 2,
  "llm_model_retry_count": 2,
  "report_fallback_profile_names": [
    "grok_reasoning_optional",
    "claude_opus_web_search_optional",
    "cheap_structured_cn"
  ]
}
```

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
- optional LangGraph-backed execution path

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
- making LangGraph the sole orchestration owner and hardening its state model
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
