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
