from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ResumeFromRequest(BaseModel):
    """任务恢复请求参数模型。

    用途:
        用于指定从哪个 checkpoint 或 artifact 恢复任务执行。

    用法:
        request = ResumeFromRequest(checkpoint_id="cp_123")

    @Author: mosliu
    """
    checkpoint_id: str | None = None
    artifact_id: str | None = None

    @model_validator(mode="after")
    def validate_single_source(self) -> "ResumeFromRequest":
        """验证恢复源的唯一性。

        用途:
            确保 checkpoint_id 和 artifact_id 恰好提供且仅提供其中一个。

        用法:
            model.validate_single_source()

        @Author: mosliu
        """
        provided_count = int(bool(self.checkpoint_id)) + int(bool(self.artifact_id))
        if provided_count != 1:
            raise ValueError("resume_from requires exactly one of checkpoint_id or artifact_id")
        return self


class ForkFromRequest(BaseModel):
    """任务分叉请求参数模型。

    用途:
        用于指定从已有任务分叉新任务时的任务 ID 及起始节点。

    用法:
        request = ForkFromRequest(task_id="task_123", start_node_key="step_1")

    @Author: mosliu
    """
    task_id: str
    start_node_key: str


class CreateTaskRequest(BaseModel):
    """创建任务的请求数据模型。

    用途:
        定义创建新调度任务所需的参数，包括模板 ID、输入参数、选项参数、幂等键、租户 ID 以及恢复/分叉配置。

    用法:
        request = CreateTaskRequest(template_id="tpl_123", input={"query": "test"})

    @Author: mosliu
    """
    template_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    tenant_id: str = "default"
    resume_from: ResumeFromRequest | None = None
    fork_from: ForkFromRequest | None = None

    @model_validator(mode="after")
    def validate_resume_and_fork(self) -> "CreateTaskRequest":
        """验证恢复与分叉配置互斥。

        用途:
            确保不能同时指定 resume_from 和 fork_from。

        用法:
            model.validate_resume_and_fork()

        @Author: mosliu
        """
        if self.resume_from and self.fork_from:
            raise ValueError("resume_from and fork_from cannot be used together")
        return self


class ArtifactReferenceResponse(BaseModel):
    """Artifact 引用响应模型。

    用途:
        在外部接口中，精简地表示一个 Artifact 的标识、类型和级别。

    用法:
        response = ArtifactReferenceResponse(artifact_id="art_123", artifact_type="report", artifact_level="task")

    @Author: mosliu
    """
    artifact_id: str
    artifact_type: str
    artifact_level: str


class CheckpointReferenceResponse(BaseModel):
    """任务检查点引用响应模型。

    用途:
        描述一个 Checkpoint 的基本引用信息，包括基于哪个步骤 ID、以及生成的 Artifact ID 列表。

    用法:
        response = CheckpointReferenceResponse(checkpoint_id="cp_123", based_on_step_run_id="step_abc")

    @Author: mosliu
    """
    checkpoint_id: str
    based_on_step_run_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)


class StepRunResponse(BaseModel):
    """步骤执行状态响应模型。

    用途:
        在任务详情中反映单个步骤的执行进度、状态、输出 Artifact 以及错误信息等。

    用法:
        response = StepRunResponse(step_run_id="step_abc", node_key="step_1", title="步骤1", status="succeeded", progress=100.0, cache_hit=False)

    @Author: mosliu
    """
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
    """任务概要响应模型。

    用途:
        用于描述任务的概要运行信息，包括任务 ID、模板、状态、输入参数、调度进度、以及起止时间等。

    用法:
        response = TaskSummaryResponse(task_id="task_123", template_id="tpl_abc", template_version="1.0", status="running", progress=50.0, planned_step_count=4, completed_step_count=2, created_at=utcnow(), updated_at=utcnow())

    @Author: mosliu
    """
    task_id: str
    template_id: str
    template_version: str
    status: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    options_payload: dict[str, Any] = Field(default_factory=dict)
    progress: float
    planned_step_count: int
    completed_step_count: int
    current_step: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None


