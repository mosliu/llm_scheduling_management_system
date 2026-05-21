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
    """列出任务运行记录。

    用途:
        根据状态、模板ID、租户ID等过滤条件，获取任务简要状态（TaskSummaryResponse）的列表。

    用法:
        GET /api/v1/tasks?status=running&limit=10

    @Author: mosliu
    """
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
    """创建新的工作流任务。

    用途:
        支持根据指定的模板、输入和配置项，创建全新任务；或者基于特定检查点（Checkpoint）、生成物（Artifact）进行恢复，或者分叉（Fork）已存在的任务。

    用法:
        POST /api/v1/tasks
        Body: CreateTaskRequest

    @Author: mosliu
    """
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
    """获取指定任务的详细信息。

    用途:
        查询特定任务运行记录（TaskRun）的全部详细信息，包括它的运行步骤、生成物和可用检查点等。

    用法:
        GET /api/v1/tasks/{task_id}

    @Author: mosliu
    """
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
    """获取指定任务的步骤运行记录列表。

    用途:
        获取任务关联的所有步骤运行记录（StepRun）列表。

    用法:
        GET /api/v1/tasks/{task_id}/steps

    @Author: mosliu
    """
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
    """获取指定任务的生成物引用列表。

    用途:
        列出当前任务产生的所有生成物（Artifact）的简要引用信息。

    用法:
        GET /api/v1/tasks/{task_id}/artifacts

    @Author: mosliu
    """
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
    """获取指定任务的可用状态检查点列表。

    用途:
        列出当前任务包含的所有用于继续、回滚或分叉的检查点信息。

    用法:
        GET /api/v1/tasks/{task_id}/checkpoints

    @Author: mosliu
    """
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
    """获取指定任务下的所有搜索接口调用记录。

    用途:
        获取整个任务执行过程中产生的所有网络搜索请求及其元数据。

    用法:
        GET /api/v1/tasks/{task_id}/search-invocations

    @Author: mosliu
    """
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
    """获取指定任务下的所有网页内容抓取接口调用记录。

    用途:
        汇总获取整个任务执行过程中网页内容抓取（Fetch）的请求和响应信息。

    用法:
        GET /api/v1/tasks/{task_id}/fetch-invocations

    @Author: mosliu
    """
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
    """获取指定任务下的所有大模型接口调用记录。

    用途:
        汇总获取整个任务执行过程中各个步骤所发生的所有大模型（LLM）调用历史。

    用法:
        GET /api/v1/tasks/{task_id}/llm-invocations

    @Author: mosliu
    """
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
    """获取指定任务下的所有 MCP 工具调用记录。

    用途:
        汇总获取当前任务执行中发起的所有外部工具（Tool）调用及输入/输出。

    用法:
        GET /api/v1/tasks/{task_id}/tool-invocations

    @Author: mosliu
    """
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
    """获取指定任务的全部事件/日志。

    用途:
        查询并获取此任务生命周期中记录的所有关键阶段转变或日志事件（TaskEvent）。

    用法:
        GET /api/v1/tasks/{task_id}/events

    @Author: mosliu
    """
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
    """获取指定任务的统计指标信息。

    用途:
        计算并统计该任务下步骤的执行状态分布、生成物的类型分布、API 各种调用（LLM、Search、Fetch、Tool）的汇总数。

    用法:
        GET /api/v1/tasks/{task_id}/stats

    @Author: mosliu
    """
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
    """获取指定任务执行期间记录到的搜索引擎命中的结果条目列表。

    用途:
        查询和筛选任务中由各搜索引擎所捕获到的网页/文献搜索结果摘要。

    用法:
        GET /api/v1/tasks/{task_id}/search-hits

    @Author: mosliu
    """
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
    """获取指定任务执行期间获取的网页文档正文。

    用途:
        查询并检索该任务抓取到的真实网页文本内容。

    用法:
        GET /api/v1/tasks/{task_id}/documents

    @Author: mosliu
    """
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
    """获取该任务的血缘与执行步骤关系图。

    用途:
        解析步骤输入/输出、生成物依赖，构造出一张包含步骤节点和生成物节点的拓扑关系图（Nodes & Edges）。

    用法:
        GET /api/v1/tasks/{task_id}/graph

    @Author: mosliu
    """
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
    """打包获取任务的全部运行时细节与关联日志数据。

    用途:
        提供一个一次性返回任务详情、统计信息、审计事件、搜索命中、网页文档、LLM/Fetch/Tool 接口调用明细的聚合包。

    用法:
        GET /api/v1/tasks/{task_id}/bundle

    @Author: mosliu
    """
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
    """获取该任务生成的最终报告。

    用途:
        直接提取并返回当前任务生成的最终 HTML 报告及相应的摘要数据。

    用法:
        GET /api/v1/tasks/{task_id}/final-report

    @Author: mosliu
    """
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
    """启动或继续执行工作流任务。

    用途:
        将任务提交给后台执行器异步运行全部未执行完的步骤。

    用法:
        POST /api/v1/tasks/{task_id}/run

    @Author: mosliu
    """
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
    """单步执行该任务的下一个待执行步骤。

    用途:
        支持工作流的人工单步调试模式，使任务只向后执行一步就暂停。

    用法:
        POST /api/v1/tasks/{task_id}/run-next-step

    @Author: mosliu
    """
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
    """取消当前正在运行的任务。

    用途:
        强行中断并停止正在执行的工作流任务，使任务状态流转为 "cancelled"。

    用法:
        POST /api/v1/tasks/{task_id}/cancel

    @Author: mosliu
    """
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
