from enum import StrEnum


class TaskStatus(StrEnum):
    """任务的运行状态枚举。

    用途:
        用于标识和管理工作流任务生命周期中的各种执行状态。

    用法:
        直接作为模型的属性状态，例如 `task.status = TaskStatus.RUNNING`。

    @Author: mosliu
    """
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_RETRY = "waiting_retry"
    WAITING_MANUAL = "waiting_manual"
    PARTIAL_FAILED = "partial_failed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    """步骤执行状态枚举。

    用途:
        用于标识任务内部具体各个步骤（Step Run）的执行状态。

    用法:
        常用于表示工作流中单个节点的运行状态，例如 `step.status = StepStatus.SUCCEEDED`。

    @Author: mosliu
    """
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CACHED = "cached"


class ArtifactLevel(StrEnum):
    """生成物（Artifact）层级枚举。

    用途:
        描述工作流产生的数据或文件在处理链路中的加工程度/生命周期层级。

    用法:
        常在创建或保存 Artifact 时进行状态标记，如 `artifact.level = ArtifactLevel.RAW`。

    @Author: mosliu
    """
    RAW = "raw"
    NORMALIZED = "normalized"
    DERIVED = "derived"
    FINAL = "final"
