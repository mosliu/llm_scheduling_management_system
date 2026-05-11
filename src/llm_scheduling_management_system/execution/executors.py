from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime

from llm_scheduling_management_system.domain.models import Artifact, StepRun, TaskRun
from llm_scheduling_management_system.execution.types import FetchInvocationRecord, LLMInvocationRecord, SearchInvocationRecord, StepExecutionResult, ToolInvocationRecord
from llm_scheduling_management_system.mcp.registry import MCPRegistry
from llm_scheduling_management_system.providers.factory import LLMProviderFactory, SearchProviderFactory
from llm_scheduling_management_system.source_registry import SourceRegistry


DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def _find_upstream_artifacts(task: TaskRun, step: StepRun) -> list[Artifact]:
    artifact_by_id = {artifact.id: artifact for artifact in task.artifacts}
    return [artifact_by_id[artifact_id] for artifact_id in step.input_artifact_refs if artifact_id in artifact_by_id]


def _first_upstream_artifact(task: TaskRun, step: StepRun) -> Artifact | None:
    artifacts = _find_upstream_artifacts(task, step)
    return artifacts[0] if artifacts else None


def _normalize_document_preview(text: str, limit: int = 220) -> str:
    collapsed = " ".join((text or "").split())
    return collapsed[:limit]


class StepExecutor(ABC):
    @abstractmethod
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        raise NotImplementedError


class SearchFanoutExecutor(StepExecutor):
    def __init__(self, search_provider_factory: SearchProviderFactory | None = None) -> None:
        self.search_provider_factory = search_provider_factory or SearchProviderFactory()
        self.source_registry = SourceRegistry()

    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        topic = task.input_payload.get("topic", "")
        time_range = task.input_payload.get("time_range", {})
        provider_names = task.options_payload.get("search_provider_names")
        providers = (
            self.search_provider_factory.build_search_providers(provider_names)
            if provider_names
            else self.search_provider_factory.build_default_search_providers()
        )
        bundles = [provider.search(topic, limit=2) for provider in providers]
        hits = []
        for bundle in bundles:
            for hit in bundle.hits:
                source_info = self.source_registry.lookup(hit.source_domain)
                hits.append(
                    {
                        "provider": hit.provider,
                        "query": hit.query,
                        "title": hit.title,
                        "source_url": hit.url or f"https://{hit.source_domain}/article-{len(hits) + 1}",
                        "source_domain": hit.source_domain,
                        "source_type": hit.source_type,
                        "region_hint": source_info["region_hint"],
                        "publisher_type": source_info["publisher_type"],
                        "snippet": hit.snippet,
                        "published_at_utc": hit.published_at_utc or time_range.get("end") or time_range.get("start"),
                    }
                )
        search_invocations = [
            SearchInvocationRecord(
                provider_name=bundle.provider,
                provider_vendor=bundle.request_metadata.get("vendor", "unknown"),
                query_text=topic,
                result_count=len(bundle.hits),
                request_metadata=bundle.request_metadata,
                response_metadata={"hit_titles": [hit.title for hit in bundle.hits]},
            )
            for bundle in bundles
        ]
        return StepExecutionResult(
            artifact_type="retrieval.search_hits",
            artifact_level="raw",
            schema_name="search_hits_bundle",
            content_json={
                "node_key": step.node_key,
                "topic": topic,
                "total_hits": len(hits),
                "hits": hits,
            },
            checkpoint_type="retrieval_search_completed",
            search_invocations=search_invocations,
        )


