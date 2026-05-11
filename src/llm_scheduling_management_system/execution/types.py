from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchInvocationRecord:
    provider_name: str
    provider_vendor: str
    query_text: str
    result_count: int
    request_metadata: dict[str, Any] = field(default_factory=dict)
    response_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchInvocationRecord:
    provider_name: str
    provider_vendor: str
    url: str
    title: str | None = None
    request_metadata: dict[str, Any] = field(default_factory=dict)
    response_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolInvocationRecord:
    server_name: str
    tool_name: str
    arguments_json: dict[str, Any] = field(default_factory=dict)
    response_json: dict[str, Any] = field(default_factory=dict)
    status: str = "completed"


@dataclass(slots=True)
class LLMInvocationRecord:
    provider_name: str
    provider_type: str
    profile_name: str
    model_name: str
    prompt_text: str
    response_text: str
    request_metadata: dict[str, Any] = field(default_factory=dict)
    response_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StepExecutionResult:
    artifact_type: str
    artifact_level: str
    schema_name: str
    schema_version: str = "v1"
    content_json: dict[str, Any] = field(default_factory=dict)
    content_text: str | None = None
    checkpoint_type: str = "step_completed"
    reusable_flag: bool = True
    input_artifact_ids: list[str] = field(default_factory=list)
    search_invocations: list[SearchInvocationRecord] = field(default_factory=list)
    fetch_invocations: list[FetchInvocationRecord] = field(default_factory=list)
    tool_invocations: list[ToolInvocationRecord] = field(default_factory=list)
    llm_invocations: list[LLMInvocationRecord] = field(default_factory=list)