class CreateTaskResponse(BaseModel):
    """任务创建成功的响应模型。

    用途:
        向用户返回新建任务的 ID、初始状态、进度以及供轮询任务状态的 URL。

    用法:
        response = CreateTaskResponse(task_id="task_123", status="pending", progress=0.0, query_url="/api/tasks/task_123")

    @Author: mosliu
    """
    task_id: str
    status: str
    progress: float
    query_url: str


class TaskDetailResponse(TaskSummaryResponse):
    """任务详情响应模型。

    用途:
        继承自 TaskSummaryResponse，包含更丰富的子步骤执行记录、生成的 Artifacts 以及可供恢复的 Checkpoints 列表。

    用法:
        response = TaskDetailResponse(...)

    @Author: mosliu
    """
    steps: list[StepRunResponse] = Field(default_factory=list)
    artifacts: list[ArtifactReferenceResponse] = Field(default_factory=list)
    available_checkpoints: list[CheckpointReferenceResponse] = Field(default_factory=list)


class WorkflowTemplateResponse(BaseModel):
    """工作流模板基本信息响应模型。

    用途:
        展示系统内置的工作流模板的基础参数，包括模板 ID、分类、名称及最新版本等。

    用法:
        response = WorkflowTemplateResponse(template_id="tpl_abc", name="示例模板", category="search", latest_version="1.0")

    @Author: mosliu
    """
    template_id: str
    name: str
    category: str
    description: str | None = None
    latest_version: str


class WorkflowTemplateStepBlueprintResponse(BaseModel):
    """工作流模板中步骤蓝图响应模型。

    用途:
        反映模板中单个步骤的节点标识、节点类型、标题和顺序编号。

    用法:
        response = WorkflowTemplateStepBlueprintResponse(node_key="step_1", node_type="search", title="搜索", sequence_no=1)

    @Author: mosliu
    """
    node_key: str
    node_type: str
    title: str
    sequence_no: int


class WorkflowTemplateDetailResponse(WorkflowTemplateResponse):
    """工作流模板详细配置响应模型。

    用途:
        继承自 WorkflowTemplateResponse，增加了该工作流下属的所有步骤蓝图列表信息。

    用法:
        response = WorkflowTemplateDetailResponse(...)

    @Author: mosliu
    """
    steps: list[WorkflowTemplateStepBlueprintResponse] = Field(default_factory=list)


class StepDetailResponse(BaseModel):
    """步骤详情响应模型。

    用途:
        展示某个步骤执行的全面上下文，包括快照数据（输入快照、模型与配置快照）、执行进度、缓存命中情况、关联的 Artifact 列表以及可能发生的错误详情。

    用法:
        response = StepDetailResponse(...)

    @Author: mosliu
    """
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
    """Artifact 详情响应模型。

    用途:
        反映特定步骤生成的 Artifact 的全部明细内容，包含 JSON 内容、文本内容、Blob 地址及内容哈希等。

    用法:
        response = ArtifactDetailResponse(...)

    @Author: mosliu
    """
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
    """Artifact 谱系关系响应模型。

    用途:
        描述 Artifact 之间的推导或依赖关系图中的一条有向边。

    用法:
        response = ArtifactLineageEdgeResponse(lineage_id="edge_1", from_artifact_id="art_1", to_artifact_id="art_2", relation_type="derived_from")

    @Author: mosliu
    """
    lineage_id: str
    from_artifact_id: str
    to_artifact_id: str
    relation_type: str


class SearchInvocationResponse(BaseModel):
    """搜索服务调用记录响应模型。

    用途:
        记录步骤执行期间对外部搜索引擎（如 Tavily, Google 等）调用的详细元数据。

    用法:
        response = SearchInvocationResponse(...)

    @Author: mosliu
    """
    invocation_id: str
    provider_name: str
    provider_vendor: str
    query_text: str
    result_count: int
    request_metadata: dict[str, Any]
    response_metadata: dict[str, Any]


class FetchInvocationResponse(BaseModel):
    """网页抓取服务调用记录响应模型。

    用途:
        记录步骤执行期间网页抓取服务（如 crawl/fetch 等接口）对指定 URL 进行内容提取调用的元数据。

    用法:
        response = FetchInvocationResponse(...)

    @Author: mosliu
    """
    invocation_id: str
    provider_name: str
    provider_vendor: str
    url: str
    title: str | None = None
    request_metadata: dict[str, Any]
    response_metadata: dict[str, Any]


