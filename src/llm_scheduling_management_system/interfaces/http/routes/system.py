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
    data = service.get_system_status()
    return SystemStatusResponse(
        app_name=settings.app_name,
        template_count=data["template_count"],
        provider_counts=data["provider_counts"],
        task_status_counts=data["task_status_counts"],
        total_tasks=data["total_tasks"],
    )
