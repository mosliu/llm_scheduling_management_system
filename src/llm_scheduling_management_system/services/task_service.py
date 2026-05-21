from sqlalchemy.orm import Session

from llm_scheduling_management_system.config_loader import load_llm_config, load_mcp_config, load_search_config, load_source_registry_config
from llm_scheduling_management_system.repositories.task_repository import TaskRepository
from llm_scheduling_management_system.schemas.tasks import CreateDerivedTaskRequest, CreateTaskRequest, ResumeFromRequest
from llm_scheduling_management_system.services.langgraph_runner import LangGraphTaskRunner
from llm_scheduling_management_system.services.task_runner import TaskAlreadyCompletedError, TaskRunner


class TaskTemplateNotFoundError(Exception):
    """任务模板未找到异常。

    用途:
        当请求指定的任务模板ID在数据库中不存在时抛出该异常。

    用法:
        raise TaskTemplateNotFoundError(template_id)

    @Author: mosliu
    """
    pass


class ResumeCheckpointNotFoundError(Exception):
    """恢复检查点未找到异常。

    用途:
        当请求从指定的检查点恢复任务，但该检查点ID在数据库中不存在时抛出该异常。

    用法:
        raise ResumeCheckpointNotFoundError(checkpoint_id)

    @Author: mosliu
    """
    pass


class ResumeArtifactNotFoundError(Exception):
    """恢复产物未找到异常。

    用途:
        当请求从指定的产物恢复任务，但该产物ID在数据库中不存在时抛出该异常。

    用法:
        raise ResumeArtifactNotFoundError(artifact_id)

    @Author: mosliu
    """
    pass


class ForkTaskNotFoundError(Exception):
    """分支任务未找到异常。

    用途:
        当请求从指定的任务进行分支（Fork）操作，但该源任务ID在数据库中不存在时抛出该异常。

    用法:
        raise ForkTaskNotFoundError(task_id)

    @Author: mosliu
    """
    pass


class ForkStartNodeNotFoundError(Exception):
    """分支启动节点未找到异常。

    用途:
        当请求从指定的节点启动分支，但该节点在源任务的执行步骤中不存在时抛出该异常。

    用法:
        raise ForkStartNodeNotFoundError(start_node_key)

    @Author: mosliu
    """
    pass


class TaskNotCancellableError(Exception):
    """任务不可取消异常。

    用途:
        当尝试取消一个已经处于非活跃状态（非 queued, running, waiting_retry 状态）的任务时抛出该异常。

    用法:
        raise TaskNotCancellableError(status)

    @Author: mosliu
    """
    pass


class StepHasNoArtifactsError(Exception):
    """步骤无产物异常。

    用途:
        当尝试从某个步骤运行实例派生任务，但该步骤没有产生任何产物，且未指定具体的 artifact_id 时抛出该异常。

    用法:
        raise StepHasNoArtifactsError(step_run_id)

    @Author: mosliu
    """
    pass


