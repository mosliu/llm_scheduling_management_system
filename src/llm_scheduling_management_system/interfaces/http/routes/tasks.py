from fastapi import APIRouter, Depends, HTTPException, Query, status

from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
from llm_scheduling_management_system.interfaces.http.mappers import (
    map_document,
    map_fetch_invocation,
    map_llm_invocation,
    map_search_hit,
    map_search_invocation,
    map_task_detail,
    map_task_event,
    map_task_summary,
    map_tool_invocation,
)
from llm_scheduling_management_system.schemas.tasks import (
    ArtifactReferenceResponse,
    CheckpointReferenceResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    DocumentResponse,
    FinalReportResponse,
    FetchInvocationResponse,
    LLMInvocationResponse,
    RunTaskResponse,
    SearchHitResponse,
    SearchInvocationResponse,
    ToolInvocationResponse,
    TaskBundleResponse,
    TaskGraphEdgeResponse,
    TaskGraphNodeResponse,
    TaskGraphResponse,
    StepRunResponse,
    TaskDetailResponse,
    TaskEventResponse,
    TaskStatsResponse,
    TaskSummaryResponse,
)
from llm_scheduling_management_system.services.task_service import (
    ForkStartNodeNotFoundError,
    ForkTaskNotFoundError,
    ResumeArtifactNotFoundError,
    ResumeCheckpointNotFoundError,
    TaskAlreadyCompletedError,
    TaskNotCancellableError,
    TaskService,
    TaskTemplateNotFoundError,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskSummaryResponse])
def list_tasks(
    status: str | None = Query(default=None),
    template_id: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: TaskService = Depends(get_task_service),
) -> list[TaskSummaryResponse]:
    tasks = service.list_tasks(
        status=status,
        template_id=template_id,
        tenant_id=tenant_id,
        limit=limit,
    )
    return [map_task_summary(task) for task in tasks]


@router.post("", response_model=CreateTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def create_task(
    request: CreateTaskRequest,
    service: TaskService = Depends(get_task_service),
) -> CreateTaskResponse:
    try:
        task = service.create_task(request)
    except TaskTemplateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "workflow_template_not_found", "message": f"Unknown template: {exc}"},
        ) from exc
    except ResumeCheckpointNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "checkpoint_not_found", "message": f"Unknown checkpoint: {exc}"},
        ) from exc
    except ResumeArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "artifact_not_found", "message": f"Unknown artifact: {exc}"},
        ) from exc
    except ForkTaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "source_task_not_found", "message": f"Unknown source task: {exc}"},
        ) from exc
    except ForkStartNodeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "source_task_node_not_found", "message": f"Unknown source node: {exc}"},
        ) from exc

    return CreateTaskResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress_percent,
        query_url=f"/api/v1/tasks/{task.id}",
    )


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(
    task_id: str,
    include: str | None = Query(default=None, description="Reserved for future selective expansion."),
    service: TaskService = Depends(get_task_service),
) -> TaskDetailResponse:
    _ = include
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    return map_task_detail(task)


