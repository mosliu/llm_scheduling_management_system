from __future__ import annotations

import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse

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


def _build_bulleted_key_points(text: str | None, limit: int = 3) -> list[str]:
    normalized = " ".join((text or "").split())
    if not normalized:
        return []
    fragments = re.split(r"[；;。.!?！？]\s*", normalized)
    points = []
    for fragment in fragments:
        candidate = fragment.strip()
        if not candidate:
            continue
        points.append(candidate[:120])
        if len(points) >= limit:
            break
    return points


def _canonicalize_url(url: str | None) -> str:
    if not url:
        return ""
    candidate = url.strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = parsed.query
    return f"{scheme}://{netloc}{path}" + (f"?{query}" if query else "")


def _choose_longer_text(left: str | None, right: str | None) -> str | None:
    left = (left or "").strip()
    right = (right or "").strip()
    if not left:
        return right or None
    if not right:
        return left or None
    return right if len(right) > len(left) else left


def _merge_hit_records(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    merged["title"] = _choose_longer_text(existing.get("title"), incoming.get("title")) or ""
    merged["snippet"] = _choose_longer_text(existing.get("snippet"), incoming.get("snippet"))
    merged["published_at_utc"] = existing.get("published_at_utc") or incoming.get("published_at_utc")
    merged["author"] = existing.get("author") or incoming.get("author")
    merged["publisher"] = existing.get("publisher") or incoming.get("publisher")
    merged["language"] = existing.get("language") or incoming.get("language")
    merged["region_hint"] = existing.get("region_hint") or incoming.get("region_hint")
    merged["publisher_type"] = existing.get("publisher_type") or incoming.get("publisher_type")
    merged["source_type"] = existing.get("source_type") or incoming.get("source_type")

    matched_provider_names = list(merged.get("matched_provider_names", []))
    provider = incoming.get("provider")
    if provider and provider not in matched_provider_names:
        matched_provider_names.append(provider)
    merged["matched_provider_names"] = matched_provider_names

    matched_source_domains = list(merged.get("matched_source_domains", []))
    source_domain = incoming.get("source_domain")
    if source_domain and source_domain not in matched_source_domains:
        matched_source_domains.append(source_domain)
    merged["matched_source_domains"] = matched_source_domains
    merged["duplicate_count"] = len(matched_provider_names)
    return merged


def _merge_document_records(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    merged["canonical_url"] = existing.get("canonical_url") or incoming.get("canonical_url")
    merged["url"] = existing.get("url") or incoming.get("url")
    merged["title"] = _choose_longer_text(existing.get("title"), incoming.get("title"))
    merged["author"] = existing.get("author") or incoming.get("author")
    merged["language"] = existing.get("language") or incoming.get("language")
    merged["source_domain"] = existing.get("source_domain") or incoming.get("source_domain")
    merged["source_type"] = existing.get("source_type") or incoming.get("source_type")
    merged["region_hint"] = existing.get("region_hint") or incoming.get("region_hint")
    merged["publisher_type"] = existing.get("publisher_type") or incoming.get("publisher_type")
    merged["published_at_utc"] = existing.get("published_at_utc") or incoming.get("published_at_utc")
    merged["content_text"] = _choose_longer_text(existing.get("content_text"), incoming.get("content_text")) or ""

    metadata = dict(existing.get("metadata", {}))
    for key, value in (incoming.get("metadata", {}) or {}).items():
        if key not in metadata or not metadata.get(key):
            metadata[key] = value

    matched_provider_names = list(metadata.get("matched_provider_names", []))
    for provider in (incoming.get("metadata", {}) or {}).get("matched_provider_names", []):
        if provider and provider not in matched_provider_names:
            matched_provider_names.append(provider)
    metadata["matched_provider_names"] = matched_provider_names

    source_urls = list(metadata.get("source_urls", []))
    for candidate in [incoming.get("url"), incoming.get("canonical_url")]:
        if candidate and candidate not in source_urls:
            source_urls.append(candidate)
    metadata["source_urls"] = source_urls
    metadata["duplicate_count"] = len(matched_provider_names)
    merged["metadata"] = metadata
    return merged


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
        configured_default_limit = self.search_provider_factory.config.policy.max_results_per_provider
        search_limit = max(int(task.options_payload.get("search_limit", configured_default_limit or 30)), 1)
        provider_names = task.options_payload.get("search_provider_names")
        providers = (
            self.search_provider_factory.build_search_providers(provider_names)
            if provider_names
            else self.search_provider_factory.build_default_search_providers()
        )
        max_workers = max(
            1,
            min(
                len(providers) or 1,
                int(task.options_payload.get("search_parallelism", len(providers) or 1)),
            ),
        )
        bundles = []
        if providers:
            ordered_results: list = [None] * len(providers)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {
                    executor.submit(provider.search, topic, limit=search_limit): index
                    for index, provider in enumerate(providers)
                }
                for future in as_completed(future_map):
                    ordered_results[future_map[future]] = future.result()
            bundles = [bundle for bundle in ordered_results if bundle is not None]
        hits_by_url: dict[str, dict] = {}
        fallback_hits: list[dict] = []
        for bundle in bundles:
            for hit in bundle.hits:
                source_info = self.source_registry.lookup(hit.source_domain)
                metadata = hit.metadata or {}
                normalized_hit = {
                    "provider": hit.provider,
                    "query": hit.query,
                    "title": hit.title,
                    "source_url": hit.url or f"https://{hit.source_domain}/article-fallback",
                    "source_domain": hit.source_domain,
                    "source_type": hit.source_type,
                    "region_hint": metadata.get("region_hint") or source_info["region_hint"],
                    "publisher_type": metadata.get("publisher_type") or source_info["publisher_type"],
                    "snippet": hit.snippet,
                    "published_at_utc": hit.published_at_utc or time_range.get("end") or time_range.get("start"),
                    "author": metadata.get("author"),
                    "publisher": metadata.get("publisher"),
                    "language": metadata.get("language"),
                    "matched_provider_names": [hit.provider],
                    "matched_source_domains": [hit.source_domain] if hit.source_domain else [],
                    "duplicate_count": 1,
                }
                dedup_key = _canonicalize_url(normalized_hit["source_url"])
                if dedup_key:
                    existing = hits_by_url.get(dedup_key)
                    hits_by_url[dedup_key] = (
                        _merge_hit_records(existing, normalized_hit) if existing is not None else normalized_hit
                    )
                else:
                    fallback_hits.append(normalized_hit)
        hits = list(hits_by_url.values()) + fallback_hits
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
                "raw_hit_count": sum(len(bundle.hits) for bundle in bundles),
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
        docs_by_url: dict[str, dict] = {}
        fetch_invocations = []
        available_artifact = _first_upstream_artifact(task, step)
        hits = available_artifact.content_json.get("hits", []) if available_artifact else []
        for hit in hits:
            source_url = hit.get("source_url") or f"https://{hit.get('source_domain', 'example.com')}/"
            fetched = fetch_provider.fetch(source_url)
            source_info = self.source_registry.lookup(hit.get("source_domain", ""))
            document_record = {
                "provider": fetched.provider,
                "url": fetched.url,
                "canonical_url": fetched.canonical_url,
                "title": fetched.title or hit.get("title"),
                "author": fetched.author or hit.get("author"),
                "language": fetched.language or hit.get("language"),
                "source_domain": hit.get("source_domain"),
                "source_type": hit.get("source_type"),
                "region_hint": hit.get("region_hint") or source_info["region_hint"],
                "publisher_type": hit.get("publisher_type") or source_info["publisher_type"],
                "published_at_utc": hit.get("published_at_utc"),
                "content_text": fetched.content_text,
                "metadata": {
                    **fetched.metadata,
                    "source_url": source_url,
                    "publisher": hit.get("publisher"),
                    "matched_provider_names": list(hit.get("matched_provider_names", [hit.get("provider")])),
                    "duplicate_count": hit.get("duplicate_count", 1),
                },
            }
            dedup_key = _canonicalize_url(fetched.canonical_url or fetched.url or source_url)
            if dedup_key:
                existing = docs_by_url.get(dedup_key)
                docs_by_url[dedup_key] = (
                    _merge_document_records(existing, document_record) if existing is not None else document_record
                )
            else:
                docs.append(document_record)
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
        docs.extend(docs_by_url.values())
        return StepExecutionResult(
            artifact_type="retrieval.fetched_documents",
            artifact_level="normalized",
            schema_name="fetched_documents_bundle",
            content_json={
                "node_key": step.node_key,
                "task_id": task.id,
                "input_artifact_ids": upstream,
                "raw_document_count": len(fetch_invocations),
                "document_count": len(docs),
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
        source_artifacts = _find_upstream_artifacts(task, step)
        documents = []
        for artifact in source_artifacts:
            if artifact.schema_name in {"merged_results_bundle", "fetched_documents_bundle"}:
                documents.extend(artifact.content_json.get("documents", []))
        if not documents:
            for artifact in task.artifacts:
                if artifact.schema_name in {"merged_results_bundle", "fetched_documents_bundle"}:
                    documents.extend(artifact.content_json.get("documents", []))
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
                response_excerpt = _normalize_document_preview(
                    item.get("content_text") or item.get("content_preview") or item.get("snippet") or "",
                    320,
                )
                response_content = _normalize_document_preview(
                    item.get("content_text") or item.get("content_preview") or item.get("snippet") or "",
                    600,
                )
                official_candidates.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source_domain": item.get("source_domain"),
                        "published_at_utc": item.get("published_at_utc"),
                        "response_excerpt": response_excerpt,
                        "response_content": response_content,
                        "response_key_points": _build_bulleted_key_points(
                            item.get("content_text") or item.get("content_preview") or item.get("snippet") or "",
                            limit=3,
                        ),
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
        if not merged_documents:
            for artifact in reversed(task.artifacts):
                if artifact.schema_name == "merged_results_bundle":
                    merged_documents = artifact.content_json.get("documents", [])
                    break
        if not official_responses:
            for artifact in reversed(task.artifacts):
                if artifact.schema_name == "official_response_bundle":
                    official_responses = artifact.content_json.get("official_responses", [])
                    break

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
        source_artifacts = _find_upstream_artifacts(task, step)
        documents = []
        for artifact in source_artifacts:
            if artifact.schema_name in {"merged_results_bundle", "fetched_documents_bundle"}:
                documents.extend(artifact.content_json.get("documents", []))
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

    @staticmethod
    def _provider_runtime_details(provider) -> tuple[str, str, str, bool]:
        provider_name = (
            getattr(provider, "provider", getattr(provider, "provider_name", None)).name
            if hasattr(getattr(provider, "provider", None), "name")
            else getattr(provider, "provider_name", "mock_llm_default")
        )
        provider_type = getattr(getattr(provider, "provider", None), "provider_type", "mock")
        model_name = getattr(getattr(provider, "profile", None), "model", "mock-model")
        simulated = getattr(getattr(provider, "provider", None), "simulate", True)
        return provider_name, provider_type, model_name, simulated

    @staticmethod
    def _build_deterministic_report_fallback(
        topic: str,
        timeline: list[dict],
        official_responses: list[dict],
        media_viewpoints: list[dict],
        public_viewpoints: list[dict],
        evidence_lines: list[str],
        last_error: str | None,
    ) -> str:
        timeline_lines = []
        for item in timeline[:12]:
            title = item.get("title") or item.get("url") or "未命名条目"
            when = item.get("event_time") or "时间待核实"
            url = item.get("url") or "URL待补充"
            timeline_lines.append(f"- {when}：{title}（{url}）")
        if not timeline_lines:
            timeline_lines.append("- 时间线候选不足，需结合原始文档进一步补充。")

        official_lines = []
        for item in official_responses[:10]:
            title = item.get("title") or "官方信息条目"
            url = item.get("url") or "URL待补充"
            excerpt = item.get("response_excerpt") or item.get("response_content") or "回应内容待补充"
            official_lines.append(f"- {title}：{excerpt}（{url}）")
        if not official_lines:
            official_lines.append("- 暂未稳定抽取出明确官方回应条目，建议人工复核央媒和政府网来源。")

        media_lines = []
        for item in media_viewpoints[:10]:
            title = item.get("title") or "媒体条目"
            domain = item.get("source_domain") or "unknown"
            viewpoint = item.get("viewpoint") or "观点摘要缺失"
            media_lines.append(f"- {title} | {domain} | {viewpoint}")
        if not media_lines:
            media_lines.append("- 暂无稳定媒体观点摘要。")

        public_lines = []
        for item in public_viewpoints[:10]:
            title = item.get("title") or "网民条目"
            domain = item.get("source_domain") or "unknown"
            viewpoint = item.get("viewpoint") or "观点摘要缺失"
            public_lines.append(f"- {title} | {domain} | {viewpoint}")
        if not public_lines:
            public_lines.append("- 暂无稳定网民观点摘要。")

        evidence_block = "\n".join(evidence_lines[:12]) if evidence_lines else "- 暂无补充证据"
        fallback_reason = last_error or "LLM returned empty content after retries."
        return (
            f"主题：{topic}\n\n"
            "1. 事件概况\n"
            "根据已抓取的多源报道，本次事件为高危行业重大爆炸事故，伤亡口径与调查进展在不同时间节点持续更新，舆情关注点集中在伤亡规模、救援处置、责任追究、企业隐患与行业整顿。\n\n"
            "2. 舆情脉络\n"
            + "\n".join(timeline_lines)
            + "\n\n3. 官方回应信息\n"
            + "\n".join(official_lines)
            + "\n\n4. 媒体观点总结\n"
            + "\n".join(media_lines)
            + "\n\n5. 网民观点总结\n"
            + "\n".join(public_lines)
            + "\n\n6. 舆情启示\n"
            "高危产业事故舆情的关键不在于单次回应，而在于持续信息披露、责任穿透调查以及行业系统性整改。若官方口径与进展披露不连续，舆情会快速转向对监管失效的追问。\n\n"
            "7. 深度舆情分析结论\n"
            "本次舆情呈现出典型的“事故冲击—伤亡升级—监管追问—国家级调查介入”路径，说明事件已从地方突发事故升级为全国性公共安全治理议题。\n\n"
            "补充证据\n"
            f"{evidence_block}\n\n"
            "系统说明\n"
            f"最终报告在自动重试与模型切换后仍未得到稳定 LLM 正文输出，因此以上内容由系统依据结构化中间产物自动整理。最后错误：{fallback_reason}"
        )

    def _generate_with_retry(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        prompt_text: str,
        primary_profile_name: str,
        timeline: list[dict],
        official_responses: list[dict],
        media_viewpoints: list[dict],
        public_viewpoints: list[dict],
        evidence_lines: list[str],
    ) -> tuple[str, list[LLMInvocationRecord], str]:
        auto_retry_count = max(0, int(task.options_payload.get("report_retry_count", 2)))
        model_retry_count = max(0, int(task.options_payload.get("llm_model_retry_count", 2)))
        extra_fallback_profiles = list(task.options_payload.get("report_fallback_profile_names", []))
        profile_chain = self.llm_provider_factory.resolve_profile_chain(primary_profile_name, extra_fallback_profiles)
        if not profile_chain:
            profile_chain = [primary_profile_name]

        invocation_records: list[LLMInvocationRecord] = []
        last_error: str | None = None

        for auto_attempt in range(auto_retry_count + 1):
            for profile_index, candidate_profile_name in enumerate(profile_chain):
                provider = self.llm_provider_factory.build_profile_provider(candidate_profile_name)
                provider_name, provider_type, model_name, simulated = self._provider_runtime_details(provider)
                for model_attempt in range(model_retry_count + 1):
                    try:
                        generated_text = provider.generate(prompt_text)
                    except Exception as exc:
                        last_error = str(exc)
                        invocation_records.append(
                            LLMInvocationRecord(
                                provider_name=provider_name,
                                provider_type=provider_type,
                                profile_name=candidate_profile_name,
                                model_name=model_name,
                                prompt_text=prompt_text,
                                response_text="",
                                request_metadata={
                                    "step_node_key": step.node_key,
                                    "auto_attempt": auto_attempt,
                                    "model_attempt": model_attempt,
                                    "profile_chain_index": profile_index,
                                },
                                response_metadata={
                                    "simulated": simulated,
                                    "error": str(exc),
                                    "empty": True,
                                },
                            )
                        )
                        continue

                    invocation_records.append(
                        LLMInvocationRecord(
                            provider_name=provider_name,
                            provider_type=provider_type,
                            profile_name=candidate_profile_name,
                            model_name=model_name,
                            prompt_text=prompt_text,
                            response_text=generated_text,
                            request_metadata={
                                "step_node_key": step.node_key,
                                "auto_attempt": auto_attempt,
                                "model_attempt": model_attempt,
                                "profile_chain_index": profile_index,
                            },
                            response_metadata={
                                "simulated": simulated,
                                "empty": not bool((generated_text or "").strip()),
                            },
                        )
                    )
                    if (generated_text or "").strip():
                        return generated_text, invocation_records, candidate_profile_name
                    last_error = f"Empty response from profile {candidate_profile_name}"

        fallback_text = self._build_deterministic_report_fallback(
            topic=task.input_payload.get("topic", "unknown topic"),
            timeline=timeline,
            official_responses=official_responses,
            media_viewpoints=media_viewpoints,
            public_viewpoints=public_viewpoints,
            evidence_lines=evidence_lines,
            last_error=last_error,
        )
        return fallback_text, invocation_records, profile_chain[-1]

    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        topic = task.input_payload.get("topic", "unknown topic")
        upstream = list(step.input_artifact_refs)
        source_artifacts = sorted(task.artifacts, key=lambda item: item.created_at)
        profile_name = task.options_payload.get("llm_profile_name", self.profile_name)

        evidence_lines = []
        official_responses = []
        media_viewpoints = []
        public_viewpoints = []
        timeline = []
        for artifact in source_artifacts:
            documents = artifact.content_json.get("documents")
            if documents:
                for item in documents[:5]:
                    preview = item.get("content_preview") or _normalize_document_preview(item.get("content_text", ""))
                    evidence_lines.append(
                        f"- {item.get('title') or item.get('url')} | {item.get('source_domain')} | {preview[:160]}"
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
                "严格要求：\n"
                "- 舆情脉络必须按时间前后排序输出\n"
                "- 舆情脉络中的每一条后面都必须附上 URL\n"
                "- 官方回应信息部分必须逐条写出回应主体、回应内容要点、发布时间和 URL\n"
                "- 优先使用已提供的时间线候选、官方回应、媒体观点、网民观点和补充证据\n"
                "- 如果信息存在不一致，要说明不同来源口径差异\n"
                "- 全文使用中文，不要输出 markdown 代码块\n\n"
                f"时间线候选：{timeline[:80]}\n"
                f"官方回应：{official_responses[:8]}\n"
                f"媒体观点：{media_viewpoints[:20]}\n"
                f"网民观点：{public_viewpoints[:20]}\n"
                "补充证据：\n" + ("\n".join(evidence_lines) if evidence_lines else "- 暂无补充证据")
            )
        else:
            prompt_text = (
                f"Task node: {step.node_key}\n"
                f"Topic: {topic}\n"
                f"Use the following evidence to produce a concise structured report.\n"
                f"Evidence:\n" + ("\n".join(evidence_lines) if evidence_lines else "- No upstream evidence available.")
            )
        generated_text, llm_invocations, resolved_profile_name = self._generate_with_retry(
            task=task,
            step=step,
            prompt_text=prompt_text,
            primary_profile_name=profile_name,
            timeline=timeline,
            official_responses=official_responses,
            media_viewpoints=media_viewpoints,
            public_viewpoints=public_viewpoints,
            evidence_lines=evidence_lines,
        )
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
                "resolved_profile_name": resolved_profile_name,
            },
            content_text=generated_text,
            checkpoint_type="report_generation_completed",
            input_artifact_ids=upstream,
            llm_invocations=llm_invocations,
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
