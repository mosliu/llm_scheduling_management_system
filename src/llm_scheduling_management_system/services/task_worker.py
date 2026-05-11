from __future__ import annotations

import time

from loguru import logger
from sqlalchemy.orm import Session

from llm_scheduling_management_system.repositories.task_repository import TaskRepository
from llm_scheduling_management_system.services.task_runner import TaskAlreadyCompletedError, TaskRunner


class TaskWorker:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = TaskRepository(session)
        self.runner = TaskRunner(self.repository)

    def process_once(self, limit: int = 10) -> int:
        processed = 0
        for task in self.repository.list_runnable_tasks(limit=limit):
            try:
                self.runner.run_next_step(task)
                processed += 1
            except TaskAlreadyCompletedError:
                logger.info("Task {} is already completed; skipping", task.id)
        return processed

    def process_until_idle(self, limit: int = 10) -> int:
        total_processed = 0
        while True:
            processed = self.process_once(limit=limit)
            total_processed += processed
            if processed == 0:
                break
        logger.info("Worker reached idle state after processing {} step(s)", total_processed)
        return total_processed

    def run_loop(self, poll_interval_seconds: float = 1.0) -> None:
        logger.info("Starting task worker loop with poll interval {}s", poll_interval_seconds)
        while True:
            processed = self.process_once()
            if processed == 0:
                time.sleep(poll_interval_seconds)
