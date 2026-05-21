from __future__ import annotations

import time

from loguru import logger
from sqlalchemy.orm import Session

from llm_scheduling_management_system.repositories.task_repository import TaskRepository
from llm_scheduling_management_system.services.task_runner import TaskAlreadyCompletedError, TaskRunner


class TaskWorker:
    """任务工作进程类。

    用途:
        负责轮询数据库中处于可运行状态的任务步骤，并通过任务运行器逐一驱动执行。

    用法:
        传入 SQLAlchemy 数据库会话实例化，然后调用 process_once、process_until_idle 或 run_loop 运行。

    @Author: mosliu
    """

    def __init__(self, session: Session) -> None:
        """初始化任务工作进程。

        用途:
            绑定数据库会话，并创建相关的底层 TaskRepository 和 TaskRunner 实例。

        用法:
            worker = TaskWorker(session)

        @Author: mosliu
        """
        self.session = session
        self.repository = TaskRepository(session)
        self.runner = TaskRunner(self.repository)

    def process_once(self, limit: int = 10) -> int:
        """执行单轮任务调度。

        用途:
            获取最多 limit 个当前可运行的任务，并驱动它们执行下一步。返回实际成功处理的任务步骤数。

        用法:
            processed = worker.process_once(limit=10)

        @Author: mosliu
        """
        processed = 0
        for task in self.repository.list_runnable_tasks(limit=limit):
            try:
                self.runner.run_next_step(task)
                processed += 1
            except TaskAlreadyCompletedError:
                logger.info("Task {} is already completed; skipping", task.id)
        return processed

    def process_until_idle(self, limit: int = 10) -> int:
        """持续执行任务直到空闲。

        用途:
            循环执行可运行的任务，直到没有待处理任务为止。返回累计处理的任务步骤总数。

        用法:
            total_processed = worker.process_until_idle(limit=10)

        @Author: mosliu
        """
        total_processed = 0
        while True:
            processed = self.process_once(limit=limit)
            total_processed += processed
            if processed == 0:
                break
        logger.info("Worker reached idle state after processing {} step(s)", total_processed)
        return total_processed

    def run_loop(self, poll_interval_seconds: float = 1.0) -> None:
        """启动无限轮询循环。

        用途:
            在后台无限循环执行可运行的任务。如果某一轮没有发现任何可执行任务，则休眠 poll_interval_seconds 秒后继续。

        用法:
            worker.run_loop(poll_interval_seconds=1.0)

        @Author: mosliu
        """
        logger.info("Starting task worker loop with poll interval {}s", poll_interval_seconds)
        while True:
            processed = self.process_once()
            if processed == 0:
                time.sleep(poll_interval_seconds)
