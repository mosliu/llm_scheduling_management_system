from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_scheduling_management_system.db import Base, utf8mb4_longtext
from llm_scheduling_management_system.domain.enums import ArtifactLevel, StepStatus, TaskStatus


def utcnow() -> datetime:
    """获取当前的 UTC 时间。

    用途:
        生成带有时区感知（timezone-aware）的当前 UTC 时间。

    用法:
        current_time = utcnow()

    @Author: mosliu
    """
    return datetime.now(timezone.utc)


def generate_prefixed_id(prefix: str) -> str:
    """生成带有指定前缀的唯一标识符。

    用途:
        拼接传入的前缀与 uuid4 的前 24 个十六进制字符，用于各类实体的主键。

    用法:
        new_id = generate_prefixed_id("run")

    @Author: mosliu
    """
    return f"{prefix}_{uuid4().hex[:24]}"


class WorkflowTemplate(Base):
    """工作流模板数据库模型实体。

    用途:
        存储预定义的工作流模板元数据，包括名称、描述、分类、最新版本及状态等。

    用法:
        用于声明不同的工作流，关联具体执行的任务实例 TaskRun。

    @Author: mosliu
    """
    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="general")
    description: Mapped[str | None] = mapped_column(utf8mb4_longtext(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    latest_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    task_runs: Mapped[list[TaskRun]] = relationship(back_populates="template")


class TaskRun(Base):
    """任务运行实例数据库模型实体。

    用途:
        保存单次任务工作流的执行实例状态、输入、选项配置、进度以及在失败时恢复所必需的关联指针（如断点 ID、生成物 ID 等）。

    用法:
        管理并在各个步骤执行器中读写具体的任务执行状态。

    @Author: mosliu
    """
    __tablename__ = "task_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("run"))
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    template_id: Mapped[str] = mapped_column(ForeignKey("workflow_templates.id"), nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=TaskStatus.QUEUED.value)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    options_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_step_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forked_from_task_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resume_from_checkpoint_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resume_from_artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    planned_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    template: Mapped[WorkflowTemplate] = relationship(back_populates="task_runs")
    step_runs: Mapped[list[StepRun]] = relationship(back_populates="task_run", cascade="all, delete-orphan")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="task_run", cascade="all, delete-orphan")
    checkpoints: Mapped[list[Checkpoint]] = relationship(back_populates="task_run", cascade="all, delete-orphan")


class StepRun(Base):
    """步骤运行数据库模型实体。

    用途:
        保存属于某一个 TaskRun 下的单个步骤节点的运行状态、重试次数、输入快照、输出总结、缓存状态、耗时及出错信息等。

    用法:
        在工作流运行时，用以跟踪各步骤节点具体的状态变更。

    @Author: mosliu
    """
    __tablename__ = "step_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("step"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=StepStatus.PENDING.value)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_artifact_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    cache_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    profile_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(utf8mb4_longtext(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    task_run: Mapped[TaskRun] = relationship(back_populates="step_runs")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="step_run", cascade="all, delete-orphan")
    checkpoints: Mapped[list[Checkpoint]] = relationship(back_populates="step_run", cascade="all, delete-orphan")


class Artifact(Base):
    """生成物（Artifact）数据库模型实体。

    用途:
        持久化存储工作流步骤节点生成出的各种格式的结构化数据、文本、大型 BLOB 的 URI、哈希值以及其 TTL 过期时间等。

    用法:
        提供工作流内部状态复用或下一步骤节点的输入，亦可用于审计和对外呈现。

    @Author: mosliu
    """
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("art"))
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str | None] = mapped_column(ForeignKey("step_runs.id"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_level: Mapped[str] = mapped_column(String(32), nullable=False, default=ArtifactLevel.DERIVED.value)
    schema_name: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    content_text: Mapped[str | None] = mapped_column(utf8mb4_longtext(), nullable=True)
    blob_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reusable_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ttl_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    task_run: Mapped[TaskRun] = relationship(back_populates="artifacts")
    step_run: Mapped[StepRun | None] = relationship(back_populates="artifacts")


class ArtifactLineage(Base):
    """生成物血缘关系数据库模型实体。

    用途:
        保存生成物之间的衍生关系（Lineage），记录哪些生成物是由哪些父生成物经过步骤转换或聚合生成的。

    用法:
        提供工作流生成物的来源回溯审计与图关系渲染。

    @Author: mosliu
    """
    __tablename__ = "artifact_lineage"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("lin"))
    from_artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    to_artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, default="derived_from")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class SearchInvocation(Base):
    """搜索调用审计数据库模型实体。

    用途:
        记录在特定步骤中，调用特定搜索服务提供商时的输入关键词、调用结果数量以及请求与响应元数据，用于计费、追踪与监控。

    用法:
        在调用 Search Provider API 成功或失败后插入记录。

    @Author: mosliu
    """
    __tablename__ = "search_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("sinv"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_vendor: Mapped[str] = mapped_column(String(64), nullable=False)
    query_text: Mapped[str] = mapped_column(utf8mb4_longtext(), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class FetchInvocation(Base):
    """内容提取（Fetch）调用审计数据库模型实体。

    用途:
        记录在特定步骤中，调用网页提取服务时的 URL、页面标题、请求和响应元数据。

    用法:
        在调用 Fetch/Crawl Provider API 时插入，审计网页数据提取历史。

    @Author: mosliu
    """
    __tablename__ = "fetch_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("finv"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_vendor: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(utf8mb4_longtext(), nullable=False)
    title: Mapped[str | None] = mapped_column(utf8mb4_longtext(), nullable=True)
    request_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class LLMInvocation(Base):
    """LLM 调用审计数据库模型实体。

    用途:
        记录在特定步骤中，调用大模型时的 Prompt 内容、模型生成的 Response 内容，以及包含 Token 消耗、耗时等详细元数据。

    用法:
        在使用大模型接口返回数据后写入，用于模型调试、审计以及 Token 使用监控。

    @Author: mosliu
    """
    __tablename__ = "llm_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("linv"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_text: Mapped[str] = mapped_column(utf8mb4_longtext(), nullable=False)
    response_text: Mapped[str] = mapped_column(utf8mb4_longtext(), nullable=False)
    request_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class TaskEvent(Base):
    """任务事件日志数据库模型实体。

    用途:
        记录任务执行生命周期中的关键事件节点（如任务入队、任务启动、任务重试、步骤完成等），提供结构化的事件负载。

    用法:
        提供工作流系统向外通知、事件溯源或在控制台上渲染任务进度树的数据基础。

    @Author: mosliu
    """
    __tablename__ = "task_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("tev"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str | None] = mapped_column(ForeignKey("step_runs.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ToolInvocation(Base):
    """MCP 外部工具调用审计数据库模型实体。

    用途:
        记录向 MCP 服务端发起的各个 Tool 调用的名称、参数、返回值及调用状态。

    用法:
        当 LLM 或步骤节点触发 MCP 工具调用时，写入相关记录供追溯审计。

    @Author: mosliu
    """
    __tablename__ = "tool_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("tinv"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    server_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class SearchHitRecord(Base):
    """单条搜索结果记录（Hit）数据库模型实体。

    用途:
        持久化存储搜索出来的具体网页标题、域名、网页摘要（snippet）、发布时间以及所属搜索服务商与源类型。

    用法:
        在执行搜索步骤时产生，作为后续内容提取（Fetch）或总结（Summary）的数据源。

    @Author: mosliu
    """
    __tablename__ = "search_hits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("shit"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    query_text: Mapped[str] = mapped_column(utf8mb4_longtext(), nullable=False)
    title: Mapped[str] = mapped_column(utf8mb4_longtext(), nullable=False)
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    region_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publisher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    snippet: Mapped[str | None] = mapped_column(utf8mb4_longtext(), nullable=True)
    published_at_utc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class DocumentRecord(Base):
    """已提取文档数据库模型实体。

    用途:
        保存被下载、解析并清洗后的网页完整正文文本或文档，包含语言、作者、发布日期及来源域名分析。

    用法:
        作为后续长文本总结或知识检索（RAG）的输入源。

    @Author: mosliu
    """
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("doc"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(utf8mb4_longtext(), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(utf8mb4_longtext(), nullable=True)
    title: Mapped[str | None] = mapped_column(utf8mb4_longtext(), nullable=True)
    author: Mapped[str | None] = mapped_column(utf8mb4_longtext(), nullable=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publisher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at_utc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_text: Mapped[str] = mapped_column(utf8mb4_longtext(), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Checkpoint(Base):
    """运行检查点（断点）数据库模型实体。

    用途:
        保存步骤节点完成后的工作流快照状态以及关联的生成物，便于任务在此检查点处进行恢复/继续执行。

    用法:
        任务在每个步骤成功后持久化 Checkpoint 记录，在系统重启或失败恢复时，重构变量池状态。

    @Author: mosliu
    """
    __tablename__ = "checkpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("cp"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str | None] = mapped_column(ForeignKey("step_runs.id"), nullable=True)
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checkpoint_type: Mapped[str] = mapped_column(String(64), nullable=False, default="artifact_boundary")
    state_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    artifact_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task_run: Mapped[TaskRun] = relationship(back_populates="checkpoints")
    step_run: Mapped[StepRun | None] = relationship(back_populates="checkpoints")
