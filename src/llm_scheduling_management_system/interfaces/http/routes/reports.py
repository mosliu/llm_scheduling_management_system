from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
from llm_scheduling_management_system.schemas.tasks import CreateTaskRequest, CreateTaskResponse
from llm_scheduling_management_system.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class PublicOpinionReportRequest(BaseModel):
    topic: str
    tenant_id: str = "default"
    disable_cache: bool = True
    llm_profile_name: str = "advanced_reasoning_cn"
    execution_engine: str = "langgraph"


@router.post("/public-opinion", response_model=CreateTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def create_public_opinion_report(
    request: PublicOpinionReportRequest,
    service: TaskService = Depends(get_task_service),
) -> CreateTaskResponse:
    task = service.create_task(
        CreateTaskRequest(
            template_id="public_opinion_report_v1",
            tenant_id=request.tenant_id,
            input={"topic": request.topic},
            options={
                "disable_cache": request.disable_cache,
                "search_provider_names": ["tavily_search", "grok_search", "exa_search"],
                "fetch_provider_name": "exa_contents",
                "llm_profile_name": request.llm_profile_name,
                "execution_engine": request.execution_engine,
            },
        )
    )
    return CreateTaskResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress_percent,
        query_url=f"/api/v1/tasks/{task.id}",
    )