class FetchDocumentsExecutor(StepExecutor):
    def __init__(self, search_provider_factory: SearchProviderFactory | None = None) -> None:
        self.search_provider_factory = search_provider_factory or SearchProviderFactory()
        self.source_registry = SourceRegistry()

    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        fetch_provider_name = task.options_payload.get("fetch_provider_name")
        fetch_provider = (
            self.search_provider_factory.build_fetch_provider_by_name(fetch_provider_name)
            if fetch_provider_name
            else self.search_provider_factory.build_default_fetch_provider()
        )
        upstream = list(step.input_artifact_refs)
        if fetch_provider is None:
            return StepExecutionResult(
                artifact_type="retrieval.fetched_documents",
                artifact_level="normalized",
                schema_name="fetched_documents_bundle",
                content_json={
                    "node_key": step.node_key,
                    "task_id": task.id,
                    "documents": [],
                },
                checkpoint_type="fetch_documents_completed",
                input_artifact_ids=upstream,
            )

        docs = []
        fetch_invocations = []
        available_artifact = _first_upstream_artifact(task, step)
        hits = available_artifact.content_json.get("hits", []) if available_artifact else []
        for hit in hits:
            source_url = hit.get("source_url") or f"https://{hit.get('source_domain', 'example.com')}/"
            fetched = fetch_provider.fetch(source_url)
            source_info = self.source_registry.lookup(hit.get("source_domain", ""))
            docs.append(
                {
                    "provider": fetched.provider,
                    "url": fetched.url,
                    "canonical_url": fetched.canonical_url,
                    "title": fetched.title,
                    "author": fetched.author,
                    "language": fetched.language,
                    "source_domain": hit.get("source_domain"),
                    "source_type": hit.get("source_type"),
                    "region_hint": source_info["region_hint"],
                    "publisher_type": source_info["publisher_type"],
                    "published_at_utc": hit.get("published_at_utc"),
                    "content_text": fetched.content_text,
                    "metadata": fetched.metadata,
                }
            )
            fetch_invocations.append(
                FetchInvocationRecord(
                    provider_name=fetched.provider,
                    provider_vendor=fetched.metadata.get("vendor", "unknown"),
                    url=fetched.url,
                    title=fetched.title,
                    request_metadata={"source_url": source_url},
                    response_metadata={"simulated": fetched.metadata.get("simulated", False)},
                )
            )
        return StepExecutionResult(
            artifact_type="retrieval.fetched_documents",
            artifact_level="normalized",
            schema_name="fetched_documents_bundle",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "input_artifact_ids": upstream,
                "documents": docs,
            },
            checkpoint_type="fetch_documents_completed",
            input_artifact_ids=upstream,
            fetch_invocations=fetch_invocations,
        )


class MCPToolExecutor(StepExecutor):
    def __init__(self, registry: MCPRegistry | None = None) -> None:
        self.registry = registry or MCPRegistry()

    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        upstream = list(step.input_artifact_refs)
        server_name = task.options_payload.get("mcp_server_name", "internal_tools")
        tool_name = task.options_payload.get("mcp_tool_name", "list_docs")
        client = self.registry.build_client(server_name)
        if client is None:
            return StepExecutionResult(
                artifact_type="tool.mcp_result",
                artifact_level="derived",
                schema_name="mcp_tool_result",
                content_json={
                    "node_key": step.node_key,
                    "task_id": task.id,
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "response": {"error": "server_not_found"},
                },
                checkpoint_type="mcp_tool_completed",
                input_artifact_ids=upstream,
                tool_invocations=[
                    ToolInvocationRecord(
                        server_name=server_name,
                        tool_name=tool_name,
                        arguments_json={"topic": task.input_payload.get("topic"), "root": "docs", "pattern": "*.md"},
                        response_json={"error": "server_not_found"},
                        status="failed",
                    )
                ],
            )

        arguments = {"topic": task.input_payload.get("topic"), "task_id": task.id, "root": "docs", "pattern": "*.md"}
        result = client.call_tool(tool_name, arguments)
        return StepExecutionResult(
            artifact_type="tool.mcp_result",
            artifact_level="derived",
            schema_name="mcp_tool_result",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "server_name": result.server_name,
                "tool_name": result.tool_name,
                "response": result.response,
                "context_documents": result.response.get("result", {}).get("files", []) if isinstance(result.response, dict) else [],
            },
            checkpoint_type="mcp_tool_completed",
            input_artifact_ids=upstream,
            tool_invocations=[
                ToolInvocationRecord(
                    server_name=result.server_name,
                    tool_name=result.tool_name,
                    arguments_json=result.arguments,
                    response_json=result.response,
                    status=result.status,
                )
            ],
        )


