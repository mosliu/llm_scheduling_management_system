from fastapi import Depends
from sqlalchemy.orm import Session

from llm_scheduling_management_system.db import get_db_session
from llm_scheduling_management_system.services.task_service import TaskService


def get_task_service(session: Session = Depends(get_db_session)) -> TaskService:
    return TaskService(session)

