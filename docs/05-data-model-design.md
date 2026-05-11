# Data Model Design

## 1. Goal

Design a persistent data model that supports:

- workflow definition
- asynchronous task execution
- step-level visibility
- artifact persistence
- cache hit reuse
- checkpoint resume
- artifact-based fork
- provider and prompt traceability
- audit and multi-tenant governance

## 2. Storage Strategy

Recommended early-stage storage stack:

- PostgreSQL for transactional metadata
- Redis for locks, queues, ephemeral cache, and coordination
- MinIO for large payloads and raw artifacts
- pgvector for vector retrieval
- optional OpenSearch or Elasticsearch for later full-text search

## 3. Main Entity Groups

### 3.1 Workflow Definition

- `workflow_template`
- `workflow_template_version`
- `workflow_node_template`
- `workflow_edge_template`

### 3.2 Runtime Execution

- `task_run`
- `step_run`
- `checkpoint`

### 3.3 Data Outputs

- `artifact`
- `artifact_lineage`
- `document`
- `search_hit`

### 3.4 LLM and Tool Traceability

- `llm_provider`
- `llm_profile`
- `llm_profile_version`
- `prompt_template`
- `prompt_template_version`
- `llm_invocation`
- `search_invocation`
- `fetch_invocation`
- `tool_invocation`

### 3.5 Runtime Timeline

- `task_event`

### 3.6 Governance and Audit

- `tenant`
- `app_user`
- `api_key`
- `audit_log`

## 4. Recommended Core Tables

## 4.1 workflow_template

Purpose:

- logical template identity

Suggested fields:

- `id`
- `name`
- `category`
- `status`
- `latest_version`
- `created_at`
- `updated_at`

## 4.2 workflow_template_version

Purpose:

- immutable workflow definition version

Suggested fields:

- `id`
- `template_id`
- `version`
- `graph_definition_json`
- `input_schema_json`
- `output_schema_json`
- `default_routing_policy_json`
- `status`
- `created_at`

## 4.3 task_run

Purpose:

- one externally visible workflow execution

Suggested fields:

- `id`
- `tenant_id`
- `template_id`
- `template_version_id`
- `status`
- `input_payload_json`
- `options_json`
- `progress_percent`
- `current_step_run_id`
- `idempotency_key`
- `forked_from_task_run_id`
- `resume_from_checkpoint_id`
- `created_at`
- `started_at`
- `updated_at`
- `ended_at`

## 4.4 step_run

Purpose:

- one execution record for one node

Suggested fields:

- `id`
- `task_run_id`
- `node_key`
- `node_type`
- `status`
- `attempt_no`
- `sequence_no`
- `input_artifact_refs`
- `input_snapshot_json`
- `output_summary_json`
- `cache_key`
- `cache_hit`
- `provider_snapshot_json`
- `profile_snapshot_json`
- `started_at`
- `ended_at`
- `error_code`
- `error_message`

## 4.5 artifact

Purpose:

- general persistent output object

Suggested fields:

- `id`
- `tenant_id`
- `task_run_id`
- `step_run_id`
- `artifact_type`
- `artifact_level`
- `schema_name`
- `schema_version`
- `content_json`
- `content_text`
- `blob_uri`
- `content_hash`
- `size_bytes`
- `reusable_flag`
- `ttl_expire_at`
- `created_at`

Recommended `artifact_level` values:

- `raw`
- `normalized`
- `derived`
- `final`

## 4.6 artifact_lineage

Purpose:

- explicit lineage relationships between artifacts

Suggested fields:

- `id`
- `from_artifact_id`
- `to_artifact_id`
- `relation_type`
- `created_at`

Possible relations:

- `derived_from`
- `cached_from`
- `forked_from`
- `merged_from`

## 4.7 checkpoint

Purpose:

- resumable state boundary

Suggested fields:

- `id`
- `task_run_id`
- `step_run_id`
- `node_key`
- `checkpoint_type`
- `state_ref_json`
- `artifact_refs_json`
- `created_at`
- `expires_at`

## 4.8 search_hit

Purpose:

- preserve normalized search hit data

Suggested fields:

