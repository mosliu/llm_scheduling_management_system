from fastapi import APIRouter, Depends
from fastapi import HTTPException, status

from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
from llm_scheduling_management_system.interfaces.http.mappers import map_template, map_template_detail
from llm_scheduling_management_system.schemas.tasks import WorkflowTemplateDetailResponse, WorkflowTemplateResponse
from llm_scheduling_management_system.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/workflow-templates", tags=["workflow-templates"])


@router.get("", response_model=list[WorkflowTemplateResponse])
def list_workflow_templates(
    service: TaskService = Depends(get_task_service),
) -> list[WorkflowTemplateResponse]:
    """获取所有可用工作流模板的列表。

    用途:
        查询系统中所有已注册的工作流模板。

    用法:
        GET /api/v1/workflow-templates

    @Author: mosliu
    """
    templates = service.list_templates()
    return [map_template(template) for template in templates]


@router.get("/{template_id}", response_model=WorkflowTemplateDetailResponse)
def get_workflow_template(
    template_id: str,
    service: TaskService = Depends(get_task_service),
) -> WorkflowTemplateDetailResponse:
    """获取指定工作流模板的详细信息与蓝图步骤。

    用途:
        查询特定工作流模板的详细配置和所包含的步骤。

    用法:
        GET /api/v1/workflow-templates/{template_id}

    @Author: mosliu
    """
    template, blueprint = service.get_template_with_blueprint(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "workflow_template_not_found", "message": f"Unknown template: {template_id}"},
        )
    return map_template_detail(template, blueprint)
