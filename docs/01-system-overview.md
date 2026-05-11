# System Overview

## 1. Goal

Build a centralized workflow platform based on LangGraph for large-model orchestration, search API integration, and optional MCP tool integration.

The platform should support:

- external task submission through API
- immediate return of a task ID
- asynchronous background execution
- task progress query at any time
- step-level status and result inspection
- page-based visualization using the same backend APIs
- intermediate result persistence and reuse
- cached step results with time-based expiration
- downstream resume based on prior step outputs
- different LLM selection policies for different workflows and different steps

## 2. Product Positioning

This system should be positioned as a workflow execution platform for intelligence and content production rather than a simple LLM gateway.

It is not only responsible for calling models. It must also manage:

- workflow definition
- execution orchestration
- retrieval and evidence handling
- data lineage
- output generation
- audit and replay
- cost and provider governance

## 3. Typical Business Scenarios

### 3.1 Public Opinion Timeline

Input:

- topic
- time range
- optional source filters

Output:

- event timeline
- event relationships
- timeline report

### 3.2 Public Opinion Analysis

Input:

- topic
- time range
- workflow options

Output:

- stance classification
- sentiment and risk signals
- source distribution
- analysis report

### 3.3 Event Summary

Input:

- topic
- source scope

Output:

- concise summary
- facts and supporting evidence
- summary report

## 4. Architecture Layers

The platform should be divided into six logical layers.

### 4.1 API Layer

Responsibilities:

- accept task creation requests
- return task IDs
- expose task query endpoints
- expose artifact and checkpoint endpoints
- expose workflow template management endpoints
- serve UI console with the same backend contract

Suggested components:

- FastAPI application
- auth middleware
- rate limiting
- request validation
- SSE or WebSocket optional real-time updates

### 4.2 Workflow Orchestration Layer

Responsibilities:

- define workflow graphs
- execute nodes in sequence or parallel
- manage branches and joins
- support retries and resume
- support subgraph reuse

Suggested technology:

- LangGraph as workflow state machine

Important boundary:

- LangGraph should orchestrate execution.
- It should not own long-term persistence logic, provider configuration logic, or governance logic.

### 4.3 Execution Layer

Responsibilities:

- execute node logic according to node type
- invoke providers through stable internal interfaces
- emit step records and artifacts
- handle standardized retry and timeout behavior

Suggested executors:

- `llm_executor`
- `search_executor`
- `mcp_executor`
- `document_fetch_executor`
- `normalize_executor`
- `classification_executor`
- `filter_executor`
- `aggregation_executor`
- `report_executor`

### 4.4 Provider Layer

Responsibilities:

- abstract different external systems
- isolate workflow logic from provider-specific details
- manage credentials and provider capabilities

Provider categories:

- LLM providers
- search providers
- MCP tool adapters
- storage and index providers
- embedding and rerank providers

### 4.5 Data and Knowledge Layer

Responsibilities:

- persist workflow definitions
- persist runs and step-level execution state
- persist raw, normalized, and derived artifacts
- support artifact retrieval and reuse
- support search result history and evidence tracing
- support later knowledge indexing

### 4.6 Governance and Observability Layer

Responsibilities:

- tenant isolation
- permission management
- audit logging
- token and cost accounting
- metrics and traces
- provider health and SLA tracking

## 5. Core Design Decisions

### 5.1 Task-First Execution Model

Every external request creates a `task_run`. The caller gets a task ID immediately. Execution continues asynchronously.

### 5.2 Step-Level Persistence

Every meaningful step creates:

- a `step_run` execution record
- zero or more `artifact` records
- optional `checkpoint` records for downstream resume

### 5.3 Search Before Classification

The system should collect search results from multiple sources first, then normalize and classify results by attributes such as:

- source domain
- language
- publisher type
- publish time
- region hints

This is more stable than splitting channels into domestic versus international at acquisition time.

### 5.4 LLM Profiles as First-Class Configurations

Different workflows and steps may use different LLMs. This must be expressed through a structured routing system instead of hard-coded `if/else` logic.

### 5.5 Artifact-Based Reuse

Downstream workflows should be able to start from previously generated artifacts or checkpoints without repeating upstream steps.

## 6. High-Level Execution Flow

```text
External Client
  -> Create Task API
  -> Task Queue / Worker Poll Loop
  -> Workflow Run Initialization
  -> Step Executors / Stepwise Control
  -> Providers / MCP / Search / Storage
  -> Step Artifacts / Search Hits / Documents / Checkpoints / Invocations / Events
  -> Task Query API / Console UI
```

## 7. Initial Deployment Strategy

For the first implementation phase, use a modular monolith instead of microservices.

Suggested initial deployable units:

- `api` service
- `worker` service
- shared library modules
- PostgreSQL
- Redis
- MinIO

This keeps operational complexity under control while preserving future split points.

## 8. Current Implementation Status

The current repository already contains a runnable MVP-oriented scaffold with:

- FastAPI task APIs
- task create / list / detail
- task run / run-next-step / cancel
- worker polling loop
- workflow template discovery and detail
- task event timeline
- search hit persistence
- fetched document persistence
- artifact lineage
- checkpoint and artifact-based continuation
- fork-from-step convenience flow
- provider catalog APIs
- task graph and task bundle export surfaces
- Loguru console and daily rotating file logs
- Alembic migration scaffold