- `id`
- `task_run_id`
- `step_run_id`
- `provider`
- `query_text`
- `source_name`
- `source_domain`
- `source_url`
- `title`
- `snippet`
- `language`
- `country_hint`
- `region_hint`
- `source_type`
- `publisher_type`
- `published_at_original`
- `published_at_utc`
- `discovered_at_utc`
- `raw_score`
- `normalized_score`
- `raw_payload_ref`

## 4.9 document

Purpose:

- fetched or known document entity

Suggested fields:

- `id`
- `source_url`
- `canonical_url`
- `title`
- `author`
- `language`
- `region_hint`
- `publisher_type`
- `published_at_utc`
- `fetched_at_utc`
- `indexed_at_utc`
- `content_hash`
- `raw_content_ref`
- `clean_content_ref`
- `source_domain`
- `country_final`
- `region_final`
- `source_type_final`
- `publisher_type_final`
- `credibility_score`

In the current scaffold:

- `task_run_id`
- `step_run_id`
- `provider_name`
- `url`
- `canonical_url`
- `title`
- `author`
- `language`
- `source_domain`
- `source_type`
- `region_hint`
- `publisher_type`
- `published_at_utc`
- `content_text`
- `content_hash`
- `extra_metadata`

## 4.10 llm_invocation

Purpose:

- persist each model call for audit and replay

Suggested fields:

- `id`
- `task_run_id`
- `step_run_id`
- `provider`
- `model_name`
- `profile_id`
- `profile_version_id`
- `profile_snapshot_json`
- `prompt_template_id`
- `prompt_template_version_id`
- `rendered_prompt_hash`
- `input_artifact_refs_json`
- `request_payload_ref`
- `response_payload_ref`
- `input_tokens`
- `output_tokens`
- `latency_ms`
- `finish_reason`
- `cost_amount`
- `cost_currency`
- `retry_count`
- `fallback_from_invocation_id`
- `created_at`

## 4.11 search_invocation

Purpose:

- persist each search provider call

Suggested fields:

- `id`
- `task_run_id`
- `step_run_id`
- `provider`
- `query_text`
- `request_payload_ref`
- `response_payload_ref`
- `latency_ms`
- `result_count`
- `status`
- `created_at`

## 4.12 fetch_invocation

Purpose:

- persist each fetch provider call

Suggested fields:

- `id`
- `task_run_id`
- `step_run_id`
- `provider_name`
- `provider_vendor`
- `url`
- `title`
- `request_metadata`
- `response_metadata`
- `created_at`

## 4.13 task_event

Purpose:

- persist durable task lifecycle and step lifecycle events

Suggested fields:

- `id`
- `task_run_id`
- `step_run_id`
- `event_type`
- `status`
- `payload`
- `created_at`

## 4.14 tool_invocation

Purpose:

- persist each MCP or other tool call

Suggested fields:

- `id`
- `task_run_id`
- `step_run_id`
- `tool_type`
- `server_name`
- `tool_name`
- `arguments_json`
- `response_ref`
- `latency_ms`
- `status`
- `created_at`

## 5. Retention Strategy

Retention should vary by artifact type.

Suggested policy examples:

- raw search payloads: 3 to 7 days
- normalized hits: 7 to 30 days
- fetched cleaned content: 7 to 30 days
- derived analysis artifacts: longer retention
- final reports: long retention
- audit and invocation metadata: long retention

Retention should be configurable per tenant and per artifact class.

## 6. Multi-Tenant Considerations

Every main runtime entity should be tenant-aware where applicable.

At minimum:

- `task_run`
- `artifact`
- `checkpoint`
- `api_key`
- cost accounting records

Tenant-scoped visibility should be enforced in both query APIs and storage access.

## 7. Replay and Audit Requirements

To support replay, the system must preserve:

- template version
- node key
- provider snapshot
- profile snapshot
- prompt version
- input artifact references

To support audit, the system must preserve:

- who started the task
- what configuration was used
- what providers were called
- what outputs were produced

## 8. Lineage Principle

Every important downstream artifact should be traceable back to:

- upstream artifacts
- step runs
- task runs
- provider and prompt configurations

This is critical for public-opinion and evidence-driven workflows.

The current scaffold already persists:

- step input artifact refs
- artifact lineage edges
- task events
- search / fetch / llm invocations
- search hits
- fetched documents