class MergeSearchResultsExecutor(StepExecutor):
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        upstream = list(step.input_artifact_refs)
        source_artifacts = _find_upstream_artifacts(task, step)
        documents = []
        mcp_context_documents = []
        for source_artifact in source_artifacts:
            if source_artifact.schema_name == "fetched_documents_bundle":
                documents.extend(source_artifact.content_json.get("documents", []))
            if source_artifact.schema_name == "mcp_tool_result":
                mcp_context_documents.extend(source_artifact.content_json.get("context_documents", []))
        merged_documents = [
            {
                "url": item.get("canonical_url") or item.get("url"),
                "title": item.get("title"),
                "provider": item.get("provider"),
                "source_domain": item.get("source_domain"),
                "source_type": item.get("source_type"),
                "region_hint": item.get("region_hint"),
                "publisher_type": item.get("publisher_type"),
                "published_at_utc": item.get("published_at_utc"),
                "language": item.get("language"),
                "author": item.get("author"),
                "content_preview": _normalize_document_preview(item.get("content_text", "")),
            }
            for item in documents
        ]
        return StepExecutionResult(
            artifact_type="retrieval.merged_results",
            artifact_level="normalized",
            schema_name="merged_results_bundle",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "strategy": "document_merge",
                "input_artifact_ids": upstream,
                "document_count": len(merged_documents),
                "documents": merged_documents,
                "mcp_context_documents": mcp_context_documents,
            },
            checkpoint_type="retrieval_merge_completed",
            input_artifact_ids=upstream,
        )


class NormalizeAndFilterExecutor(StepExecutor):
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        policy = task.options_payload.get("source_policy", {})
        upstream = list(step.input_artifact_refs)
        source_artifact = _first_upstream_artifact(task, step)
        documents = source_artifact.content_json.get("documents", []) if source_artifact else []

        require_non_empty = policy.get("require_non_empty", True)
        include_regions = set(policy.get("include_regions", []))
        filtered = []
        for item in documents:
            if require_non_empty and not item.get("content_preview"):
                continue
            if include_regions and item.get("region_hint") not in include_regions:
                continue
            filtered.append(item)

        return StepExecutionResult(
            artifact_type="retrieval.filtered_bundle",
            artifact_level="derived",
            schema_name="filtered_retrieval_bundle",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "input_artifact_ids": upstream,
                "filter_policy": policy,
                "document_count": len(filtered),
                "documents": filtered,
            },
            checkpoint_type="retrieval_bundle_completed",
            input_artifact_ids=upstream,
        )


class ClassifyAndFilterSourcesExecutor(StepExecutor):
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        upstream = list(step.input_artifact_refs)
        source_artifact = _first_upstream_artifact(task, step)
        documents = source_artifact.content_json.get("documents", []) if source_artifact else []
        mcp_context_documents = source_artifact.content_json.get("mcp_context_documents", []) if source_artifact else []

        by_region: dict[str, int] = {}
        by_publisher: dict[str, int] = {}
        by_source_type: dict[str, int] = {}
        for item in documents:
            by_region[item.get("region_hint", "unknown")] = by_region.get(item.get("region_hint", "unknown"), 0) + 1
            by_publisher[item.get("publisher_type", "unknown")] = by_publisher.get(item.get("publisher_type", "unknown"), 0) + 1
            by_source_type[item.get("source_type", "unknown")] = by_source_type.get(item.get("source_type", "unknown"), 0) + 1

        return StepExecutionResult(
            artifact_type="analysis.classified_sources",
            artifact_level="derived",
            schema_name="classified_source_bundle",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "input_artifact_ids": upstream,
                "document_count": len(documents),
                "by_region": by_region,
                "by_publisher_type": by_publisher,
                "by_source_type": by_source_type,
                "documents": documents,
                "mcp_context_documents": mcp_context_documents,
            },
            checkpoint_type="classification_completed",
            input_artifact_ids=upstream,
        )


