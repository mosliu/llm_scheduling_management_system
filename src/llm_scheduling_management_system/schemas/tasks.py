from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ResumeFromRequest(BaseModel):
    checkpoint_id: str | None = None
    artifact_id: str | None = None

    @model_validator(mode="after")
    def validate_single_source(self) -> "ResumeFromRequest":
        provided_count = int(bool(self.checkpoint_id)) + int(bool(self.artifact_id))
        if provided_count != 1:
            raise ValueError("resume_from requires exactly one of checkpoint_id or artifact_id")
        return self


class ForkFromRequest(BaseModel):
    task_id: str
    start_node_key: str


class CreateTaskRequest(BaseModel):
    template_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    tenant_id: str = "default"
    resume_from: ResumeFromRequest | None = None
    fork_from: ForkFromRequest | None = None

    @model_validator(mode="after")
    def validate_resume_and_fork(self) -> "CreateTaskRequest":
        if self.resume_from and self.fork_from:
            raise ValueError("resume_from and fork_from cannot be used together")
        return self


class ArtifactReferenceResponse(BaseModel):
    artifact_id: str
    artifact_type: str
    artifact_level: str


class CheckpointReferenceResponse(BaseModel):
    checkpoint_id: str
    based_on_step_run_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)


class StepRunResponse(BaseModel):
    step_run_id: str
    node_key: str
    title: str
    status: str
    progress: float
    input_artifact_refs: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    cache_hit: bool
    error_code: str | None = None
    error_message: str | None = None


class TaskSummaryResponse(BaseModel):
    task_id: str
    template_id: str
    template_version: str
    status: str
    progress: float
    planned_step_count: int
    completed_step_count: int
    current_step: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None


class CreateTaskResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    query_url: str


class TaskDetailResponse(TaskSummaryResponse):
    steps: list[StepRunResponse] = Field(default_factory=list)
    artifacts: list[ArtifactReferenceResponse] = Field(default_factory=list)
    available_checkpoints: list[CheckpointReferenceResponse] = Field(default_factory=list)


class WorkflowTemplateResponse(BaseModel):
    template_id: str
    name: str
    category: str
    description: str | None = None
    latest_version: str


class WorkflowTemplateStepBlueprintResponse(BaseModel):
    node_key: str
    node_type: str
    title: str
    sequence_no: int


class WorkflowTemplateDetailResponse(WorkflowTemplateResponse):
    steps: list[WorkflowTemplateStepBlueprintResponse] = Field(default_factory=list)


class StepDetailResponse(BaseModel):
    step_run_id: str
    task_run_id: str
    node_key: str
    node_type: str
    title: str
    status: str
    progress: float
    attempt_no: int
    sequence_no: int
    input_artifact_refs: list[str] = Field(default_factory=list)
    input_snapshot: dict[str, Any]
    output_summary: dict[str, Any]
    cache_key: str | None = None
    cache_hit: bool
    provider_snapshot: dict[str, Any]
    profile_snapshot: dict[str, Any]
    artifact_ids: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class ArtifactDetailResponse(BaseModel):
    artifact_id: str
    task_run_id: str
    step_run_id: str | None = None
    artifact_type: str
    artifact_level: str
    schema_name: str
    schema_version: str
    reusable_flag: bool
    content_json: dict[str, Any]
    content_text: str | None = None
    blob_uri: str | None = None
    content_hash: str | None = None


class ArtifactLineageEdgeResponse(BaseModel):
    lineage_id: str
    from_artifact_id: str
    to_artifact_id: str
    relation_type: str


class SearchInvocationResponse(BaseModel):
    invocation_id: str
    provider_name: str
    provider_vendor: str
    query_text: str
    result_count: int
    request_metadata: dict[str, Any]
    response_metadata: dict[str, Any]


class FetchInvocationResponse(BaseModel):
    invocation_id: str
    provider_name: str
    provider_vendor: str
    url: str
    title: str | None = None
    request_metadata: dict[str, Any]
    response_metadata: dict[str, Any]


class ToolInvocationResponse(BaseModel):
    invocation_id: str
    server_name: str
    tool_name: str
    arguments_json: dict[str, Any]
    response_json: dict[str, Any]
    status: str


class LLMInvocationResponse(BaseModel):
    invocation_id: str
    provider_name: str
    provider_type: str
    profile_name: str
    model_name: str
    prompt_text: str
    response_text: str
    request_metadata: dict[str, Any]
    response_metadata: dict[str, Any]


