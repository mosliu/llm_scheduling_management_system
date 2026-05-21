from fastapi import APIRouter, Depends

from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
from llm_scheduling_management_system.schemas.tasks import SystemStatusResponse
from llm_scheduling_management_system.services.task_service import TaskService
from llm_scheduling_management_system.settings import settings

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    service: TaskService = Depends(get_task_service),
) -> SystemStatusResponse:
    """获取系统运行状态和统计数据。

    用途:
        查询系统的全局摘要状态，包括已注册模板数、各服务商统计、各状态下的任务数及任务总数。

    用法:
        GET /api/v1/system/status

    @Author: mosliu
    """
    data = service.get_system_status()
    return SystemStatusResponse(
        app_name=settings.app_name,
        template_count=data["template_count"],
        provider_counts=data["provider_counts"],
        task_status_counts=data["task_status_counts"],
        total_tasks=data["total_tasks"],
    )