class ExtractOfficialResponsesExecutor(StepExecutor):
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        upstream = list(step.input_artifact_refs)
        source_artifact = _first_upstream_artifact(task, step)
        documents = source_artifact.content_json.get("documents", []) if source_artifact else []
        official_candidates = []
        for item in documents:
            text = " ".join(
                [
                    item.get("title") or "",
                    item.get("content_preview") or "",
                    item.get("content_text") or "",
                ]
            )
            if any(keyword in text for keyword in ["官方", "通报", "回应", "发布", "应急", "政府", "调查"]):
                official_candidates.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source_domain": item.get("source_domain"),
                        "published_at_utc": item.get("published_at_utc"),
                        "response_excerpt": _normalize_document_preview(item.get("content_text", ""), 320),
                    }
                )
        return StepExecutionResult(
            artifact_type="analysis.official_responses",
            artifact_level="derived",
            schema_name="official_response_bundle",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "input_artifact_ids": upstream,
                "official_responses": official_candidates,
            },
            checkpoint_type="official_response_completed",
            input_artifact_ids=upstream,
        )


class SegmentPublicOpinionExecutor(StepExecutor):
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        upstream = list(step.input_artifact_refs)
        source_artifacts = _find_upstream_artifacts(task, step)
        merged_documents = []
        official_responses = []
        for artifact in source_artifacts:
            if artifact.schema_name == "merged_results_bundle":
                merged_documents = artifact.content_json.get("documents", [])
            if artifact.schema_name == "official_response_bundle":
                official_responses = artifact.content_json.get("official_responses", [])

        media_viewpoints = []
        public_viewpoints = []
        for item in merged_documents:
            preview = item.get("content_preview") or ""
            if item.get("source_type") == "social":
                public_viewpoints.append(
                    {
                        "title": item.get("title"),
                        "source_domain": item.get("source_domain"),
                        "viewpoint": preview,
                    }
                )
            else:
                media_viewpoints.append(
                    {
                        "title": item.get("title"),
                        "source_domain": item.get("source_domain"),
                        "viewpoint": preview,
                    }
                )

        if not public_viewpoints:
            public_viewpoints.append(
                {
                    "title": "网民观点样本不足",
                    "source_domain": "system",
                    "viewpoint": "当前可用检索结果以媒体报道和资讯站点为主，缺少充足的原生社交评论样本，应谨慎解释网民观点。",
                }
            )

        return StepExecutionResult(
            artifact_type="analysis.public_opinion_segments",
            artifact_level="derived",
            schema_name="public_opinion_segments",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "input_artifact_ids": upstream,
                "media_viewpoints": media_viewpoints[:10],
                "public_viewpoints": public_viewpoints[:10],
                "official_responses": official_responses,
            },
            checkpoint_type="opinion_segmentation_completed",
            input_artifact_ids=upstream,
        )


class ExtractEventTimeExecutor(StepExecutor):
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        upstream = list(step.input_artifact_refs)
        source_artifact = _first_upstream_artifact(task, step)
        documents = source_artifact.content_json.get("documents", []) if source_artifact else []
        candidates = []
        for item in documents:
            preview = item.get("content_preview") or item.get("content_text") or ""
            match = DATE_PATTERN.search(preview)
            candidates.append(
                {
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "event_time": match.group(1) if match else item.get("published_at_utc"),
                    "source_domain": item.get("source_domain"),
                }
            )
        return StepExecutionResult(
            artifact_type="timeline.event_time_candidates",
            artifact_level="derived",
            schema_name="event_time_candidates",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "input_artifact_ids": upstream,
                "candidates": candidates,
            },
            checkpoint_type="timeline_time_extract_completed",
            input_artifact_ids=upstream,
        )


class BuildTimelineExecutor(StepExecutor):
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        upstream = list(step.input_artifact_refs)
        source_artifact = _first_upstream_artifact(task, step)
        candidates = source_artifact.content_json.get("candidates", []) if source_artifact else []
        timeline = sorted(candidates, key=lambda item: item.get("event_time") or "")
        return StepExecutionResult(
            artifact_type="timeline.timeline_bundle",
            artifact_level="derived",
            schema_name="timeline_bundle",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "input_artifact_ids": upstream,
                "timeline": timeline,
            },
            checkpoint_type="timeline_bundle_completed",
            input_artifact_ids=upstream,
        )