class ConfiguredProviderResponse(BaseModel):
    name: str
    provider_type: str
    vendor: str
    enabled: bool
    base_url: str | None = None


class ConfiguredLLMProviderResponse(BaseModel):
    name: str
    provider_type: str
    base_url: str


class ConfiguredLLMProfileResponse(BaseModel):
    name: str
    provider: str
    model: str
    structured_output: bool
    fallback_profiles: list[str] = Field(default_factory=list)


class SourceRegistryEntryResponse(BaseModel):
    domain: str
    region_hint: str
    publisher_type: str
    language: str
    official: bool


class MCPServerResponse(BaseModel):
    name: str
    transport: str
    enabled: bool
    simulate: bool
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None


class CheckpointDetailResponse(BaseModel):
    checkpoint_id: str
    task_run_id: str
    step_run_id: str | None = None
    node_key: str
    checkpoint_type: str
    state_ref: dict[str, Any]
    artifact_refs: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class RunTaskResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    planned_step_count: int
    completed_step_count: int


class FinalReportResponse(BaseModel):
    task_id: str
    task_status: str
    ready: bool
    report_state: str
    artifact_id: str | None = None
    step_run_id: str | None = None
    report_text: str | None = None
    generated_at: datetime | None = None
    llm_profile_name: str | None = None
    llm_model_name: str | None = None
    llm_invocation_id: str | None = None
    timeline_count: int = 0
    official_response_count: int = 0
    media_viewpoint_count: int = 0
    public_viewpoint_count: int = 0
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    official_responses: list[dict[str, Any]] = Field(default_factory=list)
    media_viewpoints: list[dict[str, Any]] = Field(default_factory=list)
    public_viewpoints: list[dict[str, Any]] = Field(default_factory=list)
    message: str | None = None


class CreateDerivedTaskRequest(BaseModel):
    template_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    tenant_id: str = "default"
    artifact_id: str | None = None


class TaskEventResponse(BaseModel):
    event_id: str
    task_run_id: str
    step_run_id: str | None = None
    event_type: str
    status: str | None = None
    payload: dict[str, Any]
    created_at: datetime


class TaskStatsResponse(BaseModel):
    task_id: str
    status: str
    planned_step_count: int
    completed_step_count: int
    step_status_counts: dict[str, int]
    artifact_count: int
    document_count: int
    artifact_type_counts: dict[str, int]
    cached_step_count: int
    search_hit_count: int
    search_invocation_count: int
    fetch_invocation_count: int
    tool_invocation_count: int
    llm_invocation_count: int
    event_count: int


class TaskGraphNodeResponse(BaseModel):
    node_id: str
    node_kind: str
    label: str
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskGraphEdgeResponse(BaseModel):
    edge_id: str
    edge_kind: str
    from_node_id: str
    to_node_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskGraphResponse(BaseModel):
    task_id: str
    nodes: list[TaskGraphNodeResponse] = Field(default_factory=list)
    edges: list[TaskGraphEdgeResponse] = Field(default_factory=list)


class TaskBundleResponse(BaseModel):
    task: TaskDetailResponse
    stats: TaskStatsResponse
    events: list[TaskEventResponse] = Field(default_factory=list)
    search_hits: list[SearchHitResponse] = Field(default_factory=list)
    documents: list[DocumentResponse] = Field(default_factory=list)
    search_invocations: list[SearchInvocationResponse] = Field(default_factory=list)
    fetch_invocations: list[FetchInvocationResponse] = Field(default_factory=list)
    tool_invocations: list[ToolInvocationResponse] = Field(default_factory=list)
    llm_invocations: list[LLMInvocationResponse] = Field(default_factory=list)


class SystemStatusResponse(BaseModel):
    app_name: str
    template_count: int
    provider_counts: dict[str, int]
    task_status_counts: dict[str, int]
    total_tasks: int


class SearchHitResponse(BaseModel):
    search_hit_id: str
    provider_name: str
    query_text: str
    title: str
    source_domain: str
    source_type: str
    region_hint: str | None = None
    publisher_type: str | None = None
    snippet: str | None = None
    published_at_utc: str | None = None
    metadata: dict[str, Any]


class DocumentResponse(BaseModel):
    document_id: str
    provider_name: str
    url: str
    canonical_url: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None
    source_domain: str | None = None
    source_type: str | None = None
    region_hint: str | None = None
    publisher_type: str | None = None
    published_at_utc: str | None = None
    content_text: str
    content_hash: str | None = None
    metadata: dict[str, Any]
