from fastapi import APIRouter, Depends, HTTPException, Query, status

from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
from llm_scheduling_management_system.interfaces.http.mappers import (
    map_artifact_detail,
    map_artifact_lineage_edge,
    map_checkpoint_detail,
    map_document,
    map_fetch_invocation,
    map_llm_invocation,
    map_search_hit,
    map_search_invocation,
    map_step_detail,
    map_tool_invocation,
)
from llm_scheduling_management_system.schemas.tasks import (
    ArtifactDetailResponse,
    ArtifactLineageEdgeResponse,
    CheckpointDetailResponse,
    CreateDerivedTaskRequest,
    CreateTaskResponse,
    DocumentResponse,
    FetchInvocationResponse,
    LLMInvocationResponse,
    SearchHitResponse,
    SearchInvocationResponse,
    StepDetailResponse,
    ToolInvocationResponse,
)
from llm_scheduling_management_system.services.task_service import StepHasNoArtifactsError, TaskService, TaskTemplateNotFoundError

router = APIRouter(tags=["inspection"])


@router.get("/api/v1/steps/{step_run_id}", response_model=StepDetailResponse)
def get_step(
    step_run_id: str,
    service: TaskService = Depends(get_task_service),
) -> StepDetailResponse:
    """获取指定步骤的详细运行信息。

    用途:
        查询特定步骤运行记录（StepRun）的各种元数据和执行结果。

    用法:
        GET /api/v1/steps/{step_run_id}

    @Author: mosliu
    """
    step = service.get_step(step_run_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "step_not_found", "message": f"Unknown step: {step_run_id}"},
        )
    return map_step_detail(step)


@router.post("/api/v1/steps/{step_run_id}/derive-task", response_model=CreateTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def derive_task_from_step(
    step_run_id: str,
    request: CreateDerivedTaskRequest,
    service: TaskService = Depends(get_task_service),
) -> CreateTaskResponse:
    """从已执行的步骤生成/衍生出新的任务。

    用途:
        将某一步骤的生成物作为输入，触发并创建一个新的任务工作流。

    用法:
        POST /api/v1/steps/{step_run_id}/derive-task
        Body: CreateDerivedTaskRequest

    @Author: mosliu
    """
    try:
        task = service.create_task_from_step(step_run_id, request)
    except StepHasNoArtifactsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "step_has_no_artifacts", "message": f"Step has no artifacts: {exc}"},
        ) from exc
    except TaskTemplateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "workflow_template_not_found", "message": f"Unknown template: {exc}"},
        ) from exc

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "step_not_found", "message": f"Unknown step: {step_run_id}"},
        )

    return CreateTaskResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress_percent,
        query_url=f"/api/v1/tasks/{task.id}",
    )


@router.get("/api/v1/artifacts/{artifact_id}", response_model=ArtifactDetailResponse)
def get_artifact(
    artifact_id: str,
    service: TaskService = Depends(get_task_service),
) -> ArtifactDetailResponse:
    """获取指定生成物的详细信息。

    用途:
        查询并获取任务执行过程中产生的特定生成物（Artifact）的内容与元数据。

    用法:
        GET /api/v1/artifacts/{artifact_id}

    @Author: mosliu
    """
    artifact = service.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "artifact_not_found", "message": f"Unknown artifact: {artifact_id}"},
        )
    return map_artifact_detail(artifact)


@router.get("/api/v1/artifacts/{artifact_id}/lineage", response_model=list[ArtifactLineageEdgeResponse])
def get_artifact_lineage(
    artifact_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[ArtifactLineageEdgeResponse]:
    """查询指定生成物的血缘关系链。

    用途:
        获取当前生成物与其上下游生成物之间的依赖关系（边列表）。

    用法:
        GET /api/v1/artifacts/{artifact_id}/lineage

    @Author: mosliu
    """
    artifact = service.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "artifact_not_found", "message": f"Unknown artifact: {artifact_id}"},
        )
    return [map_artifact_lineage_edge(item) for item in service.list_artifact_lineage(artifact_id)]


@router.get("/api/v1/checkpoints/{checkpoint_id}", response_model=CheckpointDetailResponse)
def get_checkpoint(
    checkpoint_id: str,
    service: TaskService = Depends(get_task_service),
) -> CheckpointDetailResponse:
    """获取指定检查点的详细信息。

    用途:
        查询工作流执行过程中的某一个状态检查点（Checkpoint）及其关联数据。

    用法:
        GET /api/v1/checkpoints/{checkpoint_id}

    @Author: mosliu
    """
    checkpoint = service.get_checkpoint(checkpoint_id)
    if checkpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "checkpoint_not_found", "message": f"Unknown checkpoint: {checkpoint_id}"},
        )
    return map_checkpoint_detail(checkpoint)


