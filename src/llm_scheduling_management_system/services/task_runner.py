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
    """任务已完成异常类。

    用途:
        当试图运行一个已经处于成功或结束状态的任务时抛出。

    用法:
        raise TaskAlreadyCompletedError("task_123")

    @Author: mosliu
    """
    pass


class StepExecutionFailedError(Exception):
    """步骤执行失败异常类。

    用途:
        在模拟执行步骤或由于特定配置强行让某个步骤执行失败时使用。

    用法:
        raise StepExecutionFailedError("step_1", "Simulated error")

    @Author: mosliu
    """
    def __init__(self, node_key: str, message: str) -> None:
        """初始化 StepExecutionFailedError 实例。

        用途:
            绑定失败的节点 Key 及错误信息。

        用法:
            exc = StepExecutionFailedError("step_1", "Simulated error")

        @Author: mosliu
        """
        super().__init__(message)
        self.node_key = node_key
        self.message = message


class TaskRunner:
    """任务调度及执行控制服务。

    用途:
        负责驱动并按序执行任务下的所有步骤，处理输入 Artifact 的依赖注入、步骤级缓存（Cache Hits）、模拟执行失败与重试等核心控制流。

    用法:
        runner = TaskRunner(repository, registry)
        updated_task = runner.run_task(task)

    @Author: mosliu
    """

    def __init__(self, repository: TaskRepository, registry: ExecutorRegistry | None = None) -> None:
        """初始化 TaskRunner 实例。

        用途:
            注入底层的任务仓储 TaskRepository，以及执行器注册表 ExecutorRegistry。

        用法:
            runner = TaskRunner(repository, registry)

        @Author: mosliu
        """
        self.repository = repository
        self.registry = registry or ExecutorRegistry()

    def run_task(self, task: TaskRun) -> TaskRun:
        """完整驱动执行任务的全部待处理步骤。

        用途:
            将任务状态更改为运行中，并依次提取、执行当前未完成的步骤，直到任务全部成功或遇到阻塞（如重试等待、步骤失败等）。

        用法:
            task = runner.run_task(task)

        @Author: mosliu
        """
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
        """仅向前驱动执行任务的下一个待处理步骤。

        用途:
            单步推进任务的调度。若存在待处理步骤，标记任务运行，执行单步并返回。

        用法:
            task = runner.run_next_step(task)

        @Author: mosliu
        """
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
        """执行一个特定的步骤。

        用途:
            重置并加载特定的步骤及任务模型，通过内部单步方法驱动执行。

        用法:
            task = runner.run_specific_step(task, step)

        @Author: mosliu
        """
        step_state = sqlalchemy_inspect(step)
        step_identity = step_state.identity[0] if step_state.identity else getattr(step, "id", None)
        current_task = self.repository.get_task(task.id) or task
        current_step = self.repository.get_step(step_identity) if step_identity else step
        return self._run_single_step(current_task, current_step)

    def _get_pending_steps(self, task: TaskRun) -> list:
        """获取任务当前的所有待处理步骤。

        用途:
            按 sequence_no 升序排序，筛选出所有状态为 PENDING 或 RETRYING 的步骤。

        用法:
            steps = runner._get_pending_steps(task)

        @Author: mosliu
        """
        return [
            step
            for step in sorted(task.step_runs, key=lambda item: item.sequence_no)
            if step.status in {StepStatus.PENDING.value, StepStatus.RETRYING.value}
        ]

    def _run_single_step(self, task: TaskRun, step) -> TaskRun:
        """运行单个步骤的具体业务流（包括依赖注入、缓存校验、执行与持久化）。

        用途:
            用于具体执行某个步骤。若有需要会注入上游的输出 Artifact，计算缓存键（缓存命中则快速完成），否则调用对应的具体 Executor 执行，处理执行失败及重试逻辑，并在成功后持久化相关服务调用元数据，推进任务状态。

        用法:
            task = runner._run_single_step(task, step)

        @Author: mosliu
        """
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
        """根据任务配置模拟特定的节点步骤失败。

        用途:
            支持从外部通过配置（一次性失败或持续失败配置）来模拟节点执行错误，以便测试重试机制和异常流程。

        用法:
            runner._simulate_failure_if_configured(task, step)

        @Author: mosliu
        """
        fail_once_nodes = set(task.options_payload.get("simulate_fail_once_nodes", []))
        fail_always_nodes = set(task.options_payload.get("simulate_fail_always_nodes", []))
        if step.node_key in fail_always_nodes:
            raise StepExecutionFailedError(step.node_key, f"Simulated failure for {step.node_key}")
        if step.node_key in fail_once_nodes and step.attempt_no == 1:
            raise StepExecutionFailedError(step.node_key, f"Simulated one-time failure for {step.node_key}")

    def _get_max_attempts(self, task: TaskRun) -> int:
        """从任务选项中获取指定步骤的最大尝试（运行）次数。

        用途:
            读取任务重试策略参数，默认值为 2。

        用法:
            max_attempts = runner._get_max_attempts(task)

        @Author: mosliu
        """
        retry_policy = task.options_payload.get("retry_policy", {})
        max_attempts = retry_policy.get("max_attempts", 2)
        return max(1, int(max_attempts))

    def _build_cache_key(self, task: TaskRun, step) -> str | None:
        """为步骤生成缓存键（Cache Key）。

        用途:
            结合步骤名称、模板信息、输入参数、选项参数及所有上游 Artifact 的哈希值，计算该步骤的 SHA256 唯一缓存键。若缓存被禁用则返回 None。

        用法:
            key = runner._build_cache_key(task, step)

        @Author: mosliu
        """
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