class LLMReportExecutor(StepExecutor):
    def __init__(self, llm_provider_factory: LLMProviderFactory | None = None, profile_name: str = "advanced_reasoning_cn") -> None:
        self.llm_provider_factory = llm_provider_factory or LLMProviderFactory()
        self.profile_name = profile_name

    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        topic = task.input_payload.get("topic", "unknown topic")
        upstream = list(step.input_artifact_refs)
        source_artifacts = _find_upstream_artifacts(task, step)
        profile_name = task.options_payload.get("llm_profile_name", self.profile_name)
        llm = self.llm_provider_factory.build_profile_provider(profile_name)

        evidence_lines = []
        official_responses = []
        media_viewpoints = []
        public_viewpoints = []
        timeline = []
        for artifact in source_artifacts:
            documents = artifact.content_json.get("documents")
            if documents:
                for item in documents[:5]:
                    evidence_lines.append(
                        f"- {item.get('title') or item.get('url')} | {item.get('source_domain')} | {item.get('content_preview', '')[:160]}"
                    )
            maybe_timeline = artifact.content_json.get("timeline")
            if maybe_timeline:
                timeline = maybe_timeline
            if artifact.schema_name == "official_response_bundle":
                official_responses = artifact.content_json.get("official_responses", [])
            if artifact.schema_name == "public_opinion_segments":
                media_viewpoints = artifact.content_json.get("media_viewpoints", [])
                public_viewpoints = artifact.content_json.get("public_viewpoints", [])

        if step.node_key == "generate_public_opinion_report":
            prompt_text = (
                f"你是一名舆情分析师。请围绕主题《{topic}》生成一份中文舆情报告。\n"
                "报告必须包含以下章节：\n"
                "1. 事件概况\n"
                "2. 舆情脉络\n"
                "3. 官方回应信息\n"
                "4. 媒体观点总结\n"
                "5. 网民观点总结\n"
                "6. 舆情启示\n"
                "7. 深度舆情分析结论\n\n"
                f"时间线候选：{timeline[:8]}\n"
                f"官方回应：{official_responses[:8]}\n"
                f"媒体观点：{media_viewpoints[:8]}\n"
                f"网民观点：{public_viewpoints[:8]}\n"
                "补充证据：\n" + ("\n".join(evidence_lines) if evidence_lines else "- 暂无补充证据")
            )
        else:
            prompt_text = (
                f"Task node: {step.node_key}\n"
                f"Topic: {topic}\n"
                f"Use the following evidence to produce a concise structured report.\n"
                f"Evidence:\n" + ("\n".join(evidence_lines) if evidence_lines else "- No upstream evidence available.")
            )
        generated_text = llm.generate(prompt_text)
        return StepExecutionResult(
            artifact_type="report.generated",
            artifact_level="final",
            schema_name="generated_report",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "topic": topic,
                "input_artifact_ids": upstream,
                "message": generated_text,
            },
            content_text=generated_text,
            checkpoint_type="report_generation_completed",
            input_artifact_ids=upstream,
            llm_invocations=[
                LLMInvocationRecord(
                    provider_name=getattr(llm, "provider", getattr(llm, "provider_name", None)).name
                    if hasattr(getattr(llm, "provider", None), "name")
                    else getattr(llm, "provider_name", "mock_llm_default"),
                    provider_type=getattr(getattr(llm, "provider", None), "provider_type", "mock"),
                    profile_name=profile_name,
                    model_name=getattr(getattr(llm, "profile", None), "model", "mock-model"),
                    prompt_text=prompt_text,
                    response_text=generated_text,
                    request_metadata={"step_node_key": step.node_key},
                    response_metadata={"simulated": getattr(getattr(llm, "provider", None), "simulate", True)},
                )
            ],
        )


class DefaultStepExecutor(StepExecutor):
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        return StepExecutionResult(
            artifact_type=f"{step.node_key}_result",
            artifact_level="derived",
            schema_name=step.node_key,
            content_json={
                "task_id": task.id,
                "node_key": step.node_key,
                "title": step.title,
                "message": f"Simulated execution completed for {step.node_key}.",
            },
            input_artifact_ids=list(step.input_artifact_refs),
        )
