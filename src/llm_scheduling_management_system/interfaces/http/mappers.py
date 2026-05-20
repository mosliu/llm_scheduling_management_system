from llm_scheduling_management_system.domain.models import Artifact, Checkpoint, StepRun, TaskRun, WorkflowTemplate
from llm_scheduling_management_system.schemas.tasks import (
    ArtifactDetailResponse,
    ArtifactLineageEdgeResponse,
    ArtifactReferenceResponse,
    CheckpointDetailResponse,
    CheckpointReferenceResponse,
    ConfiguredLLMProfileResponse,
    ConfiguredLLMProviderResponse,
    ConfiguredProviderResponse,
    DocumentResponse,
    MCPServerResponse,
    SourceRegistryEntryResponse,
    FetchInvocationResponse,
    LLMInvocationResponse,
    SearchHitResponse,
    SearchInvocationResponse,
    StepDetailResponse,
    StepRunResponse,
    TaskDetailResponse,
    TaskEventResponse,
    TaskSummaryResponse,
    ToolInvocationResponse,
    WorkflowTemplateDetailResponse,
    WorkflowTemplateResponse,
    WorkflowTemplateStepBlueprintResponse,
)


def map_task_summary(task: TaskRun) -> TaskSummaryResponse:
    current_step = None
    current_step_run_id = task.current_step_run_id
    if current_step_run_id:
        matching = next((step for step in task.step_runs if step.id == current_step_run_id), None)
        if matching:
            current_step = matching.node_key

    return TaskSummaryResponse(
        task_id=task.id,
        template_id=task.template_id,
        template_version=task.template_version,
        status=task.status,
        input_payload=task.input_payload,
        options_payload=task.options_payload,
        progress=task.progress_percent,
        planned_step_count=task.planned_step_count,
        completed_step_count=task.completed_step_count,
        current_step=current_step,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        ended_at=task.ended_at,
    )


def map_task_detail(task: TaskRun) -> TaskDetailResponse:
    summary = map_task_summary(task)
    steps = [
        StepRunResponse(
            step_run_id=step.id,
            node_key=step.node_key,
            title=step.title,
            status=step.status,
            progress=step.progress_percent,
            input_artifact_refs=step.input_artifact_refs,
            artifact_ids=[artifact.id for artifact in step.artifacts],
            cache_hit=step.cache_hit,
            error_code=step.error_code,
            error_message=step.error_message,
        )
        for step in sorted(task.step_runs, key=lambda item: item.sequence_no)
    ]
    artifacts = [
        ArtifactReferenceResponse(
            artifact_id=artifact.id,
            artifact_type=artifact.artifact_type,
            artifact_level=artifact.artifact_level,
        )
        for artifact in task.artifacts
    ]
    checkpoints = [
        CheckpointReferenceResponse(
            checkpoint_id=checkpoint.id,
            based_on_step_run_id=checkpoint.step_run_id,
            artifact_ids=checkpoint.artifact_refs,
        )
        for checkpoint in task.checkpoints
    ]
    return TaskDetailResponse(
        **summary.model_dump(),
        steps=steps,
        artifacts=artifacts,
        available_checkpoints=checkpoints,
    )


def map_template(template: WorkflowTemplate) -> WorkflowTemplateResponse:
    return WorkflowTemplateResponse(
        template_id=template.id,
        name=template.name,
        category=template.category,
        description=template.description,
        latest_version=template.latest_version,
    )


def map_template_detail(template: WorkflowTemplate, blueprint: list[dict]) -> WorkflowTemplateDetailResponse:
    return WorkflowTemplateDetailResponse(
        template_id=template.id,
        name=template.name,
        category=template.category,
        description=template.description,
        latest_version=template.latest_version,
        steps=[
            WorkflowTemplateStepBlueprintResponse(
                node_key=item["node_key"],
                node_type=item["node_type"],
                title=item["title"],
                sequence_no=index + 1,
            )
            for index, item in enumerate(blueprint)
        ],
    )


def map_step_detail(step: StepRun) -> StepDetailResponse:
    return StepDetailResponse(
        step_run_id=step.id,
        task_run_id=step.task_run_id,
        node_key=step.node_key,
        node_type=step.node_type,
        title=step.title,
        status=step.status,
        progress=step.progress_percent,
        attempt_no=step.attempt_no,
        sequence_no=step.sequence_no,
        input_artifact_refs=step.input_artifact_refs,
        input_snapshot=step.input_snapshot,
        output_summary=step.output_summary,
        cache_key=step.cache_key,
        cache_hit=step.cache_hit,
        provider_snapshot=step.provider_snapshot,
        profile_snapshot=step.profile_snapshot,
        artifact_ids=[artifact.id for artifact in step.artifacts],
        error_code=step.error_code,
        error_message=step.error_message,
    )


def map_artifact_detail(artifact: Artifact) -> ArtifactDetailResponse:
    return ArtifactDetailResponse(
        artifact_id=artifact.id,
        task_run_id=artifact.task_run_id,
        step_run_id=artifact.step_run_id,
        artifact_type=artifact.artifact_type,
        artifact_level=artifact.artifact_level,
        schema_name=artifact.schema_name,
        schema_version=artifact.schema_version,
        reusable_flag=artifact.reusable_flag,
        content_json=artifact.content_json,
        content_text=artifact.content_text,
        blob_uri=artifact.blob_uri,
        content_hash=artifact.content_hash,
    )


