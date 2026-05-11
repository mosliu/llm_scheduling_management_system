import hashlib
import json

from loguru import logger

from llm_scheduling_management_system.domain.enums import StepStatus, TaskStatus
from llm_scheduling_management_system.domain.models import TaskRun
from llm_scheduling_management_system.execution.registry import ExecutorRegistry
from llm_scheduling_management_system.repositories.task_repository import TaskRepository


class TaskAlreadyCompletedError(Exception):
    pass


class StepExecutionFailedError(Exception):
    def __init__(self, node_key: str, message: str) -> None:
        super().__init__(message)
        self.node_key = node_key
        self.message = message


class TaskRunner:
    def __init__(self, repository: TaskRepository, registry: ExecutorRegistry | None = None) -> None:
        self.repository = repository
        self.registry = registry or ExecutorRegistry()

    def run_task(self, task: TaskRun) -> TaskRun:
        if task.status == TaskStatus.SUCCEEDED.value:
            raise TaskAlreadyCompletedError(task.id)

        pending_steps = self._get_pending_steps(task)
        if pending_steps:
            self.repository.mark_task_running(task, current_step_run_id=pending_steps[0].id)

        logger.info("Running task {} with {} pending steps", task.id, len(pending_steps))

        for step in pending_steps:
            task = self._run_single_step(task, step)
            if task.status in {TaskStatus.WAITING_RETRY.value, TaskStatus.FAILED.value, TaskStatus.PARTIAL_FAILED.value}:
                break

        return self.repository.get_task(task.id) or task

    def run_next_step(self, task: TaskRun) -> TaskRun:
        if task.status == TaskStatus.SUCCEEDED.value:
            raise TaskAlreadyCompletedError(task.id)

        pending_steps = self._get_pending_steps(task)
        if not pending_steps:
            return self.repository.get_task(task.id) or task

        self.repository.mark_task_running(task, current_step_run_id=pending_steps[0].id)
        logger.info("Running next step for task {}: {}", task.id, pending_steps[0].node_key)
        task = self.run_specific_step(task, pending_steps[0])
        return self.repository.get_task(task.id) or task

    def run_specific_step(self, task: TaskRun, step) -> TaskRun:
        return self._run_single_step(task, step)

    def _get_pending_steps(self, task: TaskRun) -> list:
        return [
            step
            for step in sorted(task.step_runs, key=lambda item: item.sequence_no)
            if step.status in {StepStatus.PENDING.value, StepStatus.RETRYING.value}
        ]

    def _run_single_step(self, task: TaskRun, step) -> TaskRun:
        available_artifacts = self.repository.list_task_artifacts(task.id)
        latest_upstream_artifact_ids = []
        if available_artifacts:
            latest_artifact = available_artifacts[-1]
            if latest_artifact.step_run_id != step.id and not step.input_artifact_refs:
                latest_upstream_artifact_ids = [latest_artifact.id]
        if latest_upstream_artifact_ids:
            step.input_artifact_refs = latest_upstream_artifact_ids
        cache_key = self._build_cache_key(task, step)
        if cache_key is not None:
            cached_artifact = self.repository.find_cached_artifact(cache_key)
            if cached_artifact is not None:
                logger.info(
                    "Cache hit for step {} on task {} using artifact {}",
                    step.node_key,
                    task.id,
                    cached_artifact.id,
                )
                return self.repository.complete_step_from_cache(
                    task=task,
                    step=step,
                    cache_key=cache_key,
                    source_artifact=cached_artifact,
                )
        executor = self.registry.get(step.node_key)
        logger.info(
            "Executing step {} for task {} using executor {}",
            step.node_key,
            task.id,
            executor.__class__.__name__,
        )
        try:
            self._simulate_failure_if_configured(task, step)
            result = executor.execute(task, step)
        except StepExecutionFailedError as exc:
            logger.warning("Step {} failed for task {}: {}", step.node_key, task.id, exc.message)
            return self.repository.fail_step(
                task=task,
                step=step,
                error_code="simulated_step_failure",
                error_message=exc.message,
                max_attempts=self._get_max_attempts(task),
            )
        task = self.repository.advance_step(
            task=task,
            step=step,
            artifact_type=result.artifact_type,
            artifact_level=result.artifact_level,
            schema_name=result.schema_name,
            schema_version=result.schema_version,
            content_json=result.content_json,
            content_text=result.content_text,
            checkpoint_type=result.checkpoint_type,
            reusable_flag=result.reusable_flag,
            input_artifact_ids=result.input_artifact_ids or latest_upstream_artifact_ids or step.input_artifact_refs,
            search_invocations=result.search_invocations,
            fetch_invocations=result.fetch_invocations,
            tool_invocations=result.tool_invocations,
            llm_invocations=result.llm_invocations,
            cache_key=cache_key,
        )
        logger.info(
            "Completed step {} for task {}. progress={} status={}",
            step.node_key,
            task.id,
            task.progress_percent,
            task.status,
        )
        return task

    def _simulate_failure_if_configured(self, task: TaskRun, step) -> None:
        fail_once_nodes = set(task.options_payload.get("simulate_fail_once_nodes", []))
        fail_always_nodes = set(task.options_payload.get("simulate_fail_always_nodes", []))
        if step.node_key in fail_always_nodes:
            raise StepExecutionFailedError(step.node_key, f"Simulated failure for {step.node_key}")
        if step.node_key in fail_once_nodes and step.attempt_no == 1:
            raise StepExecutionFailedError(step.node_key, f"Simulated one-time failure for {step.node_key}")

    def _get_max_attempts(self, task: TaskRun) -> int:
        retry_policy = task.options_payload.get("retry_policy", {})
        max_attempts = retry_policy.get("max_attempts", 2)
        return max(1, int(max_attempts))

    def _build_cache_key(self, task: TaskRun, step) -> str | None:
        if task.options_payload.get("disable_cache") is True:
            return None
        disabled_nodes = set(task.options_payload.get("disable_cache_nodes", []))
        if step.node_key in disabled_nodes:
            return None
        cacheable_steps = {
            "search_fanout",
            "fetch_documents",
            "merge_search_results",
            "normalize_and_filter",
            "classify_and_filter_sources",
            "extract_event_time",
            "build_timeline",
            "generate_event_summary",
            "analyze_public_opinion",
            "generate_timeline_report",
        }
        if step.node_key not in cacheable_steps:
            return None
        upstream_hashes = []
        if step.input_artifact_refs:
            available_artifacts = {
                artifact.id: artifact for artifact in self.repository.list_task_artifacts(task.id)
            }
            for artifact_id in step.input_artifact_refs:
                artifact = available_artifacts.get(artifact_id) or self.repository.get_artifact(artifact_id)
                if artifact is not None:
                    upstream_hashes.append(artifact.content_hash)
        payload = {
            "node_key": step.node_key,
            "template_id": task.template_id,
            "template_version": task.template_version,
            "input_payload": task.input_payload,
            "options_payload": task.options_payload,
            "upstream_hashes": upstream_hashes,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
