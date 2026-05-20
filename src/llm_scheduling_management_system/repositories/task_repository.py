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
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _compute_artifact_hash(content_json: dict, content_text: str | None) -> str:
        payload = {
            "content_json": content_json,
            "content_text": content_text,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def ensure_default_templates(self) -> None:
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
        return self.session.get(WorkflowTemplate, template_id)

    def get_template_blueprint(self, template_id: str) -> list[dict]:
        return list(DEFAULT_TEMPLATE_STEP_BLUEPRINTS.get(template_id, []))

    def list_templates(self) -> list[WorkflowTemplate]:
        return list(self.session.scalars(select(WorkflowTemplate).order_by(WorkflowTemplate.id)))

    def get_task_status_counts(self) -> dict[str, int]:
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
        statement = select(TaskRun).where(
            TaskRun.tenant_id == tenant_id,
            TaskRun.template_id == template_id,
            TaskRun.idempotency_key == idempotency_key,
        )
        return self.session.scalar(statement)

    def list_runnable_tasks(self, limit: int = 10) -> list[TaskRun]:
        statement = (
            select(TaskRun)
            .where(TaskRun.status.in_([TaskStatus.QUEUED.value, TaskStatus.RUNNING.value, TaskStatus.WAITING_RETRY.value]))
            .order_by(TaskRun.created_at)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def find_cached_artifact(self, cache_key: str) -> Artifact | None:
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
        return self.session.get(TaskRun, task_id)

    def get_step(self, step_run_id: str) -> StepRun | None:
        return self.session.get(StepRun, step_run_id)

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        return self.session.get(Artifact, artifact_id)

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        return self.session.get(Checkpoint, checkpoint_id)

    def list_task_artifacts(self, task_id: str) -> list[Artifact]:
        statement = select(Artifact).where(Artifact.task_run_id == task_id).order_by(Artifact.created_at)
        return list(self.session.scalars(statement))

    def list_artifact_lineage(self, artifact_id: str) -> list[ArtifactLineage]:
        statement = select(ArtifactLineage).where(
            (ArtifactLineage.from_artifact_id == artifact_id) | (ArtifactLineage.to_artifact_id == artifact_id)
        ).order_by(ArtifactLineage.created_at)
        return list(self.session.scalars(statement))

    def list_step_search_invocations(self, step_run_id: str) -> list[SearchInvocation]:
        statement = select(SearchInvocation).where(SearchInvocation.step_run_id == step_run_id).order_by(SearchInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_step_fetch_invocations(self, step_run_id: str) -> list[FetchInvocation]:
        statement = select(FetchInvocation).where(FetchInvocation.step_run_id == step_run_id).order_by(FetchInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_step_llm_invocations(self, step_run_id: str) -> list[LLMInvocation]:
        statement = select(LLMInvocation).where(LLMInvocation.step_run_id == step_run_id).order_by(LLMInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_step_tool_invocations(self, step_run_id: str) -> list[ToolInvocation]:
        statement = select(ToolInvocation).where(ToolInvocation.step_run_id == step_run_id).order_by(ToolInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_search_invocations(self, task_id: str) -> list[SearchInvocation]:
        statement = select(SearchInvocation).where(SearchInvocation.task_run_id == task_id).order_by(SearchInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_fetch_invocations(self, task_id: str) -> list[FetchInvocation]:
        statement = select(FetchInvocation).where(FetchInvocation.task_run_id == task_id).order_by(FetchInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_llm_invocations(self, task_id: str) -> list[LLMInvocation]:
        statement = select(LLMInvocation).where(LLMInvocation.task_run_id == task_id).order_by(LLMInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_tool_invocations(self, task_id: str) -> list[ToolInvocation]:
        statement = select(ToolInvocation).where(ToolInvocation.task_run_id == task_id).order_by(ToolInvocation.created_at)
        return list(self.session.scalars(statement))

    def list_task_events(self, task_id: str) -> list[TaskEvent]:
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