def map_checkpoint_detail(checkpoint: Checkpoint) -> CheckpointDetailResponse:
    return CheckpointDetailResponse(
        checkpoint_id=checkpoint.id,
        task_run_id=checkpoint.task_run_id,
        step_run_id=checkpoint.step_run_id,
        node_key=checkpoint.node_key,
        checkpoint_type=checkpoint.checkpoint_type,
        state_ref=checkpoint.state_ref,
        artifact_refs=checkpoint.artifact_refs,
        expires_at=checkpoint.expires_at,
    )


def map_artifact_lineage_edge(lineage) -> ArtifactLineageEdgeResponse:
    return ArtifactLineageEdgeResponse(
        lineage_id=lineage.id,
        from_artifact_id=lineage.from_artifact_id,
        to_artifact_id=lineage.to_artifact_id,
        relation_type=lineage.relation_type,
    )


def map_search_invocation(invocation) -> SearchInvocationResponse:
    return SearchInvocationResponse(
        invocation_id=invocation.id,
        provider_name=invocation.provider_name,
        provider_vendor=invocation.provider_vendor,
        query_text=invocation.query_text,
        result_count=invocation.result_count,
        request_metadata=invocation.request_metadata,
        response_metadata=invocation.response_metadata,
    )


def map_fetch_invocation(invocation) -> FetchInvocationResponse:
    return FetchInvocationResponse(
        invocation_id=invocation.id,
        provider_name=invocation.provider_name,
        provider_vendor=invocation.provider_vendor,
        url=invocation.url,
        title=invocation.title,
        request_metadata=invocation.request_metadata,
        response_metadata=invocation.response_metadata,
    )


def map_tool_invocation(invocation) -> ToolInvocationResponse:
    return ToolInvocationResponse(
        invocation_id=invocation.id,
        server_name=invocation.server_name,
        tool_name=invocation.tool_name,
        arguments_json=invocation.arguments_json,
        response_json=invocation.response_json,
        status=invocation.status,
    )


def map_llm_invocation(invocation) -> LLMInvocationResponse:
    return LLMInvocationResponse(
        invocation_id=invocation.id,
        provider_name=invocation.provider_name,
        provider_type=invocation.provider_type,
        profile_name=invocation.profile_name,
        model_name=invocation.model_name,
        prompt_text=invocation.prompt_text,
        response_text=invocation.response_text,
        request_metadata=invocation.request_metadata,
        response_metadata=invocation.response_metadata,
    )


def map_configured_provider(provider) -> ConfiguredProviderResponse:
    return ConfiguredProviderResponse(
        name=provider.name,
        provider_type=provider.provider_type,
        vendor=provider.vendor,
        enabled=provider.enabled,
        base_url=getattr(provider, "base_url", None),
    )


def map_configured_llm_provider(provider) -> ConfiguredLLMProviderResponse:
    return ConfiguredLLMProviderResponse(
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
    )


def map_configured_llm_profile(profile) -> ConfiguredLLMProfileResponse:
    return ConfiguredLLMProfileResponse(
        name=profile.name,
        provider=profile.provider,
        model=profile.model,
        structured_output=profile.structured_output,
        fallback_profiles=profile.fallback_profiles,
    )


def map_source_registry_entry(entry) -> SourceRegistryEntryResponse:
    return SourceRegistryEntryResponse(
        domain=entry.domain,
        region_hint=entry.region_hint,
        publisher_type=entry.publisher_type,
        language=entry.language,
        official=entry.official,
    )


def map_mcp_server(entry) -> MCPServerResponse:
    return MCPServerResponse(
        name=entry.name,
        transport=entry.transport,
        enabled=entry.enabled,
        simulate=entry.simulate,
        command=entry.command,
        args=entry.args,
        url=entry.url,
    )


def map_task_event(event) -> TaskEventResponse:
    return TaskEventResponse(
        event_id=event.id,
        task_run_id=event.task_run_id,
        step_run_id=event.step_run_id,
        event_type=event.event_type,
        status=event.status,
        payload=event.payload,
        created_at=event.created_at,
    )


def map_search_hit(hit) -> SearchHitResponse:
    return SearchHitResponse(
        search_hit_id=hit.id,
        provider_name=hit.provider_name,
        query_text=hit.query_text,
        title=hit.title,
        source_domain=hit.source_domain,
        source_type=hit.source_type,
        region_hint=hit.region_hint,
        publisher_type=hit.publisher_type,
        snippet=hit.snippet,
        published_at_utc=hit.published_at_utc,
        metadata=hit.extra_metadata,
    )


def map_document(document) -> DocumentResponse:
    return DocumentResponse(
        document_id=document.id,
        provider_name=document.provider_name,
        url=document.url,
        canonical_url=document.canonical_url,
        title=document.title,
        author=document.author,
        language=document.language,
        source_domain=document.source_domain,
        source_type=document.source_type,
        region_hint=document.region_hint,
        publisher_type=document.publisher_type,
        published_at_utc=document.published_at_utc,
        content_text=document.content_text,
        content_hash=document.content_hash,
        metadata=document.extra_metadata,
    )
