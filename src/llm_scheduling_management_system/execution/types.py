from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchInvocationRecord:
    """搜索服务调用记录。

    用途:
        用于记录工作流步骤中对外部搜索服务（如 Search API）的单次调用元数据和结果统计。

    用法:
        实例化并附加到步骤执行结果的 search_invocations 列表中。

    @Author: mosliu
    """
    provider_name: str
    provider_vendor: str
    query_text: str
    result_count: int
    request_metadata: dict[str, Any] = field(default_factory=dict)
    response_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchInvocationRecord:
    """网页获取/内容提取服务调用记录。

    用途:
        用于记录工作流步骤中获取特定 URL 内容的调用元数据和返回内容摘要。

    用法:
        实例化并附加到步骤执行结果的 fetch_invocations 列表中。

    @Author: mosliu
    """
    provider_name: str
    provider_vendor: str
    url: str
    title: str | None = None
    request_metadata: dict[str, Any] = field(default_factory=dict)
    response_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolInvocationRecord:
    """MCP 工具调用记录。

    用途:
        用于记录工作流中通过 Model Context Protocol (MCP) 调用的工具、参数以及返回的响应内容。

    用法:
        实例化并附加到步骤执行结果的 tool_invocations 列表中。

    @Author: mosliu
    """
    server_name: str
    tool_name: str
    arguments_json: dict[str, Any] = field(default_factory=dict)
    response_json: dict[str, Any] = field(default_factory=dict)
    status: str = "completed"


@dataclass(slots=True)
class LLMInvocationRecord:
    """大语言模型 (LLM) 调用记录。

    用途:
        用于记录工作流步骤中对 LLM 的调用，包含提示词、响应文本、模型及服务提供商元数据。

    用法:
        实例化并附加到步骤执行结果的 llm_invocations 列表中。

    @Author: mosliu
    """
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
    """步骤执行结果及元数据记录。

    用途:
        承载工作流中单个步骤（Step Executor）执行后的输出内容、产生的生成物（Artifact）元数据，
        以及执行该步骤期间所有的外部调用记录（搜索、网页获取、工具、LLM 调用）。

    用法:
        由 Executor 执行完成后返回，用于持久化步骤运行结果和运行日志。

    @Author: mosliu
    """
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
