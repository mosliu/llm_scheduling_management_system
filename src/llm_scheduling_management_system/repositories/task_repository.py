import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from llm_scheduling_management_system.domain.enums import ArtifactLevel, StepStatus, TaskStatus
from llm_scheduling_management_system.domain.models import (
    Artifact,
    ArtifactLineage,
    Checkpoint,
    DocumentRecord,
    FetchInvocation,
    LLMInvocation,
    SearchHitRecord,
    SearchInvocation,
    StepRun,
    TaskEvent,
    TaskRun,
    ToolInvocation,
    WorkflowTemplate,
    utcnow,
)


DEFAULT_TEMPLATE_FIXTURES = (
    {
        "id": "event_summary_v1",
        "name": "Event Summary",
        "category": "summary",
        "description": "Summarize retrieved evidence into an event summary report.",
    },
    {
        "id": "public_opinion_analysis_v1",
        "name": "Public Opinion Analysis",
        "category": "analysis",
        "description": "Analyze public opinion based on multi-source retrieval evidence.",
    },
    {
        "id": "public_opinion_timeline_v1",
        "name": "Public Opinion Timeline",
        "category": "timeline",
        "description": "Build public opinion timelines from retrieved evidence.",
    },
    {
        "id": "public_opinion_report_v1",
        "name": "Public Opinion Report",
        "category": "report",
        "description": "Produce an end-to-end public opinion report with official responses, media views, public views, and implications.",
    },
)

DEFAULT_TEMPLATE_STEP_BLUEPRINTS = {
    "event_summary_v1": [
        {
            "node_key": "search_fanout",
            "node_type": "search",
            "title": "Search Fanout",
        },
        {
            "node_key": "fetch_documents",
            "node_type": "fetch",
            "title": "Fetch Documents",
        },
        {
            "node_key": "merge_search_results",
            "node_type": "transform",
            "title": "Merge Search Results",
        },
        {
            "node_key": "normalize_and_filter",
            "node_type": "transform",
            "title": "Normalize and Filter",
        },
        {
            "node_key": "generate_event_summary",
            "node_type": "llm_call",
            "title": "Generate Event Summary",
        },
    ],
    "public_opinion_analysis_v1": [
        {
            "node_key": "search_fanout",
            "node_type": "search",
            "title": "Search Fanout",
        },
        {
            "node_key": "fetch_documents",
            "node_type": "fetch",
            "title": "Fetch Documents",
        },
        {
            "node_key": "mcp_lookup_context",
            "node_type": "tool",
            "title": "MCP Lookup Context",
        },
        {
            "node_key": "merge_search_results",
            "node_type": "transform",
            "title": "Merge Search Results",
        },
        {
            "node_key": "classify_and_filter_sources",
            "node_type": "classification",
            "title": "Classify and Filter Sources",
        },
        {
            "node_key": "analyze_public_opinion",
            "node_type": "llm_call",
            "title": "Analyze Public Opinion",
        },
    ],
    "public_opinion_timeline_v1": [
        {
            "node_key": "search_fanout",
            "node_type": "search",
            "title": "Search Fanout",
        },
        {
            "node_key": "fetch_documents",
            "node_type": "fetch",
            "title": "Fetch Documents",
        },
        {
            "node_key": "extract_event_time",
            "node_type": "extract",
            "title": "Extract Event Time",
        },
        {
            "node_key": "build_timeline",
            "node_type": "transform",
            "title": "Build Timeline",
        },
        {
            "node_key": "generate_timeline_report",
            "node_type": "llm_call",
            "title": "Generate Timeline Report",
        },
    ],
    "public_opinion_report_v1": [
        {
            "node_key": "search_fanout",
            "node_type": "search",
            "title": "Search Fanout",
        },
        {
            "node_key": "fetch_documents",
            "node_type": "fetch",
            "title": "Fetch Documents",
        },
        {
            "node_key": "merge_search_results",
            "node_type": "transform",
            "title": "Merge Search Results",
        },
        {
            "node_key": "extract_event_time",
            "node_type": "extract",
            "title": "Extract Event Time",
        },
        {
            "node_key": "build_timeline",
            "node_type": "transform",
            "title": "Build Timeline",
        },
        {
            "node_key": "extract_official_responses",
            "node_type": "analysis",
            "title": "Extract Official Responses",
        },
        {
            "node_key": "segment_public_opinion",
            "node_type": "analysis",
            "title": "Segment Media and Public Opinion",
        },
        {
            "node_key": "generate_public_opinion_report",
            "node_type": "llm_call",
            "title": "Generate Public Opinion Report",
        },
    ],
}