class ToolInvocationResponse(BaseModel):
    """MCP 工具调用记录响应模型。

    用途:
        用于记录在步骤执行中对 MCP 服务器工具调用的入参、出参和状态。

    用法:
        response = ToolInvocationResponse(...)

    @Author: mosliu
    """
    invocation_id: str
    server_name: str
    tool_name: str
    arguments_json: dict[str, Any]
    response_json: dict[str, Any]
    status: str


class LLMInvocationResponse(BaseModel):
    """大语言模型调用记录响应模型。

    用途:
        记录步骤执行期间对大语言模型进行交互调用的关键信息，如提示词、回复内容、使用的模型和元数据。

    用法:
        response = LLMInvocationResponse(...)

    @Author: mosliu
    """
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
    """配置的服务提供商响应模型。

    用途:
        展示系统中已注册配置的通用服务提供商（如搜索提供商）的基本设置 and 启用状态。

    用法:
        response = ConfiguredProviderResponse(name="exa", provider_type="search", vendor="exa", enabled=True)

    @Author: mosliu
    """
    name: str
    provider_type: str
    vendor: str
    enabled: bool
    base_url: str | None = None


class ConfiguredLLMProviderResponse(BaseModel):
    """配置的 LLM 服务提供商响应模型。

    用途:
        展示系统中已配置的 LLM 供应商的名称、类型和基础端点。

    用法:
        response = ConfiguredLLMProviderResponse(name="openai", provider_type="openai", base_url="https://api.openai.com/v1")

    @Author: mosliu
    """
    name: str
    provider_type: str
    base_url: str


class ConfiguredLLMProfileResponse(BaseModel):
    """配置的 LLM Profile 响应模型。

    用途:
        描述系统在模型路由中预设的 Profile 配置，如名称、底层所用供应商与模型、是否使用结构化输出及后备 fallback Profile。

    用法:
        response = ConfiguredLLMProfileResponse(name="gpt-4o", provider="openai", model="gpt-4o", structured_output=True)

    @Author: mosliu
    """
    name: str
    provider: str
    model: str
    structured_output: bool
    fallback_profiles: list[str] = Field(default_factory=list)


class SourceRegistryEntryResponse(BaseModel):
    """可信数据源配置响应模型。

    用途:
        展示数据源白名单或数据源特征库中的配置条目，如域名、官方属性、主要语言等。

    用法:
        response = SourceRegistryEntryResponse(domain="gov.cn", region_hint="cn", publisher_type="government", language="zh", official=True)

    @Author: mosliu
    """
    domain: str
    region_hint: str
    publisher_type: str
    language: str
    official: bool


class MCPServerResponse(BaseModel):
    """MCP 服务注册配置响应模型。

    用途:
        展示向系统注册的 MCP (Model Context Protocol) 服务的连接方式、状态及运行参数。

    用法:
        response = MCPServerResponse(name="sqlite-mcp", transport="stdio", enabled=True, simulate=False)

    @Author: mosliu
    """
    name: str
    transport: str
    enabled: bool
    simulate: bool
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None


class CheckpointDetailResponse(BaseModel):
    """检查点详情响应模型。

    用途:
        展示任务运行中生成的特定检查点的详细状态数据，包括引用的 Artifact 列表和过期时间。

    用法:
        response = CheckpointDetailResponse(...)

    @Author: mosliu
    """
    checkpoint_id: str
    task_run_id: str
    step_run_id: str | None = None
    node_key: str
    checkpoint_type: str
    state_ref: dict[str, Any]
    artifact_refs: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class RunTaskResponse(BaseModel):
    """触发任务运行的响应模型。

    用途:
        用于在异步触发或恢复任务运行时，快速返回当前的任务状态与步骤执行进度概况。

    用法:
        response = RunTaskResponse(task_id="task_123", status="running", progress=25.0, planned_step_count=4, completed_step_count=1)

    @Author: mosliu
    """
    task_id: str
    status: str
    progress: float
    planned_step_count: int
    completed_step_count: int


