from fastapi import Depends
from sqlalchemy.orm import Session

from llm_scheduling_management_system.db import get_db_session
from llm_scheduling_management_system.services.elasticsearch_service import ElasticsearchService
from llm_scheduling_management_system.services.task_service import TaskService


def get_task_service(session: Session = Depends(get_db_session)) -> TaskService:
    """获取 TaskService 实例依赖注入函数。

    用途:
        用于 FastAPI 路由中依赖注入，提供基于当前数据库会话（Session）的 TaskService 实例。

    用法:
        @router.post("/tasks")
        def create_task(service: TaskService = Depends(get_task_service)):
            ...

    @Author: mosliu
    """
    return TaskService(session)


def get_elasticsearch_service() -> ElasticsearchService:
    """获取 ElasticsearchService 实例依赖注入函数。"""

    return ElasticsearchService()
