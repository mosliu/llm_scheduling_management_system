import hashlib
import json

from loguru import logger
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.exc import OperationalError

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
            task = self.repository.mark_task_running(task, current_step_run_id=pending_steps[0].id)

        logger.info("Running task {} with {} pending steps", task.id, len(pending_steps))

        while True:
            current_task = self.repository.get_task(task.id) or task
            current_pending_steps = self._get_pending_steps(current_task)
            if not current_pending_steps:
                break
            task = self._run_single_step(current_task, current_pending_steps[0])
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
        step_state = sqlalchemy_inspect(step)
        step_identity = step_state.identity[0] if step_state.identity else getattr(step, "id", None)
        current_task = self.repository.get_task(task.id) or task
        current_step = self.repository.get_step(step_identity) if step_identity else step
        return self._run_single_step(current_task, current_step)

    def _get_pending_steps(self, task: TaskRun) -> list:
        return [
            step
            for step in sorted(task.step_runs, key=lambda item: item.sequence_no)
            if step.status in {StepStatus.PENDING.value, StepStatus.RETRYING.value}
        ]

    def _run_single_step(self, task: TaskRun, step) -> TaskRun:
        task_id = task.id
        step_id = step.id
        step_node_key = step.node_key
        artifact_by_id = {artifact.id: artifact for artifact in task.artifacts}
        available_artifacts = self.repository.list_task_artifacts(task.id)
        latest_upstream_artifact_ids = []
        if available_artifacts:
            step_sequence_by_id = {item.id: item.sequence_no for item in task.step_runs}
            eligible_artifacts = [
                artifact
                for artifact in available_artifacts
                if artifact.step_run_id != step.id
                and step_sequence_by_id.get(artifact.step_run_id or "", 0) < step.sequence_no
            ]
            if eligible_artifacts and not step.input_artifact_refs:
                latest_artifact = max(
                    eligible_artifacts,
                    key=lambda artifact: (
                        step_sequence_by_id.get(artifact.step_run_id or "", 0),
                        artifact.created_at,
                    ),
                )
                latest_upstream_artifact_ids = [latest_artifact.id]
        if latest_upstream_artifact_ids:
            step.input_artifact_refs = latest_upstream_artifact_ids
        for artifact_id in step.input_artifact_refs:
            if artifact_id in artifact_by_id:
                continue
            external_artifact = self.repository.get_artifact(artifact_id)
            if external_artifact is not None:
                task.artifacts.append(external_artifact)
                artifact_by_id[artifact_id] = external_artifact
        cache_key = self._build_cache_key(task, step)
        if cache_key is not None:
            cached_artifact = self.repository.find_cached_artifact(cache_key)
            if cached_artifact is not None:
                logger.info(
                    "Cache hit for step {} on task {} using artifact {}",
                    step_node_key,
                    task_id,
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
            step_node_key,
            task_id,
            executor.__class__.__name__,
        )
        try:
            self._simulate_failure_if_configured(task, step)
            result = executor.execute(task, step)
        except StepExecutionFailedError as exc:
            logger.warning("Step {} failed for task {}: {}", step_node_key, task_id, exc.message)
            return self.repository.fail_step(
                task=task,
                step=step,
                error_code="simulated_step_failure",
                error_message=exc.message,
                max_attempts=self._get_max_attempts(task),
            )
        # Long-running external calls can leave the checked-out DB connection stale.
        # Releasing the session here forces a fresh checkout for persistence.
        self.repository.session.close()
        reloaded_task = self.repository.get_task(task_id)
        reloaded_step = self.repository.get_step(step_id)
        if reloaded_task is None or reloaded_step is None:
            raise RuntimeError(f"Task or step disappeared before persistence: {task_id} / {step_id}")
        advance_kwargs = {
            "task": reloaded_task,
            "step": reloaded_step,
            "artifact_type": result.artifact_type,
            "artifact_level": result.artifact_level,
            "schema_name": result.schema_name,
            "schema_version": result.schema_version,
            "content_json": result.content_json,
            "content_text": result.content_text,
            "checkpoint_type": result.checkpoint_type,
            "reusable_flag": result.reusable_flag,
            "input_artifact_ids": result.input_artifact_ids or latest_upstream_artifact_ids or reloaded_step.input_artifact_refs,
            "search_invocations": result.search_invocations,
            "fetch_invocations": result.fetch_invocations,
            "tool_invocations": result.tool_invocations,
            "llm_invocations": result.llm_invocations,
            "cache_key": cache_key,
        }
        try:
            task = self.repository.advance_step(**advance_kwargs)
        except OperationalError as exc:
            self.repository.session.rollback()
            logger.warning(
                "OperationalError while persisting step {} for task {}. Rolling back and retrying once. {}",
                step_node_key,
                task_id,
                exc,
            )
            reloaded_task = self.repository.get_task(task_id)
            reloaded_step = self.repository.get_step(step_id)
            if reloaded_task is None or reloaded_step is None:
                raise
            advance_kwargs["task"] = reloaded_task
            advance_kwargs["step"] = reloaded_step
            task = self.repository.advance_step(**advance_kwargs)
        logger.info(
            "Completed step {} for task {}. progress={} status={}",
            step_node_key,
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
