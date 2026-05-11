# Implementation Roadmap

## 1. Goal

Define a phased delivery plan that moves from a workable MVP to a configurable workflow platform.

## 2. Phase 1: MVP

### 2.1 Target Outcome

Deliver a usable asynchronous workflow platform that can:

- accept tasks
- run workflows in background
- show progress by task ID
- persist step results
- support search and downstream generation
- support different LLM profiles per step

### 2.2 Scope

Implement:

- FastAPI API skeleton
- LangGraph orchestration
- worker process
- PostgreSQL metadata tables
- Redis-based queue coordination
- MinIO artifact storage
- three workflow templates:
  - `event_summary_v1`
  - `public_opinion_analysis_v1`
  - `public_opinion_timeline_v1`
- reusable search subgraph
- LLM provider abstraction
- prompt template persistence
- task and artifact query APIs

Current implementation status:

- FastAPI API skeleton: done
- worker process: done as polling loop scaffold
- three workflow templates: done as executable blueprints
- reusable search subgraph: done as scaffolded step chain
- provider abstraction: done as configuration-driven adapter skeleton
- task / artifact / checkpoint / lineage query APIs: done
- task control APIs: done
- task graph / task bundle / provider catalog / system status: done
- search hit and fetched document persistence: done
- cache and retry scaffolding: done
- Alembic scaffold: done

### 2.3 Not in Scope

Do not implement yet:

- visual drag-and-drop workflow builder
- advanced multi-tenant billing
- complex manual review console
- complete knowledge graph reasoning
- too many provider integrations

## 3. Phase 2: Reuse and Governance

### 3.1 Target Outcome

Turn the MVP into a true reusable platform.

### 3.2 Scope

Implement:

- checkpoint resume
- artifact-based fork
- step cache with TTL
- model profile management
- routing policy management
- source registry management
- pgvector retrieval
- cost dashboards
- tenant-level access boundaries

Current implementation status:

- checkpoint resume: scaffolded and operational for artifact seeding
- artifact-based fork: operational
- step cache with TTL: partial, cache logic implemented, TTL policy still simplified
- source registry management: scaffolded through config
- tenant-level access boundaries: still minimal

## 4. Phase 3: Expansion and Productization

### 4.1 Target Outcome

Support more workflows, tool integrations, and operational visibility.

### 4.2 Scope

Implement:

- MCP tool registry
- OpenSearch integration
- human review checkpoints
- webhook callbacks
- SSE task event streams
- workflow template management UI
- source quality management console

Current implementation status:

- these items are still pending

## 5. Suggested Codebase Structure

Recommended initial structure:

```text
apps/
  api/
  worker/

src/
  domain/
    workflows/
    runs/
    artifacts/
    providers/
    prompts/
    governance/

  application/
    workflow_templates/
    workflow_runs/
    artifact_reuse/
    routing/

  infrastructure/
    db/
    cache/
    object_store/
    queue/
    providers/
      llm/
      search/
      mcp/
    observability/

  interfaces/
    http/
    tasks/

docs/
```

## 6. Suggested Delivery Order

### 6.1 First

- data model migration draft
- API contract skeleton
- worker startup and queue flow
- task creation and query

Current status:

- initial Alembic scaffolding is present
- local reset script remains available for fast iteration

### 6.2 Second

- search subgraph
- artifact persistence
- step visibility

Status:

- completed in scaffold form

### 6.3 Third

- LLM routing and prompt versioning
- final report generation
- cache strategy

Status:

- LLM routing scaffold: implemented
- final report generation scaffold: implemented
- cache strategy scaffold: implemented

### 6.4 Fourth

- checkpoint and fork flows
- UI task console

Status:

- checkpoint and fork flows: implemented at API and runtime scaffold level
- UI task console: pending

## 7. Acceptance Criteria for MVP

The MVP should be considered acceptable only if it satisfies all of the following:

- external request returns task ID immediately
- task progress is queryable at any time
- each step has visible status and output references
- search results preserve source metadata and publish time
- different steps can use different LLM profiles
- at least one reusable checkpoint or artifact-based continuation path works
- final output is traceable back to search and LLM invocation evidence