@router.get("/{task_id}/steps", response_model=list[StepRunResponse])
def list_task_steps(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[StepRunResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    detail = map_task_detail(task)
    return detail.steps


@router.get("/{task_id}/artifacts", response_model=list[ArtifactReferenceResponse])
def list_task_artifacts(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[ArtifactReferenceResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    detail = map_task_detail(task)
    return detail.artifacts


@router.get("/{task_id}/checkpoints", response_model=list[CheckpointReferenceResponse])
def list_task_checkpoints(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[CheckpointReferenceResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    detail = map_task_detail(task)
    return detail.available_checkpoints


@router.get("/{task_id}/search-invocations", response_model=list[SearchInvocationResponse])
def list_task_search_invocations(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[SearchInvocationResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return [map_search_invocation(item) for item in service.list_task_search_invocations(task_id)]


@router.get("/{task_id}/fetch-invocations", response_model=list[FetchInvocationResponse])
def list_task_fetch_invocations(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[FetchInvocationResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return [map_fetch_invocation(item) for item in service.list_task_fetch_invocations(task_id)]


@router.get("/{task_id}/llm-invocations", response_model=list[LLMInvocationResponse])
def list_task_llm_invocations(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[LLMInvocationResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return [map_llm_invocation(item) for item in service.list_task_llm_invocations(task_id)]


@router.get("/{task_id}/tool-invocations", response_model=list[ToolInvocationResponse])
def list_task_tool_invocations(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[ToolInvocationResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return [map_tool_invocation(item) for item in service.list_task_tool_invocations(task_id)]


@router.get("/{task_id}/events", response_model=list[TaskEventResponse])
def list_task_events(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[TaskEventResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return [map_task_event(item) for item in service.list_task_events(task_id)]


@router.get("/{task_id}/stats", response_model=TaskStatsResponse)
def get_task_stats(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskStatsResponse:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    step_status_counts: dict[str, int] = {}
    for step in task.step_runs:
        step_status_counts[step.status] = step_status_counts.get(step.status, 0) + 1

    artifact_type_counts: dict[str, int] = {}
    for artifact in task.artifacts:
        artifact_type_counts[artifact.artifact_type] = artifact_type_counts.get(artifact.artifact_type, 0) + 1

    cached_step_count = sum(1 for step in task.step_runs if step.status == "cached")
    search_hits = service.list_task_search_hits(task_id)
    documents = service.list_task_documents(task_id)
    search_invocations = service.list_task_search_invocations(task_id)
    fetch_invocations = service.list_task_fetch_invocations(task_id)
    tool_invocations = service.list_task_tool_invocations(task_id)
    llm_invocations = service.list_task_llm_invocations(task_id)
    events = service.list_task_events(task_id)

    return TaskStatsResponse(
        task_id=task.id,
        status=task.status,
        planned_step_count=task.planned_step_count,
        completed_step_count=task.completed_step_count,
        step_status_counts=step_status_counts,
        artifact_count=len(task.artifacts),
        document_count=len(documents),
        artifact_type_counts=artifact_type_counts,
        cached_step_count=cached_step_count,
        search_hit_count=len(search_hits),
        search_invocation_count=len(search_invocations),
        fetch_invocation_count=len(fetch_invocations),
        tool_invocation_count=len(tool_invocations),
        llm_invocation_count=len(llm_invocations),
        event_count=len(events),
    )


@router.get("/{task_id}/search-hits", response_model=list[SearchHitResponse])
def list_task_search_hits(
    task_id: str,
    provider_name: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    region_hint: str | None = Query(default=None),
    published_after: str | None = Query(default=None),
    published_before: str | None = Query(default=None),
    service: TaskService = Depends(get_task_service),
) -> list[SearchHitResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return [
        map_search_hit(item)
        for item in service.list_task_search_hits(
            task_id,
            provider_name=provider_name,
            source_type=source_type,
            region_hint=region_hint,
            published_after=published_after,
            published_before=published_before,
        )
    ]


@router.get("/{task_id}/documents", response_model=list[DocumentResponse])
def list_task_documents(
    task_id: str,
    provider_name: str | None = Query(default=None),
    source_domain: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    region_hint: str | None = Query(default=None),
    published_after: str | None = Query(default=None),
    published_before: str | None = Query(default=None),
    service: TaskService = Depends(get_task_service),
) -> list[DocumentResponse]:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return [
        map_document(item)
        for item in service.list_task_documents(
            task_id,
            provider_name=provider_name,
            source_domain=source_domain,
            source_type=source_type,
            region_hint=region_hint,
            published_after=published_after,
            published_before=published_before,
        )
    ]


@router.get("/{task_id}/graph", response_model=TaskGraphResponse)
def get_task_graph(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskGraphResponse:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    artifacts = service.repository.list_task_artifacts(task_id)
    artifact_by_id = {artifact.id: artifact for artifact in artifacts}
    lineage = []
    for artifact in artifacts:
        lineage.extend(service.list_artifact_lineage(artifact.id))

    nodes = []
    edges = []

    for step in sorted(task.step_runs, key=lambda item: item.sequence_no):
        step_node_id = f"step:{step.id}"
        nodes.append(
            TaskGraphNodeResponse(
                node_id=step_node_id,
                node_kind="step",
                label=step.node_key,
                status=step.status,
                metadata={"title": step.title, "sequence_no": step.sequence_no},
            )
        )
        for artifact_id in step.input_artifact_refs:
            if artifact_id in artifact_by_id:
                edges.append(
                    TaskGraphEdgeResponse(
                        edge_id=f"artifact-input:{artifact_id}:{step.id}",
                        edge_kind="artifact_input",
                        from_node_id=f"artifact:{artifact_id}",
                        to_node_id=step_node_id,
                        metadata={},
                    )
                )

    for artifact in artifacts:
        artifact_node_id = f"artifact:{artifact.id}"
        nodes.append(
            TaskGraphNodeResponse(
                node_id=artifact_node_id,
                node_kind="artifact",
                label=artifact.artifact_type,
                metadata={"artifact_level": artifact.artifact_level, "schema_name": artifact.schema_name},
            )
        )
        if artifact.step_run_id:
            edges.append(
                TaskGraphEdgeResponse(
                    edge_id=f"step-output:{artifact.step_run_id}:{artifact.id}",
                    edge_kind="step_output",
                    from_node_id=f"step:{artifact.step_run_id}",
                    to_node_id=artifact_node_id,
                    metadata={},
                )
            )

    seen_lineage_edges = set()
    for edge in lineage:
        edge_key = (edge.from_artifact_id, edge.to_artifact_id, edge.relation_type)
        if edge_key in seen_lineage_edges:
            continue
        seen_lineage_edges.add(edge_key)
        edges.append(
            TaskGraphEdgeResponse(
                edge_id=f"lineage:{edge.id}",
                edge_kind=edge.relation_type,
                from_node_id=f"artifact:{edge.from_artifact_id}",
                to_node_id=f"artifact:{edge.to_artifact_id}",
                metadata={},
            )
        )

    return TaskGraphResponse(task_id=task.id, nodes=nodes, edges=edges)


@router.get("/{task_id}/bundle", response_model=TaskBundleResponse)
def get_task_bundle(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskBundleResponse:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    detail = map_task_detail(task)
    step_status_counts: dict[str, int] = {}
    for step in task.step_runs:
        step_status_counts[step.status] = step_status_counts.get(step.status, 0) + 1
    artifact_type_counts: dict[str, int] = {}
    for artifact in task.artifacts:
        artifact_type_counts[artifact.artifact_type] = artifact_type_counts.get(artifact.artifact_type, 0) + 1

    search_hits = service.list_task_search_hits(task_id)
    documents = service.list_task_documents(task_id)
    search_invocations = service.list_task_search_invocations(task_id)
    fetch_invocations = service.list_task_fetch_invocations(task_id)
    tool_invocations = service.list_task_tool_invocations(task_id)
    llm_invocations = service.list_task_llm_invocations(task_id)
    events = service.list_task_events(task_id)

    stats = TaskStatsResponse(
        task_id=task.id,
        status=task.status,
        planned_step_count=task.planned_step_count,
        completed_step_count=task.completed_step_count,
        step_status_counts=step_status_counts,
        artifact_count=len(task.artifacts),
        document_count=len(documents),
        artifact_type_counts=artifact_type_counts,
        cached_step_count=sum(1 for step in task.step_runs if step.status == "cached"),
        search_hit_count=len(search_hits),
        search_invocation_count=len(search_invocations),
        fetch_invocation_count=len(fetch_invocations),
        tool_invocation_count=len(tool_invocations),
        llm_invocation_count=len(llm_invocations),
        event_count=len(events),
    )

    return TaskBundleResponse(
        task=detail,
        stats=stats,
        events=[map_task_event(item) for item in events],
        search_hits=[map_search_hit(item) for item in search_hits],
        documents=[map_document(item) for item in documents],
        search_invocations=[map_search_invocation(item) for item in search_invocations],
        fetch_invocations=[map_fetch_invocation(item) for item in fetch_invocations],
        tool_invocations=[map_tool_invocation(item) for item in tool_invocations],
        llm_invocations=[map_llm_invocation(item) for item in llm_invocations],
    )


@router.get("/{task_id}/final-report", response_model=FinalReportResponse)
def get_task_final_report(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> FinalReportResponse:
    payload = service.get_final_report(task_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )
    return FinalReportResponse(**payload)


@router.post("/{task_id}/run", response_model=RunTaskResponse)
def run_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> RunTaskResponse:
    try:
        task = service.run_task(task_id)
    except TaskAlreadyCompletedError:
        existing = service.get_task(task_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
            )
        task = existing

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    return RunTaskResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress_percent,
        planned_step_count=task.planned_step_count,
        completed_step_count=task.completed_step_count,
    )


@router.post("/{task_id}/run-next-step", response_model=RunTaskResponse)
def run_next_step(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> RunTaskResponse:
    try:
        task = service.run_next_step(task_id)
    except TaskAlreadyCompletedError:
        existing = service.get_task(task_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
            )
        task = existing

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    return RunTaskResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress_percent,
        planned_step_count=task.planned_step_count,
        completed_step_count=task.completed_step_count,
    )


@router.post("/{task_id}/cancel", response_model=RunTaskResponse)
def cancel_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> RunTaskResponse:
    try:
        task = service.cancel_task(task_id)
    except TaskNotCancellableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "task_not_cancellable", "message": f"Task is not cancellable from state: {exc}"},
        ) from exc

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Unknown task: {task_id}"},
        )

    return RunTaskResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress_percent,
        planned_step_count=task.planned_step_count,
        completed_step_count=task.completed_step_count,
    )
