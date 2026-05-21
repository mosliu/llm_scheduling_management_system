from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
from llm_scheduling_management_system.schemas.tasks import CreateTaskRequest, CreateTaskResponse, FinalReportResponse
from llm_scheduling_management_system.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class PublicOpinionReportRequest(BaseModel):
    """舆情报告生成请求数据模型。

    用途:
        承载创建舆情报告任务时所需的各种配置选项和主题词。

    用法:
        req = PublicOpinionReportRequest(topic="AI趋势")

    @Author: mosliu
    """
    topic: str
    tenant_id: str = "default"
    disable_cache: bool = True
    llm_profile_name: str = "advanced_reasoning_cn"
    execution_engine: str = "langgraph"
    search_limit: int = 20
    report_retry_count: int = 2
    llm_model_retry_count: int = 2
    report_fallback_profile_names: list[str] = Field(
        default_factory=lambda: ["grok_reasoning_optional", "claude_opus_web_search_optional", "cheap_structured_cn"]
    )
    search_provider_names: list[str] = Field(
        default_factory=lambda: ["tavily_search", "grok_search", "gpt_search", "exa_search"]
    )
    fetch_provider_name: str = "exa_contents"


@router.post("/public-opinion", response_model=CreateTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def create_public_opinion_report(
    request: PublicOpinionReportRequest,
    service: TaskService = Depends(get_task_service),
) -> CreateTaskResponse:
    """创建并提交舆情报告生成任务。

    用途:
        使用指定的舆情报告工作流模板（public_opinion_report_v1）创建并异步启动任务。

    用法:
        POST /api/v1/reports/public-opinion
        Body: PublicOpinionReportRequest

    @Author: mosliu
    """
    task = service.create_task(
        CreateTaskRequest(
            template_id="public_opinion_report_v1",
            tenant_id=request.tenant_id,
            input={"topic": request.topic},
            options={
                "disable_cache": request.disable_cache,
                "search_provider_names": request.search_provider_names,
                "search_limit": request.search_limit,
                "fetch_provider_name": request.fetch_provider_name,
                "llm_profile_name": request.llm_profile_name,
                "report_retry_count": request.report_retry_count,
                "llm_model_retry_count": request.llm_model_retry_count,
                "report_fallback_profile_names": request.report_fallback_profile_names,
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


@router.get("/public-opinion/{task_id}/final-report", response_model=FinalReportResponse)
def get_public_opinion_final_report(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> FinalReportResponse:
    """获取指定任务的最终生成的舆情报告。

    用途:
        从任务结果（生成物）中提取出最终渲染的 HTML 报告和元数据。

    用法:
        GET /api/v1/reports/public-opinion/{task_id}/final-report

    @Author: mosliu
    """
    payload = service.get_final_report(task_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return FinalReportResponse(**payload)
