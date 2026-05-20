from sqlalchemy.orm import Session

from llm_scheduling_management_system.config_loader import load_llm_config, load_mcp_config, load_search_config, load_source_registry_config
from llm_scheduling_management_system.repositories.task_repository import TaskRepository
from llm_scheduling_management_system.schemas.tasks import CreateDerivedTaskRequest, CreateTaskRequest, ResumeFromRequest
from llm_scheduling_management_system.services.langgraph_runner import LangGraphTaskRunner
from llm_scheduling_management_system.services.task_runner import TaskAlreadyCompletedError, TaskRunner


class TaskTemplateNotFoundError(Exception):
    pass


class ResumeCheckpointNotFoundError(Exception):
    pass


class ResumeArtifactNotFoundError(Exception):
    pass


class ForkTaskNotFoundError(Exception):
    pass


class ForkStartNodeNotFoundError(Exception):
    pass


class TaskNotCancellableError(Exception):
    pass


class StepHasNoArtifactsError(Exception):
    pass


class TaskService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = TaskRepository(session)
        self.runner = TaskRunner(self.repository)
        self.langgraph_runner = LangGraphTaskRunner(self.runner)

    def ensure_bootstrap_state(self) -> None:
        self.repository.ensure_default_templates()

    def create_task(self, request: CreateTaskRequest):
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
        self.ensure_bootstrap_state()
        return self.repository.list_tasks(
            status=status,
            template_id=template_id,
            tenant_id=tenant_id,
            limit=limit,
        )

    def list_templates(self):
        self.ensure_bootstrap_state()
        return self.repository.list_templates()

    def get_template_with_blueprint(self, template_id: str):
        self.ensure_bootstrap_state()
        template = self.repository.get_template(template_id)
        if template is None:
            return None, []
        return template, self.repository.get_template_blueprint(template_id)

    def get_system_status(self):
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
        self.ensure_bootstrap_state()
        return self.repository.get_step(step_run_id)

    def get_artifact(self, artifact_id: str):
        self.ensure_bootstrap_state()
        return self.repository.get_artifact(artifact_id)

    def get_checkpoint(self, checkpoint_id: str):
        self.ensure_bootstrap_state()
        return self.repository.get_checkpoint(checkpoint_id)

    def list_artifact_lineage(self, artifact_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_artifact_lineage(artifact_id)

    def list_step_search_invocations(self, step_run_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_step_search_invocations(step_run_id)

    def list_step_fetch_invocations(self, step_run_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_step_fetch_invocations(step_run_id)

    def list_step_tool_invocations(self, step_run_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_step_tool_invocations(step_run_id)

    def list_step_llm_invocations(self, step_run_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_step_llm_invocations(step_run_id)

    def list_task_search_invocations(self, task_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_task_search_invocations(task_id)

    def list_task_fetch_invocations(self, task_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_task_fetch_invocations(task_id)

    def list_task_tool_invocations(self, task_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_task_tool_invocations(task_id)

    def list_task_llm_invocations(self, task_id: str):
        self.ensure_bootstrap_state()
        return self.repository.list_task_llm_invocations(task_id)

    def list_task_events(self, task_id: str):
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
        self.ensure_bootstrap_state()
        task = self.repository.get_task(task_id)
        if task is None:
            return None
        if task.options_payload.get("execution_engine") == "langgraph":
            return self.langgraph_runner.run_task(task)
        return self.runner.run_task(task)

    def run_next_step(self, task_id: str):
        self.ensure_bootstrap_state()
        task = self.repository.get_task(task_id)
        if task is None:
            return None
        return self.runner.run_next_step(task)

    def cancel_task(self, task_id: str):
        self.ensure_bootstrap_state()
        task = self.repository.get_task(task_id)
        if task is None:
            return None
        if task.status not in {"queued", "running", "waiting_retry"}:
            raise TaskNotCancellableError(task.status)
        return self.repository.cancel_task(task)

    def create_task_from_step(self, step_run_id: str, request: CreateDerivedTaskRequest):
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
