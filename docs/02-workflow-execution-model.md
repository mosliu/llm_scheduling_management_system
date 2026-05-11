# Workflow Execution Model

## 1. Goal

Define a unified execution model that supports:

- asynchronous task creation
- real-time progress query
- step-level visibility
- artifact persistence
- cache hit reuse
- downstream resume from checkpoint or artifact
- many different business workflows built on the same runtime model

## 2. First-Class Runtime Entities

The execution model should revolve around the following entities.

### 2.1 Workflow Template

Represents a reusable workflow definition.

Examples:

- `event_summary_v1`
- `public_opinion_analysis_v1`
- `public_opinion_timeline_v1`

### 2.2 Task Run

Represents one external task request.

This is the main external ID returned to clients.

### 2.3 Step Run

Represents one execution instance of one workflow step.

Examples:

- search results acquisition
- ES recall
- result merge
- deduplication
- report generation

### 2.4 Artifact

Represents data produced by a step.

Examples:

- raw search hits
- normalized documents
- classified source results
- merged evidence bundle
- final report

### 2.5 Checkpoint

Represents a resumable boundary in a workflow.

It should reference either:

- one output artifact
- a set of output artifacts
- a workflow state snapshot plus artifact references

## 3. Standard Task Lifecycle

### 3.1 Task Statuses

Suggested `task_run.status` values:

- `pending`
- `queued`
- `running`
- `waiting_retry`
- `waiting_manual`
- `partial_failed`
- `succeeded`
- `failed`
- `cancelled`

### 3.2 Step Statuses

Suggested `step_run.status` values:

- `pending`
- `running`
- `retrying`
- `succeeded`
- `failed`
- `skipped`
- `cached`

The `cached` status is useful to distinguish reused results from newly executed results.

## 4. Standard API Interaction Pattern

### 4.1 Create Task

Client sends a workflow execution request:

- `template_id`
- `input`
- optional overrides
- optional resume or fork parameters

The system:

- validates request
- creates a `task_run`
- persists initial execution context
- enqueues background execution
- returns `task_id`

### 4.2 Query Task

Client queries by `task_id` to retrieve:

- task status
- overall progress
- current step
- step list
- artifact list
- available checkpoints

### 4.3 Inspect Step or Artifact

Client can retrieve details for:

- specific step run
- specific artifact
- specific checkpoint

### 4.4 Resume or Fork

Client can create a new task from:

- prior `checkpoint_id`
- prior `artifact_id`
- prior `task_id` and `start_node_key`

## 5. Progress Model

Progress should not be based only on elapsed time. It should be derived from planned nodes and their weighted execution importance.

Suggested fields:

- `planned_step_count`
- `completed_step_count`
- `weighted_progress`
- `current_step_run_id`
- `current_node_key`

Node weights can differ. For example:

- search fanout nodes: lower individual weight
- large merge node: moderate weight
- final report generation: higher weight

## 6. LangGraph Usage Pattern

## 6.1 What Goes Into Graph State

Graph state should remain lightweight and contain:

- `task_run_id`
- `template_id`
- current control state
- references to prior step outputs
- branch coordination metadata
- retry state

## 6.2 What Should Not Go Into Graph State

Large documents and full payloads should not live inside graph state:

- raw search responses
- page content
- full normalized datasets
- large LLM outputs

These should be stored in artifact storage and referenced by ID.

## 6.3 Subgraphs

Use subgraphs to encapsulate common logic:

- search fanout subgraph
- document normalization subgraph
- classification subgraph
- report generation subgraph

This allows reuse across workflows without duplicating execution logic.

## 7. Cache and Reuse Model

## 7.1 Automatic Step Cache

Each cacheable step computes a `cache_key` based on:

- template ID and version if relevant
- node key
- normalized input hash
- provider configuration version
- model profile version if LLM-based
- prompt version if LLM-based

If cache hits:

- create a new `step_run` with `status = cached`
- attach reused artifact IDs
- record source lineage
- skip external invocation

## 7.2 Checkpoint Resume

Resume should be supported via explicit checkpoint objects:

- load upstream state references
- rebuild graph state
- continue from the next executable node

## 7.3 Artifact-Based Fork

Fork should support a different workflow template starting from an existing artifact.

Example:

- prior search-and-dedup output artifact
- new workflow for event summary
- skip search and dedup entirely

## 7.4 Step Input Artifact References

Each `step_run` should record which upstream artifacts it consumed.

Recommended field:

- `input_artifact_refs`

This makes the workflow traceable at execution time, not only after offline lineage reconstruction.

## 7.5 Artifact Lineage

Every downstream artifact should be traceable to one or more upstream artifacts through an explicit lineage relation.

Recommended relation:

- `derived_from`

This supports:

- replay analysis
- downstream reuse inspection
- debugging incorrect generated outputs
- future graph-style lineage visualization

## 8. Idempotency Model

External task creation should support an `idempotency_key`.

Suggested uniqueness scope:

- tenant ID
- template ID
- template version
- idempotency key

If the same request is submitted again within the business time window:

- return the existing `task_run`
- do not create a duplicate task

## 9. Failure and Retry Model

Not all failures should be retried in the same way.

### 9.1 Retryable Failures

- network timeout
- provider rate limit
- transient search API errors
- temporary MCP tool unavailability

### 9.2 Non-Retryable Failures

- invalid input schema
- unsupported workflow configuration
- missing credential configuration

### 9.3 Conditional Retry

Some LLM failures should trigger fallback instead of blind retry:

- malformed structured output
- context overflow
- model unavailability

Possible recovery:

- retry same provider
- switch to fallback model profile
- run output repair parser

## 10. Manual Intervention Points

Some workflows may need optional approval points:

- review retrieved evidence before report generation
- confirm source filtering policy
- review low-confidence conclusions

This should use `waiting_manual` state and preserve all prior artifacts.

## 11. Example Runtime Pattern

```text
task_run created
  -> search fanout steps execute in parallel
  -> merge search results
  -> normalize and classify
  -> deduplicate
  -> create checkpoint
  -> downstream LLM analysis
  -> final report artifact
  -> task_run succeeded
```

## 12. Why Step Number Is Not Enough

Do not rely on human-readable sequence numbers alone for downstream reuse.

Use these stable identifiers instead:

- `node_key` for template-level identity
- `step_run_id` for runtime identity
- `artifact_id` for reusable output
- `checkpoint_id` for resumable state boundary

This avoids breakage when workflow versions change.