class TaskRepository:
    """任务仓库类。

    用途:
        提供针对任务（TaskRun）、步骤（StepRun）、制品（Artifact）以及相关调用痕迹（LLM/Search/Fetch 等）的统一持久化与查询接口。

    用法:
        repo = TaskRepository(session)

    @Author: mosliu
    """
    def __init__(self, session: Session) -> None:
        """初始化任务仓库。

        用途:
            存储 SQLAlchemy Session 实例用于数据库交互。

        用法:
            repo = TaskRepository(session)

        @Author: mosliu
        """
        self.session = session

    @staticmethod
    def _compute_artifact_hash(content_json: dict, content_text: str | None) -> str:
        """计算制品的哈希值。

        用途:
            根据制品的 JSON 内容 and 文本内容，通过 SHA256 计算出一个唯一的哈希字符串，用于校验完整性和做缓存键校验。

        用法:
            hash_val = TaskRepository._compute_artifact_hash(content_json, content_text)

        @Author: mosliu
        """
        payload = {
            "content_json": content_json,
            "content_text": content_text,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def ensure_default_templates(self) -> None:
        """确保系统默认的工作流模板存在。

        用途:
            在数据库中自动初始化并补全系统默认的四种工作流模板（Event Summary, Public Opinion Analysis, Timeline, Report）。

        用法:
            repo.ensure_default_templates()

        @Author: mosliu
        """
        existing_ids = {
            template_id
            for template_id in self.session.scalars(select(WorkflowTemplate.id))
        }
        changed = False
        for fixture in DEFAULT_TEMPLATE_FIXTURES:
            if fixture["id"] in existing_ids:
                continue
            self.session.add(
                WorkflowTemplate(
                    id=fixture["id"],
                    name=fixture["name"],
                    category=fixture["category"],
                    description=fixture["description"],
                    latest_version="v1",
                )
            )
            changed = True

        if changed:
            self.session.commit()

    def get_template(self, template_id: str) -> WorkflowTemplate | None:
        """获取工作流模板。

        用途:
            根据模板 ID 从数据库检索 WorkflowTemplate 实体。

        用法:
            template = repo.get_template("event_summary_v1")

        @Author: mosliu
        """
        return self.session.get(WorkflowTemplate, template_id)

    def get_template_blueprint(self, template_id: str) -> list[dict]:
        """获取模板的步骤蓝图。

        用途:
            获取指定工作流模板对应的静态步骤蓝图定义列表。

        用法:
            blueprint = repo.get_template_blueprint("event_summary_v1")

        @Author: mosliu
        """
        return list(DEFAULT_TEMPLATE_STEP_BLUEPRINTS.get(template_id, []))

    def list_templates(self) -> list[WorkflowTemplate]:
        """列出所有模板。

        用途:
            检索数据库中所有的 WorkflowTemplate 并按 ID 排序返回。

        用法:
            templates = repo.list_templates()

        @Author: mosliu
        """
        return list(self.session.scalars(select(WorkflowTemplate).order_by(WorkflowTemplate.id)))

    def get_task_status_counts(self) -> dict[str, int]:
        """获取不同状态的任务统计数。

        用途:
            统计当前数据库中所有 TaskRun 记录按 status 分组的数量并返回字典。

        用法:
            counts = repo.get_task_status_counts()

        @Author: mosliu
        """
        rows = self.session.execute(select(TaskRun.status))
        counts: dict[str, int] = {}
        for (status,) in rows:
            counts[status] = counts.get(status, 0) + 1
        return counts

    def list_tasks(
        self,
        *,
        status: str | None = None,
        template_id: str | None = None,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> list[TaskRun]:
        """过滤和列出任务运行记录。

        用途:
            根据状态、模板 ID 和租户 ID 过滤 TaskRun 记录，按创建时间倒序返回列表。

        用法:
            tasks = repo.list_tasks(status="running", limit=10)

        @Author: mosliu
        """
        statement = select(TaskRun)
        if status:
            statement = statement.where(TaskRun.status == status)
        if template_id:
            statement = statement.where(TaskRun.template_id == template_id)
        if tenant_id:
            statement = statement.where(TaskRun.tenant_id == tenant_id)
        statement = statement.order_by(TaskRun.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement))

    def get_task_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        template_id: str,
        idempotency_key: str,
    ) -> TaskRun | None:
        """根据幂等键查找任务运行记录。

        用途:
            针对特定租户和模板，根据传入的幂等键查找已有的 TaskRun，以实现防重复提交逻辑。

        用法:
            task = repo.get_task_by_idempotency_key(tenant_id="t1", template_id="temp1", idempotency_key="key123")

        @Author: mosliu
        """
        statement = select(TaskRun).where(
            TaskRun.tenant_id == tenant_id,
            TaskRun.template_id == template_id,
            TaskRun.idempotency_key == idempotency_key,
        )
        return self.session.scalar(statement)

    def list_runnable_tasks(self, limit: int = 10) -> list[TaskRun]:
        """列出可执行的任务。

        用途:
            获取状态处于 QUEUED、RUNNING 或 WAITING_RETRY 的 TaskRun 列表，按创建时间排序，供后台 Worker 调度执行。

        用法:
            tasks = repo.list_runnable_tasks(limit=10)

        @Author: mosliu
        """
        statement = (
            select(TaskRun)
            .where(TaskRun.status.in_([TaskStatus.QUEUED.value, TaskStatus.RUNNING.value, TaskStatus.WAITING_RETRY.value]))
            .order_by(TaskRun.created_at)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def find_cached_artifact(self, cache_key: str) -> Artifact | None:
        """查找缓存的可重用制品。

        用途:
            根据传入的步骤缓存键 (cache_key)，在数据库中检索最近生成的且被标记为可重用的 Artifact 记录。

        用法:
            artifact = repo.find_cached_artifact("cache_hash_string")

        @Author: mosliu
        """
        statement = (
            select(Artifact)
            .join(StepRun, Artifact.step_run_id == StepRun.id)
            .where(StepRun.cache_key == cache_key, Artifact.reusable_flag.is_(True))
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def create_task(
        self,
        *,
        tenant_id: str,
        template: WorkflowTemplate,
        input_payload: dict,
        options_payload: dict,
        idempotency_key: str | None,
        forked_from_task_run_id: str | None,
        resume_from_checkpoint_id: str | None,
        resume_from_artifact_id: str | None,
        resume_seed_artifact_ids: list[str] | None,
        start_from_node_key: str | None,
    ) -> TaskRun:
        """创建并初始化新任务。

        用途:
            根据模板、输入、配置和历史记录（如从某检查点/制品恢复或分叉），在数据库中创建并保存一个新的 TaskRun。
            自动初始化首个系统接入步骤 (request_intake)，插入对应的接入制品 (task_request)、线索血缘 (ArtifactLineage)、初始检查点 (Checkpoint) 和事件日志，
            并根据蓝图初始化后续步骤为 PENDING（待执行）或 SKIPPED（跳过）。

        用法:
            task = repo.create_task(
                tenant_id="t1",
                template=temp,
                input_payload={"query": "test"},
                options_payload={},
                idempotency_key="idemp_123",
                forked_from_task_run_id=None,
                resume_from_checkpoint_id=None,
                resume_from_artifact_id=None,
                resume_seed_artifact_ids=None,
                start_from_node_key=None
            )

        @Author: mosliu
        """
        source_artifact_ids: list[str] = []
        if resume_seed_artifact_ids:
            source_artifact_ids = list(resume_seed_artifact_ids)
        elif resume_from_artifact_id:
            source_artifact_ids = [resume_from_artifact_id]
        elif resume_from_checkpoint_id:
            checkpoint = self.get_checkpoint(resume_from_checkpoint_id)
            if checkpoint is not None:
                source_artifact_ids = list(checkpoint.artifact_refs)

        blueprints = list(DEFAULT_TEMPLATE_STEP_BLUEPRINTS.get(template.id, []))
        planned_blueprints = blueprints
        if start_from_node_key:
            start_index = next(
                (index for index, blueprint in enumerate(blueprints) if blueprint["node_key"] == start_from_node_key),
                0,
            )
            planned_blueprints = blueprints[start_index:]

        task = TaskRun(
            tenant_id=tenant_id,
            template_id=template.id,
            template_version=template.latest_version,
            status=TaskStatus.QUEUED.value,
            input_payload=input_payload,
            options_payload=options_payload,
            progress_percent=5.0,
            idempotency_key=idempotency_key,
            forked_from_task_run_id=forked_from_task_run_id,
            resume_from_checkpoint_id=resume_from_checkpoint_id,
            resume_from_artifact_id=resume_from_artifact_id,
            planned_step_count=1 + len(planned_blueprints),
            completed_step_count=1,
        )
        self.session.add(task)
        self.session.flush()

        intake_step = StepRun(
            task_run_id=task.id,
            node_key="request_intake",
            node_type="system",
            title="Request Intake",
            status=StepStatus.SUCCEEDED.value,
            progress_percent=100.0,
            sequence_no=1,
            input_snapshot=input_payload,
            output_summary={"accepted": True},
        )
        self.session.add(intake_step)
        self.session.flush()

        task.current_step_run_id = intake_step.id

        request_artifact = Artifact(
            tenant_id=tenant_id,
            task_run_id=task.id,
            step_run_id=intake_step.id,
            artifact_type="task_request",
            artifact_level=ArtifactLevel.RAW.value,
            schema_name="task_request",
            content_json={
                "template_id": template.id,
                "input": input_payload,
                "options": options_payload,
            },
        )
        self.session.add(request_artifact)
        self.session.flush()

        for source_artifact_id in source_artifact_ids:
            self.session.add(
                ArtifactLineage(
                    from_artifact_id=source_artifact_id,
                    to_artifact_id=request_artifact.id,
                    relation_type="forked_from",
                )
            )

        initial_checkpoint = Checkpoint(
            task_run_id=task.id,
            step_run_id=intake_step.id,
            node_key="request_intake",
            checkpoint_type="task_initialized",
            state_ref={"task_status": task.status, "source_artifact_ids": source_artifact_ids},
            artifact_refs=[request_artifact.id],
        )
        self.session.add(initial_checkpoint)
        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=intake_step.id,
                event_type="task_created",
                status=task.status,
                payload={
                    "template_id": template.id,
                    "planned_step_count": task.planned_step_count,
                },
            )
        )
        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=intake_step.id,
                event_type="step_succeeded",
                status=intake_step.status,
                payload={"node_key": intake_step.node_key},
            )
        )

        reached_start = start_from_node_key is None
        seeded_first_active_step = False
        for index, blueprint in enumerate(blueprints, start=2):
            is_skipped = False
            if not reached_start:
                if blueprint["node_key"] == start_from_node_key:
                    reached_start = True
                else:
                    is_skipped = True
            step_input_artifact_refs: list[str] = []
            if not is_skipped and not seeded_first_active_step and source_artifact_ids:
                step_input_artifact_refs = list(source_artifact_ids)
                seeded_first_active_step = True
            pending_step = StepRun(
                task_run_id=task.id,
                node_key=blueprint["node_key"],
                node_type=blueprint["node_type"],
                title=blueprint["title"],
                status=StepStatus.SKIPPED.value if is_skipped else StepStatus.PENDING.value,
                progress_percent=100.0 if is_skipped else 0.0,
                sequence_no=index,
                input_artifact_refs=step_input_artifact_refs,
                input_snapshot={},
                output_summary={"skipped": True} if is_skipped else {},
            )
            self.session.add(pending_step)

        self.session.commit()
        self.session.refresh(task)
        return task

    def get_task(self, task_id: str) -> TaskRun | None:
        """根据任务 ID 获取任务。

        用途:
            从数据库中加载并返回指定 ID 的 TaskRun 对象。

        用法:
            task = repo.get_task("task_id_123")

        @Author: mosliu
        """
        return self.session.get(TaskRun, task_id)

    def get_step(self, step_run_id: str) -> StepRun | None:
        """根据步骤运行 ID 获取步骤记录。

        用途:
            从数据库中加载并返回指定 ID 的 StepRun 对象。

        用法:
            step = repo.get_step("step_id_123")

        @Author: mosliu
        """
        return self.session.get(StepRun, step_run_id)

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        """根据制品 ID 获取制品记录。

        用途:
            从数据库中加载并返回指定 ID 的 Artifact 实体。

        用法:
            artifact = repo.get_artifact("artifact_id_123")

        @Author: mosliu
        """
        return self.session.get(Artifact, artifact_id)

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """根据检查点 ID 获取检查点记录。

        用途:
            从数据库中加载并返回指定 ID 的 Checkpoint 实体。

        用法:
            checkpoint = repo.get_checkpoint("checkpoint_id_123")

        @Author: mosliu
        """
        return self.session.get(Checkpoint, checkpoint_id)

    def list_task_artifacts(self, task_id: str) -> list[Artifact]:
        """列出特定任务下的所有制品。

        用途:
            按创建时间升序排列，返回该任务产生的所有 Artifact 记录列表。

        用法:
            artifacts = repo.list_task_artifacts("task_id_123")

        @Author: mosliu
        """
        statement = select(Artifact).where(Artifact.task_run_id == task_id).order_by(Artifact.created_at)
        return list(self.session.scalars(statement))

    def list_artifact_lineage(self, artifact_id: str) -> list[ArtifactLineage]:
        """获取制品的血缘关系。

        用途:
            返回与指定制品 ID 相关（作为来源或目标）的所有 ArtifactLineage 记录列表。

        用法:
            lineages = repo.list_artifact_lineage("artifact_id_123")

        @Author: mosliu
        """
        statement = select(ArtifactLineage).where(
            (ArtifactLineage.from_artifact_id == artifact_id) | (ArtifactLineage.to_artifact_id == artifact_id)
        ).order_by(ArtifactLineage.created_at)
        return list(self.session.scalars(statement))

    def list_step_search_invocations(self, step_run_id: str) -> list[SearchInvocation]:
        """列出特定步骤的搜索服务调用记录。

        用途:
            按创建时间升序排列，查询并返回指定步骤在执行过程中产生的 SearchInvocation 记录。

        用法:
            invocations = repo.list_step_search_invocations("step_id_123")

        @Author: mosliu
        """
        statement = select(SearchInvocation).where(SearchInvocation.step_run_id == step_run_id).order_by(SearchInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_step_fetch_invocations(self, step_run_id: str) -> list[FetchInvocation]:
        """列出特定步骤的网页抓取服务调用记录。

        用途:
            按创建时间升序排列，获取指定步骤运行过程中产生的 FetchInvocation 记录。

        用法:
            invocations = repo.list_step_fetch_invocations("step_id_123")

        @Author: mosliu
        """
        statement = select(FetchInvocation).where(FetchInvocation.step_run_id == step_run_id).order_by(FetchInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_step_llm_invocations(self, step_run_id: str) -> list[LLMInvocation]:
        """列出特定步骤的大语言模型服务调用记录。

        用途:
            按创建时间升序排列，检索指定步骤执行期间产生的所有 LLMInvocation 记录。

        用法:
            invocations = repo.list_step_llm_invocations("step_id_123")

        @Author: mosliu
        """
        statement = select(LLMInvocation).where(LLMInvocation.step_run_id == step_run_id).order_by(LLMInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_step_tool_invocations(self, step_run_id: str) -> list[ToolInvocation]:
        """列出特定步骤的 MCP 工具调用记录。

        用途:
            按创建时间升序排列，检索指定步骤内产生的所有 ToolInvocation 记录。

        用法:
            invocations = repo.list_step_tool_invocations("step_id_123")

        @Author: mosliu
        """
        statement = select(ToolInvocation).where(ToolInvocation.step_run_id == step_run_id).order_by(ToolInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_search_invocations(self, task_id: str) -> list[SearchInvocation]:
        """列出特定任务下的所有搜索服务调用记录。

        用途:
            获取该任务运行周期内产生的全部 SearchInvocation 记录，按时间升序返回。

        用法:
            invocations = repo.list_task_search_invocations("task_id_123")

        @Author: mosliu
        """
        statement = select(SearchInvocation).where(SearchInvocation.task_run_id == task_id).order_by(SearchInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_fetch_invocations(self, task_id: str) -> list[FetchInvocation]:
        """列出特定任务下的所有网页抓取服务调用记录。

        用途:
            获取该任务运行周期内产生的全部 FetchInvocation 记录，按时间升序返回。

        用法:
            invocations = repo.list_task_fetch_invocations("task_id_123")

        @Author: mosliu
        """
        statement = select(FetchInvocation).where(FetchInvocation.task_run_id == task_id).order_by(FetchInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_llm_invocations(self, task_id: str) -> list[LLMInvocation]:
        """列出特定任务下的所有大语言模型服务调用记录。

        用途:
            获取该任务运行周期内产生的全部 LLMInvocation 记录，按时间升序返回。

        用法:
            invocations = repo.list_task_llm_invocations("task_id_123")

        @Author: mosliu
        """
        statement = select(LLMInvocation).where(LLMInvocation.task_run_id == task_id).order_by(LLMInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_tool_invocations(self, task_id: str) -> list[ToolInvocation]:
        """列出特定任务下的所有工具调用记录。

        用途:
            获取该任务运行周期内产生的全部 ToolInvocation 记录，按时间升序返回。

        用法:
            invocations = repo.list_task_tool_invocations("task_id_123")

        @Author: mosliu
        """
        statement = select(ToolInvocation).where(ToolInvocation.task_run_id == task_id).order_by(ToolInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_events(self, task_id: str) -> list[TaskEvent]:
        """列出任务关联的所有状态变更及行为事件。

        用途:
            返回该任务产生的所有事件记录（TaskEvent），以便于进行可视化追踪和审计。

        用法:
            events = repo.list_task_events("task_id_123")

        @Author: mosliu
        """
        statement = select(TaskEvent).where(TaskEvent.task_run_id == task_id).order_by(TaskEvent.created_at)
        return list(self.session.scalars(statement))

    def list_task_documents(
        self,
        task_id: str,
        *,
        provider_name: str | None = None,
        source_domain: str | None = None,
        source_type: str | None = None,
        region_hint: str | None = None,
        published_after: str | None = None,
        published_before: str | None = None,
    ) -> list[DocumentRecord]:
        """列出任务范围内抓取的网页文档。

        用途:
            支持按服务商名称、域名、源类型、地区、发布时间段进行灵活过滤，返回符合条件的 DocumentRecord 列表。

        用法:
            docs = repo.list_task_documents("task_123", provider_name="exa", source_type="news")

        @Author: mosliu
        """
        statement = select(DocumentRecord).where(DocumentRecord.task_run_id == task_id)
        if provider_name:
            statement = statement.where(DocumentRecord.provider_name == provider_name)
        if source_domain:
            statement = statement.where(DocumentRecord.source_domain == source_domain)
        if source_type:
            statement = statement.where(DocumentRecord.source_type == source_type)
        if region_hint:
            statement = statement.where(DocumentRecord.region_hint == region_hint)
        if published_after:
            statement = statement.where(DocumentRecord.published_at_utc >= published_after)
        if published_before:
            statement = statement.where(DocumentRecord.published_at_utc <= published_before)
        statement = statement.order_by(DocumentRecord.created_at)
        return list(self.session.scalars(statement))

    def list_step_documents(
        self,
        step_run_id: str,
        *,
        provider_name: str | None = None,
        source_domain: str | None = None,
        source_type: str | None = None,
        region_hint: str | None = None,
        published_after: str | None = None,
        published_before: str | None = None,
    ) -> list[DocumentRecord]:
        """列出特定步骤范围内抓取的网页文档。

        用途:
            类似于 list_task_documents，但范围限制在单个步骤运行记录内，同样支持灵活的多字段过滤。

        用法:
            docs = repo.list_step_documents("step_123", source_domain="example.com")

        @Author: mosliu
        """
        statement = select(DocumentRecord).where(DocumentRecord.step_run_id == step_run_id)
        if provider_name:
            statement = statement.where(DocumentRecord.provider_name == provider_name)
        if source_domain:
            statement = statement.where(DocumentRecord.source_domain == source_domain)
        if source_type:
            statement = statement.where(DocumentRecord.source_type == source_type)
        if region_hint:
            statement = statement.where(DocumentRecord.region_hint == region_hint)
        if published_after:
            statement = statement.where(DocumentRecord.published_at_utc >= published_after)
        if published_before:
            statement = statement.where(DocumentRecord.published_at_utc <= published_before)
        statement = statement.order_by(DocumentRecord.created_at)
        return list(self.session.scalars(statement))

    def list_task_search_hits(
        self,
        task_id: str,
        *,
        provider_name: str | None = None,
        source_type: str | None = None,
        region_hint: str | None = None,
        published_after: str | None = None,
        published_before: str | None = None,
    ) -> list[SearchHitRecord]:
        """列出任务关联的全部搜索命中记录。

        用途:
            支持服务商名称、来源类型、区域暗示和发布时间等过滤条件，返回满足要求的 SearchHitRecord 列表。

        用法:
            hits = repo.list_task_search_hits("task_123", region_hint="cn")

        @Author: mosliu
        """
        statement = select(SearchHitRecord).where(SearchHitRecord.task_run_id == task_id)
        if provider_name:
            statement = statement.where(SearchHitRecord.provider_name == provider_name)
        if source_type:
            statement = statement.where(SearchHitRecord.source_type == source_type)
        if region_hint:
            statement = statement.where(SearchHitRecord.region_hint == region_hint)
        if published_after:
            statement = statement.where(SearchHitRecord.published_at_utc >= published_after)
        if published_before:
            statement = statement.where(SearchHitRecord.published_at_utc <= published_before)
        statement = statement.order_by(SearchHitRecord.created_at)
        return list(self.session.scalars(statement))

    def list_step_search_hits(
        self,
        step_run_id: str,
        *,
        provider_name: str | None = None,
        source_type: str | None = None,
        region_hint: str | None = None,
        published_after: str | None = None,
        published_before: str | None = None,
    ) -> list[SearchHitRecord]:
        """列出特定步骤关联的搜索命中记录。

        用途:
            类似于 list_task_search_hits，但仅过滤单个步骤产生的结果，支持多维度过滤。

        用法:
            hits = repo.list_step_search_hits("step_123", source_type="social")

        @Author: mosliu
        """
        statement = select(SearchHitRecord).where(SearchHitRecord.step_run_id == step_run_id)
        if provider_name:
            statement = statement.where(SearchHitRecord.provider_name == provider_name)
        if source_type:
            statement = statement.where(SearchHitRecord.source_type == source_type)
        if region_hint:
            statement = statement.where(SearchHitRecord.region_hint == region_hint)
        if published_after:
            statement = statement.where(SearchHitRecord.published_at_utc >= published_after)
        if published_before:
            statement = statement.where(SearchHitRecord.published_at_utc <= published_before)
        statement = statement.order_by(SearchHitRecord.created_at)
        return list(self.session.scalars(statement))

    def mark_task_running(self, task: TaskRun, *, current_step_run_id: str | None = None) -> TaskRun:
        """将任务状态标记为运行中。

        用途:
            更新任务的开始时间及状态为运行中，记录相关任务事件并刷新会话状态。

        用法:
            repo.mark_task_running(task, current_step_run_id="step_123")

        @Author: mosliu
        """
        if task.started_at is None:
            task.started_at = utcnow()
        task.status = TaskStatus.RUNNING.value
        if current_step_run_id is not None:
            task.current_step_run_id = current_step_run_id
        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=current_step_run_id,
                event_type="task_running",
                status=task.status,
                payload={"current_step_run_id": current_step_run_id},
            )
        )
        self.session.commit()
        self.session.refresh(task)
        return task

    def cancel_task(self, task: TaskRun) -> TaskRun:
        """取消当前正在运行或等待的任务。

        用途:
            将任务状态更改为已取消，更新结束时间并记录任务取消事件。

        用法:
            repo.cancel_task(task)

        @Author: mosliu
        """
        task.status = TaskStatus.CANCELLED.value
        task.ended_at = utcnow()
        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=task.current_step_run_id,
                event_type="task_cancelled",
                status=task.status,
                payload={"current_step_run_id": task.current_step_run_id},
            )
        )
        self.session.commit()
        self.session.refresh(task)
        return task

    def fail_step(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        error_code: str,
        error_message: str,
        max_attempts: int,
    ) -> TaskRun:
        """处理步骤失败的情况，并根据最大尝试次数决定是重试还是标记失败。

        用途:
            步骤执行出错时调用，记录错误码和错误信息，判断是否可重试，若可重试则更新步骤状态为 RETRYING 且任务状态为 WAITING_RETRY，否则标记步骤为 FAILED 且任务为 FAILED 或 PARTIAL_FAILED，写入对应事件。

        用法:
            repo.fail_step(task=task, step=step, error_code="ERR_500", error_message="Internal Error", max_attempts=3)

        @Author: mosliu
        """
        now = utcnow()
        step.started_at = step.started_at or now
        step.ended_at = utcnow()
        step.error_code = error_code
        step.error_message = error_message

        current_attempt = step.attempt_no
        retryable = current_attempt < max_attempts
        if retryable:
            step.status = StepStatus.RETRYING.value
            step.attempt_no = current_attempt + 1
            task.status = TaskStatus.WAITING_RETRY.value
            task.current_step_run_id = step.id
            task.ended_at = None
        else:
            step.status = StepStatus.FAILED.value
            task.status = TaskStatus.PARTIAL_FAILED.value if task.completed_step_count > 0 else TaskStatus.FAILED.value
            task.current_step_run_id = step.id
            task.ended_at = utcnow()

        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=step.id,
                event_type="step_failed",
                status=step.status,
                payload={
                    "node_key": step.node_key,
                    "error_code": error_code,
                    "error_message": error_message,
                    "retryable": retryable,
                    "attempt_no": step.attempt_no,
                },
            )
        )
        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=step.id,
                event_type="task_waiting_retry" if retryable else "task_failed",
                status=task.status,
                payload={
                    "node_key": step.node_key,
                    "retryable": retryable,
                    "attempt_no": step.attempt_no,
                },
            )
        )
        self.session.commit()
        self.session.refresh(task)
        return task

    def fail_step(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        error_code: str,
        error_message: str,
        max_attempts: int,
    ) -> TaskRun:
        """处理步骤失败的情况，并根据最大尝试次数决定是重试还是标记失败（重复定义以保持代码原样）。

        用途:
            步骤执行出错时调用，记录错误码和错误信息，判断是否可重试，若可重试则更新步骤状态为 RETRYING 且任务状态为 WAITING_RETRY，否则标记步骤为 FAILED 且任务为 FAILED 或 PARTIAL_FAILED，写入对应事件。

        用法:
            repo.fail_step(task=task, step=step, error_code="ERR_500", error_message="Internal Error", max_attempts=3)

        @Author: mosliu
        """
        now = utcnow()
        step.started_at = step.started_at or now
        step.ended_at = utcnow()
        step.error_code = error_code
        step.error_message = error_message

        current_attempt = step.attempt_no
        retryable = current_attempt < max_attempts
        if retryable:
            step.status = StepStatus.RETRYING.value
            step.attempt_no = current_attempt + 1
            task.status = TaskStatus.WAITING_RETRY.value
            task.current_step_run_id = step.id
            task.ended_at = None
        else:
            step.status = StepStatus.FAILED.value
            task.status = TaskStatus.PARTIAL_FAILED.value if task.completed_step_count > 0 else TaskStatus.FAILED.value
            task.current_step_run_id = step.id
            task.ended_at = utcnow()

        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=step.id,
                event_type="step_failed",
                status=step.status,
                payload={
                    "node_key": step.node_key,
                    "error_code": error_code,
                    "error_message": error_message,
                    "retryable": retryable,
                    "attempt_no": step.attempt_no,
                },
            )
        )
        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=step.id,
                event_type="task_waiting_retry" if retryable else "task_failed",
                status=task.status,
                payload={
                    "node_key": step.node_key,
                    "retryable": retryable,
                    "attempt_no": step.attempt_no,
                },
            )
        )
        self.session.commit()
        self.session.refresh(task)
        return task

    def complete_step_from_cache(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        cache_key: str,
        source_artifact: Artifact,
    ) -> TaskRun:
        """从缓存的 Artifact 快速完成当前步骤。

        用途:
            利用已有的 Artifact 缓存跳过步骤的实际计算。会复制该 Artifact，建立缓存谱系，更新步骤状态为 CACHED，并根据完成的步骤进度更新任务进度与状态。

        用法:
            repo.complete_step_from_cache(task=task, step=step, cache_key="key_abc", source_artifact=old_art)

        @Author: mosliu
        """
        now = utcnow()
        step.status = StepStatus.CACHED.value
        step.started_at = step.started_at or now
        step.ended_at = utcnow()
        step.progress_percent = 100.0
        step.cache_hit = True
        step.cache_key = cache_key
        step.input_artifact_refs = step.input_artifact_refs or []
        step.output_summary = {
            "artifact_type": source_artifact.artifact_type,
            "status": "cached",
            "source_artifact_id": source_artifact.id,
        }
        task.status = TaskStatus.RUNNING.value
        task.current_step_run_id = step.id

        artifact = Artifact(
            tenant_id=task.tenant_id,
            task_run_id=task.id,
            step_run_id=step.id,
            artifact_type=source_artifact.artifact_type,
            artifact_level=source_artifact.artifact_level,
            schema_name=source_artifact.schema_name,
            schema_version=source_artifact.schema_version,
            content_json=source_artifact.content_json,
            content_text=source_artifact.content_text,
            blob_uri=source_artifact.blob_uri,
            content_hash=source_artifact.content_hash or self._compute_artifact_hash(source_artifact.content_json, source_artifact.content_text),
            size_bytes=source_artifact.size_bytes,
            reusable_flag=source_artifact.reusable_flag,
            ttl_expire_at=source_artifact.ttl_expire_at,
        )
        self.session.add(artifact)
        self.session.flush()
        self.session.add(
            ArtifactLineage(
                from_artifact_id=source_artifact.id,
                to_artifact_id=artifact.id,
                relation_type="cached_from",
            )
        )

        completed_steps = sum(
            1 for item in task.step_runs if item.status in {StepStatus.SUCCEEDED.value, StepStatus.CACHED.value}
        )
        task.completed_step_count = completed_steps
        task.progress_percent = round((completed_steps / max(task.planned_step_count, 1)) * 100, 2)
        if completed_steps >= task.planned_step_count:
            task.status = TaskStatus.SUCCEEDED.value
            task.ended_at = utcnow()

        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=step.id,
                event_type="step_cached",
                status=step.status,
                payload={
                    "node_key": step.node_key,
                    "source_artifact_id": source_artifact.id,
                    "artifact_id": artifact.id,
                    "progress": task.progress_percent,
                },
            )
        )
        if task.status == TaskStatus.SUCCEEDED.value:
            self.session.add(
                TaskEvent(
                    task_run_id=task.id,
                    step_run_id=step.id,
                    event_type="task_succeeded",
                    status=task.status,
                    payload={"completed_step_count": task.completed_step_count},
                )
            )

        self.session.commit()
        self.session.refresh(task)
        return task

    def advance_step(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        artifact_type: str,
        artifact_level: str,
        schema_name: str,
        schema_version: str,
        content_json: dict,
        content_text: str | None = None,
        checkpoint_type: str = "step_completed",
        reusable_flag: bool = True,
        input_artifact_ids: list[str] | None = None,
        search_invocations: list | None = None,
        fetch_invocations: list | None = None,
        tool_invocations: list | None = None,
        llm_invocations: list | None = None,
        cache_key: str | None = None,
    ) -> TaskRun:
        """推进步骤的执行，创建输出 Artifact 及检查点，并记录相关服务的调用。

        用途:
            在步骤正常执行完成后调用。用于将步骤标记为运行并最终标记为成功，创建新的 Artifact 和 Checkpoint，建立输入输出依赖图（谱系），将各服务（搜索、网页抓取、MCP工具、LLM）的调用详情写入数据库，并更新任务进度和状态。

        用法:
            repo.advance_step(task=task, step=step, artifact_type="report", ...)

        @Author: mosliu
        """
        now = utcnow()
        input_artifact_ids = input_artifact_ids or []
        search_invocations = search_invocations or []
        fetch_invocations = fetch_invocations or []
        tool_invocations = tool_invocations or []
        llm_invocations = llm_invocations or []
        step.status = StepStatus.RUNNING.value
        step.started_at = step.started_at or now
        step.progress_percent = 25.0
        step.input_artifact_refs = input_artifact_ids
        step.cache_key = cache_key
        task.status = TaskStatus.RUNNING.value
        task.current_step_run_id = step.id
        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=step.id,
                event_type="step_started",
                status=step.status,
                payload={"node_key": step.node_key},
            )
        )
        self.session.flush()

        step.status = StepStatus.SUCCEEDED.value
        step.progress_percent = 100.0
        step.ended_at = utcnow()
        step.output_summary = {
            "artifact_type": artifact_type,
            "status": "completed",
        }

        artifact = Artifact(
            tenant_id=task.tenant_id,
            task_run_id=task.id,
            step_run_id=step.id,
            artifact_type=artifact_type,
            artifact_level=artifact_level,
            schema_name=schema_name,
            schema_version=schema_version,
            content_json=content_json,
            content_text=content_text,
            content_hash=self._compute_artifact_hash(content_json, content_text),
            reusable_flag=reusable_flag,
        )
        self.session.add(artifact)
        self.session.flush()

        for input_artifact_id in input_artifact_ids:
            self.session.add(
                ArtifactLineage(
                    from_artifact_id=input_artifact_id,
                    to_artifact_id=artifact.id,
                    relation_type="derived_from",
                )
            )

        for invocation in search_invocations:
            self.session.add(
                SearchInvocation(
                    task_run_id=task.id,
                    step_run_id=step.id,
                    provider_name=invocation.provider_name,
                    provider_vendor=invocation.provider_vendor,
                    query_text=invocation.query_text,
                    result_count=invocation.result_count,
                    request_metadata=invocation.request_metadata,
                    response_metadata=invocation.response_metadata,
                )
            )

        for invocation in fetch_invocations:
            self.session.add(
                FetchInvocation(
                    task_run_id=task.id,
                    step_run_id=step.id,
                    provider_name=invocation.provider_name,
                    provider_vendor=invocation.provider_vendor,
                    url=invocation.url,
                    title=invocation.title,
                    request_metadata=invocation.request_metadata,
                    response_metadata=invocation.response_metadata,
                )
            )

        for invocation in tool_invocations:
            self.session.add(
                ToolInvocation(
                    task_run_id=task.id,
                    step_run_id=step.id,
                    server_name=invocation.server_name,
                    tool_name=invocation.tool_name,
                    arguments_json=invocation.arguments_json,
                    response_json=invocation.response_json,
                    status=invocation.status,
                )
            )

        if artifact_type == "retrieval.search_hits":
            for hit in content_json.get("hits", []):
                self.session.add(
                    SearchHitRecord(
                        task_run_id=task.id,
                        step_run_id=step.id,
                        provider_name=hit.get("provider", "unknown"),
                        query_text=hit.get("query", ""),
                        title=hit.get("title", ""),
                        source_domain=hit.get("source_domain", ""),
                        source_type=hit.get("source_type", ""),
                        region_hint=hit.get("region_hint"),
                        publisher_type=hit.get("publisher_type"),
                        snippet=hit.get("snippet"),
                        published_at_utc=hit.get("published_at_utc"),
                        extra_metadata={
                            "node_key": step.node_key,
                            "source_url": hit.get("source_url"),
                            "author": hit.get("author"),
                            "publisher": hit.get("publisher"),
                            "language": hit.get("language"),
                            "matched_provider_names": hit.get("matched_provider_names", [hit.get("provider")]),
                            "matched_source_domains": hit.get("matched_source_domains", [hit.get("source_domain")]),
                            "duplicate_count": hit.get("duplicate_count", 1),
                        },
                    )
                )

        if artifact_type == "retrieval.fetched_documents":
            for document in content_json.get("documents", []):
                self.session.add(
                    DocumentRecord(
                        task_run_id=task.id,
                        step_run_id=step.id,
                        provider_name=document.get("provider", "unknown"),
                        url=document.get("url", ""),
                        canonical_url=document.get("canonical_url"),
                        title=document.get("title"),
                        author=document.get("author"),
                        language=document.get("language"),
                        source_domain=document.get("source_domain"),
                        source_type=document.get("source_type"),
                        region_hint=document.get("region_hint"),
                        publisher_type=document.get("publisher_type"),
                        published_at_utc=document.get("published_at_utc"),
                        content_text=document.get("content_text", ""),
                        content_hash=self._compute_artifact_hash({"url": document.get("url"), "title": document.get("title")}, document.get("content_text")),
                        extra_metadata=document.get("metadata", {}),
                    )
                )

        for invocation in llm_invocations:
            self.session.add(
                LLMInvocation(
                    task_run_id=task.id,
                    step_run_id=step.id,
                    provider_name=invocation.provider_name,
                    provider_type=invocation.provider_type,
                    profile_name=invocation.profile_name,
                    model_name=invocation.model_name,
                    prompt_text=invocation.prompt_text,
                    response_text=invocation.response_text,
                    request_metadata=invocation.request_metadata,
                    response_metadata=invocation.response_metadata,
                )
            )

        checkpoint = Checkpoint(
            task_run_id=task.id,
            step_run_id=step.id,
            node_key=step.node_key,
            checkpoint_type=checkpoint_type,
            state_ref={"step_status": step.status},
            artifact_refs=[artifact.id],
        )
        self.session.add(checkpoint)

        completed_steps = sum(
            1 for item in task.step_runs if item.status in {StepStatus.SUCCEEDED.value, StepStatus.CACHED.value}
        )
        task.completed_step_count = completed_steps
        task.progress_percent = round((completed_steps / max(task.planned_step_count, 1)) * 100, 2)

        if completed_steps >= task.planned_step_count:
            task.status = TaskStatus.SUCCEEDED.value
            task.ended_at = utcnow()
        else:
            task.status = TaskStatus.RUNNING.value

        self.session.add(
            TaskEvent(
                task_run_id=task.id,
                step_run_id=step.id,
                event_type="step_succeeded",
                status=step.status,
                payload={
                    "node_key": step.node_key,
                    "artifact_id": artifact.id,
                    "progress": task.progress_percent,
                },
            )
        )
        if task.status == TaskStatus.SUCCEEDED.value:
            self.session.add(
                TaskEvent(
                    task_run_id=task.id,
                    step_run_id=step.id,
                    event_type="task_succeeded",
                    status=task.status,
                    payload={"completed_step_count": task.completed_step_count},
                )
            )

        self.session.commit()
        self.session.refresh(task)
        return task
