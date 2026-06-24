# LLM Workflow Platform Design Documents

## Overview

This document set defines a workflow-oriented platform for:

- centralized LLM invocation
- multi-source search and retrieval
- MCP tool integration
- asynchronous task execution
- step-level artifact persistence
- cached reuse and downstream resume
- external API access and internal console visualization

The target business scenarios include:

- public opinion timeline generation
- public opinion analysis
- event summary
- additional workflow templates built on the same execution model

## Document Index

- [CHANGELOG.md](./CHANGELOG.md)
- [01-system-overview.md](./01-system-overview.md)
- [02-workflow-execution-model.md](./02-workflow-execution-model.md)
- [03-search-pipeline-design.md](./03-search-pipeline-design.md)
- [04-llm-routing-and-provider-design.md](./04-llm-routing-and-provider-design.md)
- [05-data-model-design.md](./05-data-model-design.md)
- [06-api-design.md](./06-api-design.md)
- [07-implementation-roadmap.md](./07-implementation-roadmap.md)
- [08-liuzhou-earthquake-task-execution.md](./08-liuzhou-earthquake-task-execution.md)
- [09-user-facing-briefing-ui.md](./09-user-facing-briefing-ui.md)
- [10-briefing-standalone-build.md](./10-briefing-standalone-build.md)
- [11-search-provider-configuration.md](./11-search-provider-configuration.md)

## Recommended Reading Order

1. System overview
2. Workflow execution model
3. Search pipeline design
4. LLM routing and provider design
5. Data model design
6. API design
7. Implementation roadmap
8. Liuzhou earthquake task execution
9. User-facing briefing UI
10. Briefing standalone build
11. Search provider configuration

## Local Development

This repository now includes a runnable MVP backend plus local operator console.

The operational entry guide lives in the repository root:

- [../README.md](../README.md)

Recommended commands:

```bash
uv sync
uv run alembic upgrade head
uv run python scripts/dev_reset_db.py
uv run python scripts/dev_run_api.py
uv run python scripts/dev_run_worker.py --mode until-idle
uv run python scripts/dev_export_task_bundle.py <task_id>
uv run pytest
```

Notes:

- `uv run alembic upgrade head` is the standard schema initialization path.
- `dev_reset_db.py` is a development-only reset path that is still useful when local development needs a full clean rebuild.
- `dev_run_worker.py` supports `--mode once`, `--mode until-idle`, and `--mode loop`.
- `dev_export_task_bundle.py` exports `/bundle` output to a local JSON file under `artifacts/` by default.
- Logging now uses Loguru and writes to both console and `logs/app.log`.
- File logs are configured for daily rotation.
- The API also exposes `GET /healthz`.
- Runtime config loading now prefers local files such as `config/search.toml` and `config/llm.toml`.
- If local files are absent, the system falls back to the checked-in `*.example.toml` files.
- Repeated identical tasks now support cache hits at `search_fanout` and deterministic downstream steps.
- `search_fanout` now supports parallel multi-provider fanout with task-level `search_limit`; the default limit is `30` results per provider.
- Final report generation now supports automatic retry, per-model retry, fallback profiles, and a dedicated `final-report` polling endpoint that can return both report text and structured sections.
- Provider configs now support `simulate=true|false`; set `simulate=false` in local config when moving from mock execution toward real HTTP integrations.
- The local console is available at `/console` and now includes task creation, task control, provider selection, and continuation tools.
- Real provider integration has started: local runtime can use real Tavily search, real Exa search/fetch, Grok model-embedded search, OpenAI-compatible web search, OpenAI-compatible generation gateways, and optional Claude relay profiles when configured.
- A topic-only convenience endpoint exists at `POST /api/v1/reports/public-opinion`.
- Windows deployment helpers are available under `scripts/services/`.
- Linux `systemd` deployment templates are available under `scripts/services/` and should be treated as the primary server deployment path.
- A Linux one-shot deployment script is available at `scripts/services/deploy.sh`.

## Core Principles

- Treat workflows as first-class business products, not as ad hoc scripts.
- Treat `task_run`, `step_run`, `artifact`, and `checkpoint` as first-class system entities.
- Persist every important intermediate result for traceability and reuse.
- Keep orchestration state light; store large payloads in artifact storage.
- Support different LLM profiles per workflow and per step.
- Normalize multi-source retrieval before classification and filtering.
- Make resume, replay, cache hit, and derived execution explicit in the data model.