class TaskService:
    """任务管理与服务类。

    用途:
        负责管理任务的整个生命周期，包括任务和模板的增删改查、任务的运行与取消、执行状态汇总、调用记录的级联查询以及从步骤派生任务。

    用法:
        通过传入一个 SQLAlchemy 数据库会话(Session)实例化后，即可使用其提供的接口。

    @Author: mosliu
    """

    def __init__(self, session: Session) -> None:
        """初始化任务服务。

        用途:
            绑定数据库会话，并创建相关的底层 TaskRepository、TaskRunner 和 LangGraphTaskRunner 实例。

        用法:
            service = TaskService(session)

        @Author: mosliu
        """
        self.session = session
        self.repository = TaskRepository(session)
        self.runner = TaskRunner(self.repository)
        self.langgraph_runner = LangGraphTaskRunner(self.runner)

    def ensure_bootstrap_state(self) -> None:
        """确保基础引导状态。

        用途:
            在执行相关业务操作前，确保数据库中已加载并创建了默认的任务模板。

        用法:
            self.ensure_bootstrap_state()

        @Author: mosliu
        """
        self.repository.ensure_default_templates()

    def create_task(self, request: CreateTaskRequest):
        """创建新任务。

        用途:
            根据请求的模板 ID、输入参数、选项和幂等键，创建并持久化一个任务。支持从特定的检查点、产物恢复，或者从其他已完成任务的某个特定步骤节点进行分支（Fork）创建。

        用法:
            task = service.create_task(create_task_request)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        template = self.repository.get_template(request.template_id)
        if template is None:
            raise TaskTemplateNotFoundError(request.template_id)

        if request.idempotency_key:
            existing = self.repository.get_task_by_idempotency_key(
                tenant_id=request.tenant_id,
                template_id=request.template_id,
                idempotency_key=request.idempotency_key,
            )
            if existing is not None:
                return existing

        if request.resume_from and request.resume_from.checkpoint_id:
            checkpoint = self.repository.get_checkpoint(request.resume_from.checkpoint_id)
            if checkpoint is None:
                raise ResumeCheckpointNotFoundError(request.resume_from.checkpoint_id)
        else:
            checkpoint = None

        if request.resume_from and request.resume_from.artifact_id:
            artifact = self.repository.get_artifact(request.resume_from.artifact_id)
            if artifact is None:
                raise ResumeArtifactNotFoundError(request.resume_from.artifact_id)

        fork_seed_artifact_ids: list[str] = []
        start_from_node_key: str | None = None
        if request.fork_from:
            source_task = self.repository.get_task(request.fork_from.task_id)
            if source_task is None:
                raise ForkTaskNotFoundError(request.fork_from.task_id)
            source_node_keys = {step.node_key for step in source_task.step_runs}
            if request.fork_from.start_node_key not in source_node_keys:
                raise ForkStartNodeNotFoundError(request.fork_from.start_node_key)
            source_step = next(
                (step for step in source_task.step_runs if step.node_key == request.fork_from.start_node_key),
                None,
            )
            if source_step is not None:
                if source_step.input_artifact_refs:
                    fork_seed_artifact_ids = list(source_step.input_artifact_refs)
                else:
                    fork_seed_artifact_ids = [artifact.id for artifact in source_step.artifacts]
            start_from_node_key = request.fork_from.start_node_key
        elif checkpoint is not None:
            blueprint = self.repository.get_template_blueprint(request.template_id)
            checkpoint_index = next(
                (index for index, item in enumerate(blueprint) if item["node_key"] == checkpoint.node_key),
                None,
            )
            if checkpoint_index is not None and checkpoint_index + 1 < len(blueprint):
                start_from_node_key = blueprint[checkpoint_index + 1]["node_key"]

        forked_from_task_run_id = request.fork_from.task_id if request.fork_from else None
        resume_from_checkpoint_id = request.resume_from.checkpoint_id if request.resume_from else None
        resume_from_artifact_id = request.resume_from.artifact_id if request.resume_from else None

        return self.repository.create_task(
            tenant_id=request.tenant_id,
            template=template,
            input_payload=request.input,
            options_payload=request.options,
            idempotency_key=request.idempotency_key,
            forked_from_task_run_id=forked_from_task_run_id,
            resume_from_checkpoint_id=resume_from_checkpoint_id,
            resume_from_artifact_id=resume_from_artifact_id,
            resume_seed_artifact_ids=fork_seed_artifact_ids,
            start_from_node_key=start_from_node_key,
        )

    def get_task(self, task_id: str):
        """查询指定任务。

        用途:
            根据任务 ID 获取数据库中的任务运行对象。

        用法:
            task = service.get_task(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.get_task(task_id)

    def list_tasks(
        self,
        *,
        status: str | None = None,
        template_id: str | None = None,
        tenant_id: str | None = None,
        limit: int = 50,
    ):
        """列出任务列表。

        用途:
            根据状态、模板 ID 和租户 ID 过滤任务，并支持限制返回的最大数量。

        用法:
            tasks = service.list_tasks(status="completed", limit=20)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_tasks(
            status=status,
            template_id=template_id,
            tenant_id=tenant_id,
            limit=limit,
        )

    def list_templates(self):
        """列出所有模板。

        用途:
            获取系统中所有已注册并初始化的任务模板。

        用法:
            templates = service.list_templates()

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_templates()

    def get_template_with_blueprint(self, template_id: str):
        """获取任务模板与对应的蓝图结构。

        用途:
            查询指定模板详情，并返回该模板定义的所有步骤节点及依赖关系（蓝图）。

        用法:
            template, blueprint = service.get_template_with_blueprint(template_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        template = self.repository.get_template(template_id)
        if template is None:
            return None, []
        return template, self.repository.get_template_blueprint(template_id)

    def get_system_status(self):
        """获取系统状态概要。

        用途:
            获取系统的健康与配置状况，汇总各个 Provider (LLM, MCP, Search, Fetch 等) 的数量，以及系统当前的任务状态分布数据。

        用法:
            status = service.get_system_status()

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        search_config = load_search_config()
        llm_config = load_llm_config()
        mcp_config = load_mcp_config()
        source_registry = load_source_registry_config()
        templates = self.repository.list_templates()
        task_status_counts = self.repository.get_task_status_counts()
        provider_counts = {
            "search": len(search_config.providers),
            "fetch": len(search_config.fetch_providers),
            "crawl": len(search_config.crawl_providers),
            "embedded_search": len(search_config.embedded_search_providers),
            "mcp_servers": len(mcp_config.servers),
            "llm_providers": len(llm_config.providers),
            "llm_profiles": len(llm_config.profiles),
            "source_registry_entries": len(source_registry.sources),
        }
        return {
            "template_count": len(templates),
            "provider_counts": provider_counts,
            "task_status_counts": task_status_counts,
            "total_tasks": sum(task_status_counts.values()),
        }

    def get_step(self, step_run_id: str):
        """获取步骤运行详情。

        用途:
            根据步骤运行 ID 获取详细的步骤执行记录。

        用法:
            step = service.get_step(step_run_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.get_step(step_run_id)

    def get_artifact(self, artifact_id: str):
        """获取产物详情。

        用途:
            根据产物 ID 获取生成的产物记录。

        用法:
            artifact = service.get_artifact(artifact_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.get_artifact(artifact_id)

    def get_checkpoint(self, checkpoint_id: str):
        """获取检查点详情。

        用途:
            根据检查点 ID 获取对应的任务状态检查点记录。

        用法:
            checkpoint = service.get_checkpoint(checkpoint_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.get_checkpoint(checkpoint_id)

    def list_artifact_lineage(self, artifact_id: str):
        """列出产物血缘关系。

        用途:
            获取指定产物的级联父级产物链，用于溯源该产物是如何被生成出来的。

        用法:
            lineage = service.list_artifact_lineage(artifact_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_artifact_lineage(artifact_id)

    def list_step_search_invocations(self, step_run_id: str):
        """列出步骤的搜索接口调用记录。

        用途:
            获取指定步骤运行期间调用的所有搜索引擎 API 记录。

        用法:
            invocations = service.list_step_search_invocations(step_run_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_step_search_invocations(step_run_id)

    def list_step_fetch_invocations(self, step_run_id: str):
        """列出步骤的网页抓取接口调用记录。

        用途:
            获取指定步骤运行期间调用的所有网页抓取 API 记录。

        用法:
            invocations = service.list_step_fetch_invocations(step_run_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_step_fetch_invocations(step_run_id)

    def list_step_tool_invocations(self, step_run_id: str):
        """列出步骤的 MCP 工具调用记录。

        用途:
            获取指定步骤运行期间调用的所有 MCP 工具调用记录。

        用法:
            invocations = service.list_step_tool_invocations(step_run_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_step_tool_invocations(step_run_id)

    def list_step_llm_invocations(self, step_run_id: str):
        """列出步骤的 LLM 接口调用记录。

        用途:
            获取指定步骤运行期间调用的所有大语言模型 API 记录。

        用法:
            invocations = service.list_step_llm_invocations(step_run_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_step_llm_invocations(step_run_id)

    def list_task_search_invocations(self, task_id: str):
        """列出任务的搜索接口调用记录。

        用途:
            获取指定任务生命周期内所有步骤中调用的所有搜索引擎 API 记录。

        用法:
            invocations = service.list_task_search_invocations(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_task_search_invocations(task_id)

    def list_task_fetch_invocations(self, task_id: str):
        """列出任务的网页抓取接口调用记录。

        用途:
            获取指定任务生命周期内所有步骤中调用的所有网页抓取 API 记录。

        用法:
            invocations = service.list_task_fetch_invocations(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_task_fetch_invocations(task_id)

    def list_task_tool_invocations(self, task_id: str):
        """列出任务的 MCP 工具调用记录。

        用途:
            获取指定任务生命周期内所有步骤中调用的所有 MCP 工具调用记录。

        用法:
            invocations = service.list_task_tool_invocations(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_task_tool_invocations(task_id)

    def list_task_llm_invocations(self, task_id: str):
        """列出任务的 LLM 接口调用记录。

        用途:
            获取指定任务生命周期内所有步骤中调用的所有大语言模型 API 记录。

        用法:
            invocations = service.list_task_llm_invocations(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_task_llm_invocations(task_id)

    def list_task_events(self, task_id: str):
        """获取任务事件记录。

        用途:
            查询指定任务在其生命周期内产生的全部事件（例如启动、失败、完成、重试等日志）。

        用法:
            events = service.list_task_events(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_task_events(task_id)

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
    ):
        """列出任务相关文档。

        用途:
            获取指定任务在各步骤中所涉及或抓取到的文档列表，支持按服务商、来源域名、来源类型、区域、发布时间等多条件进行过滤。

        用法:
            docs = service.list_task_documents(task_id, source_type="news")

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_task_documents(
            task_id,
            provider_name=provider_name,
            source_domain=source_domain,
            source_type=source_type,
            region_hint=region_hint,
            published_after=published_after,
            published_before=published_before,
        )

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
    ):
        """列出步骤相关文档。

        用途:
            获取指定步骤运行中所涉及或抓取到的文档列表，支持按服务商、来源域名、来源类型、区域、发布时间等多条件进行过滤。

        用法:
            docs = service.list_step_documents(step_run_id, provider_name="jina")

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_step_documents(
            step_run_id,
            provider_name=provider_name,
            source_domain=source_domain,
            source_type=source_type,
            region_hint=region_hint,
            published_after=published_after,
            published_before=published_before,
        )

    def list_task_search_hits(
        self,
        task_id: str,
        *,
        provider_name: str | None = None,
        source_type: str | None = None,
        region_hint: str | None = None,
        published_after: str | None = None,
        published_before: str | None = None,
    ):
        """列出任务级别的搜索结果命中项。

        用途:
            获取指定任务所有搜索引擎调用中检索出来的命中内容（search hits），支持服务商、类型、区域、时间过滤。

        用法:
            hits = service.list_task_search_hits(task_id, region_hint="CN")

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_task_search_hits(
            task_id,
            provider_name=provider_name,
            source_type=source_type,
            region_hint=region_hint,
            published_after=published_after,
            published_before=published_before,
        )

    def list_step_search_hits(
        self,
        step_run_id: str,
        *,
        provider_name: str | None = None,
        source_type: str | None = None,
        region_hint: str | None = None,
        published_after: str | None = None,
        published_before: str | None = None,
    ):
        """列出步骤级别的搜索结果命中项。

        用途:
            获取指定步骤中搜索引擎调用所检索出来的命中内容，支持各种字段过滤。

        用法:
            hits = service.list_step_search_hits(step_run_id, provider_name="google")

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        return self.repository.list_step_search_hits(
            step_run_id,
            provider_name=provider_name,
            source_type=source_type,
            region_hint=region_hint,
            published_after=published_after,
            published_before=published_before,
        )

    def get_final_report(self, task_id: str) -> dict | None:
        """获取任务的最终总结报告。

        用途:
            收集任务产生的各类关键产物（如时间线、官方响应、媒体观点等数据），提取并组装最后的 LLM 生成报告内容，返回结构化的总结数据。

        用法:
            report = service.get_final_report(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        task = self.repository.get_task(task_id)
        if task is None:
            return None

        artifacts = self.repository.list_task_artifacts(task_id)
        artifact_by_schema: dict[str, object] = {}
        for artifact in artifacts:
            artifact_by_schema[artifact.schema_name] = artifact

        timeline_artifact = artifact_by_schema.get("timeline_bundle")
        official_artifact = artifact_by_schema.get("official_response_bundle")
        opinion_artifact = artifact_by_schema.get("public_opinion_segments")
        timeline = timeline_artifact.content_json.get("timeline", []) if timeline_artifact else []
        official_responses = official_artifact.content_json.get("official_responses", []) if official_artifact else []
        media_viewpoints = opinion_artifact.content_json.get("media_viewpoints", []) if opinion_artifact else []
        public_viewpoints = opinion_artifact.content_json.get("public_viewpoints", []) if opinion_artifact else []
        summary_fields = {
            "timeline_count": len(timeline),
            "official_response_count": len(official_responses),
            "media_viewpoint_count": len(media_viewpoints),
            "public_viewpoint_count": len(public_viewpoints),
            "timeline": timeline,
            "official_responses": official_responses,
            "media_viewpoints": media_viewpoints,
            "public_viewpoints": public_viewpoints,
        }

        report_artifacts = [artifact for artifact in artifacts if artifact.artifact_type == "report.generated"]
        if not report_artifacts:
            return {
                "task_id": task.id,
                "task_status": task.status,
                "ready": False,
                "report_state": "not_generated",
                "message": "Final report has not been generated yet.",
                **summary_fields,
            }

        report_artifact = max(report_artifacts, key=lambda item: item.created_at)
        report_text = (report_artifact.content_text or report_artifact.content_json.get("message") or "").strip()
        matching_invocation = None
        if report_artifact.step_run_id:
            step_invocations = self.repository.list_step_llm_invocations(report_artifact.step_run_id)
            if step_invocations:
                matching_invocation = step_invocations[-1]

        if not report_text:
            return {
                "task_id": task.id,
                "task_status": task.status,
                "ready": False,
                "report_state": "empty",
                "artifact_id": report_artifact.id,
                "step_run_id": report_artifact.step_run_id,
                "generated_at": report_artifact.created_at,
                "llm_profile_name": matching_invocation.profile_name if matching_invocation else None,
                "llm_model_name": matching_invocation.model_name if matching_invocation else None,
                "llm_invocation_id": matching_invocation.id if matching_invocation else None,
                "message": "Final report artifact exists but report text is empty.",
                **summary_fields,
            }

        return {
            "task_id": task.id,
            "task_status": task.status,
            "ready": True,
            "report_state": "ready",
            "artifact_id": report_artifact.id,
            "step_run_id": report_artifact.step_run_id,
            "report_text": report_text,
            "generated_at": report_artifact.created_at,
            "llm_profile_name": matching_invocation.profile_name if matching_invocation else None,
            "llm_model_name": matching_invocation.model_name if matching_invocation else None,
            "llm_invocation_id": matching_invocation.id if matching_invocation else None,
            "message": "ok",
            **summary_fields,
        }

    def run_task(self, task_id: str):
        """执行任务。

        用途:
            根据任务配置运行整个任务链。根据选项中指定的执行引擎（如 langgraph），分发给对应的 Runner 进行驱动。

        用法:
            result = service.run_task(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        task = self.repository.get_task(task_id)
        if task is None:
            return None
        if task.options_payload.get("execution_engine") == "langgraph":
            return self.langgraph_runner.run_task(task)
        return self.runner.run_task(task)

    def run_next_step(self, task_id: str):
        """执行任务的下一个步骤。

        用途:
            仅对任务执行一个等待中的步骤（单步模式），可供 Worker 单步推进任务使用。

        用法:
            step = service.run_next_step(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        task = self.repository.get_task(task_id)
        if task is None:
            return None
        return self.runner.run_next_step(task)

    def cancel_task(self, task_id: str):
        """取消任务。

        用途:
            将处于活跃状态（queued, running, waiting_retry 等）的任务标记为取消状态。

        用法:
            service.cancel_task(task_id)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        task = self.repository.get_task(task_id)
        if task is None:
            return None
        if task.status not in {"queued", "running", "waiting_retry"}:
            raise TaskNotCancellableError(task.status)
        return self.repository.cancel_task(task)

    def create_task_from_step(self, step_run_id: str, request: CreateDerivedTaskRequest):
        """从已有步骤派生并创建新任务。

        用途:
            基于某个已有任务中已完成步骤产生的输出（默认为该步骤最新的产物，或通过请求指定的产物），生成一个衍生子任务。

        用法:
            derived_task = service.create_task_from_step(step_run_id, request)

        @Author: mosliu
        """
        self.ensure_bootstrap_state()
        step = self.repository.get_step(step_run_id)
        if step is None:
            return None

        selected_artifact_id = request.artifact_id
        if selected_artifact_id is None:
            if not step.artifacts:
                raise StepHasNoArtifactsError(step_run_id)
            selected_artifact_id = step.artifacts[-1].id

        return self.create_task(
            CreateTaskRequest(
                template_id=request.template_id,
                input=request.input,
                options=request.options,
                idempotency_key=request.idempotency_key,
                tenant_id=request.tenant_id,
                resume_from=ResumeFromRequest(artifact_id=selected_artifact_id),
                fork_from=None,
            )
        )


__all__ = [
    "ForkStartNodeNotFoundError",
    "ForkTaskNotFoundError",
    "ResumeArtifactNotFoundError",
    "ResumeCheckpointNotFoundError",
    "TaskAlreadyCompletedError",
    "TaskNotCancellableError",
    "StepHasNoArtifactsError",
    "TaskService",
    "TaskTemplateNotFoundError",
]