class FinalReportResponse(BaseModel):
    """最终任务报告详情响应模型。

    用途:
        提供最终生成报告（如舆情分析、调查结果）的详细展示信息，包括提取的时间线、官方回应、媒体及公众观点。

    用法:
        response = FinalReportResponse(...)

    @Author: mosliu
    """
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
    """创建派生任务请求数据模型。

    用途:
        用于基于一个已有的 Artifact (例如前一阶段的产出) 派生启动新的工作流任务。

    用法:
        request = CreateDerivedTaskRequest(template_id="tpl_analyze", artifact_id="art_123")

    @Author: mosliu
    """
    template_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    tenant_id: str = "default"
    artifact_id: str | None = None


class TaskEventResponse(BaseModel):
    """任务运行事件响应模型。

    用途:
        在任务审计日志和调试日志中展示单条行为/状态变化事件的具体信息。

    用法:
        response = TaskEventResponse(...)

    @Author: mosliu
    """
    event_id: str
    task_run_id: str
    step_run_id: str | None = None
    event_type: str
    status: str | None = None
    payload: dict[str, Any]
    created_at: datetime


class TaskStatsResponse(BaseModel):
    """任务统计数据响应模型。

    用途:
        汇总显示单个任务运行的整体度量指标，如运行步骤总数、生成文件数、各服务（搜索、LLM、工具、爬虫）调用次数等。

    用法:
        response = TaskStatsResponse(...)

    @Author: mosliu
    """
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
    """任务流程图节点数据响应模型。

    用途:
        在前端展示可视化工作流图时，代表其中一个节点（如任务开始、特定执行步骤等）。

    用法:
        response = TaskGraphNodeResponse(node_id="step_1", node_kind="step", label="执行搜索")

    @Author: mosliu
    """
    node_id: str
    node_kind: str
    label: str
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskGraphEdgeResponse(BaseModel):
    """任务流程图连线数据响应模型。

    用途:
        在前端展示可视化工作流图时，代表节点之间的流转关系边。

    用法:
        response = TaskGraphEdgeResponse(edge_id="edge_1", edge_kind="dependency", from_node_id="start", to_node_id="step_1")

    @Author: mosliu
    """
    edge_id: str
    edge_kind: str
    from_node_id: str
    to_node_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskGraphResponse(BaseModel):
    """任务可视化流程图响应模型。

    用途:
        汇总任务包含的全部节点与边，方便前端渲染完整的任务状态流转图。

    用法:
        response = TaskGraphResponse(task_id="task_123", nodes=[...], edges=[...])

    @Author: mosliu
    """
    task_id: str
    nodes: list[TaskGraphNodeResponse] = Field(default_factory=list)
    edges: list[TaskGraphEdgeResponse] = Field(default_factory=list)


class TaskBundleResponse(BaseModel):
    """任务包合集数据响应模型。

    用途:
        一次性打包返回任务运行的全部关联数据（基本信息、统计、事件、搜索结果、文档及所有类型调用记录），供高级监控界面一次性加载。

    用法:
        response = TaskBundleResponse(...)

    @Author: mosliu
    """
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
    """系统运行状态响应模型。

    用途:
        描述当前系统的全局运行指标，如模板数、各引擎状态分布、累计处理的任务总数等。

    用法:
        response = SystemStatusResponse(...)

    @Author: mosliu
    """
    app_name: str
    template_count: int
    provider_counts: dict[str, int]
    task_status_counts: dict[str, int]
    total_tasks: int


class SearchHitResponse(BaseModel):
    """单条搜索命中详情响应模型。

    用途:
        在检索结果中细化表示一条从搜索引擎中命中的具体记录（网页摘要、发布时间、来源等）。

    用法:
        response = SearchHitResponse(...)

    @Author: mosliu
    """
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
    """单条抓取文档响应模型。

    用途:
        返回给客户端的已抓取网页文档的完整数据，包含正文文本、标题、元数据等。

    用法:
        response = DocumentResponse(...)

    @Author: mosliu
    """
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