@router.get("/api/v1/steps/{step_run_id}/search-invocations", response_model=list[SearchInvocationResponse])
def get_step_search_invocations(
    step_run_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[SearchInvocationResponse]:
    """获取指定步骤执行期间的搜索接口调用记录。

    用途:
        追踪和审计该步骤内进行过的所有网络搜索（Search）调用请求与响应。

    用法:
        GET /api/v1/steps/{step_run_id}/search-invocations

    @Author: mosliu
    """
    step = service.get_step(step_run_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "step_not_found", "message": f"Unknown step: {step_run_id}"},
        )
    return [map_search_invocation(item) for item in service.list_step_search_invocations(step_run_id)]


@router.get("/api/v1/steps/{step_run_id}/fetch-invocations", response_model=list[FetchInvocationResponse])
def get_step_fetch_invocations(
    step_run_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[FetchInvocationResponse]:
    """获取指定步骤执行期间的内容抓取接口调用记录。

    用途:
        追踪和审计该步骤内进行过的网页抓取/提取（Fetch）调用情况。

    用法:
        GET /api/v1/steps/{step_run_id}/fetch-invocations

    @Author: mosliu
    """
    step = service.get_step(step_run_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "step_not_found", "message": f"Unknown step: {step_run_id}"},
        )
    return [map_fetch_invocation(item) for item in service.list_step_fetch_invocations(step_run_id)]


@router.get("/api/v1/steps/{step_run_id}/documents", response_model=list[DocumentResponse])
def get_step_documents(
    step_run_id: str,
    provider_name: str | None = Query(default=None),
    source_domain: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    region_hint: str | None = Query(default=None),
    published_after: str | None = Query(default=None),
    published_before: str | None = Query(default=None),
    service: TaskService = Depends(get_task_service),
) -> list[DocumentResponse]:
    """获取指定步骤获取到的所有文档记录。

    用途:
        查询某一步骤执行中拉取到的网页正文或文档列表，并支持多维度过滤。

    用法:
        GET /api/v1/steps/{step_run_id}/documents

    @Author: mosliu
    """
    step = service.get_step(step_run_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "step_not_found", "message": f"Unknown step: {step_run_id}"},
        )
    return [
        map_document(item)
        for item in service.list_step_documents(
            step_run_id,
            provider_name=provider_name,
            source_domain=source_domain,
            source_type=source_type,
            region_hint=region_hint,
            published_after=published_after,
            published_before=published_before,
        )
    ]


@router.get("/api/v1/steps/{step_run_id}/llm-invocations", response_model=list[LLMInvocationResponse])
def get_step_llm_invocations(
    step_run_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[LLMInvocationResponse]:
    """获取指定步骤执行期间的大模型（LLM）调用记录。

    用途:
        追踪、调试和审计该步骤内进行过的所有大语言模型调用细节（提示词、回复、耗时等）。

    用法:
        GET /api/v1/steps/{step_run_id}/llm-invocations

    @Author: mosliu
    """
    step = service.get_step(step_run_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "step_not_found", "message": f"Unknown step: {step_run_id}"},
        )
    return [map_llm_invocation(item) for item in service.list_step_llm_invocations(step_run_id)]


@router.get("/api/v1/steps/{step_run_id}/tool-invocations", response_model=list[ToolInvocationResponse])
def get_step_tool_invocations(
    step_run_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[ToolInvocationResponse]:
    """获取指定步骤执行期间的 MCP 工具调用记录。

    用途:
        追踪和审计该步骤内运行过的所有外部 Model Context Protocol (MCP) 工具的请求和返回信息。

    用法:
        GET /api/v1/steps/{step_run_id}/tool-invocations

    @Author: mosliu
    """
    step = service.get_step(step_run_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "step_not_found", "message": f"Unknown step: {step_run_id}"},
        )
    return [map_tool_invocation(item) for item in service.list_step_tool_invocations(step_run_id)]


@router.get("/api/v1/steps/{step_run_id}/search-hits", response_model=list[SearchHitResponse])
def get_step_search_hits(
    step_run_id: str,
    provider_name: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    region_hint: str | None = Query(default=None),
    published_after: str | None = Query(default=None),
    published_before: str | None = Query(default=None),
    service: TaskService = Depends(get_task_service),
) -> list[SearchHitResponse]:
    """获取指定步骤执行期间的搜索命中条目。

    用途:
        获取某步骤通过搜索引擎检索到的命中网页摘要信息，并支持过滤。

    用法:
        GET /api/v1/steps/{step_run_id}/search-hits

    @Author: mosliu
    """
    step = service.get_step(step_run_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "step_not_found", "message": f"Unknown step: {step_run_id}"},
        )
    return [
        map_search_hit(item)
        for item in service.list_step_search_hits(
            step_run_id,
            provider_name=provider_name,
            source_type=source_type,
            region_hint=region_hint,
            published_after=published_after,
            published_before=published_before,
        )
    ]
