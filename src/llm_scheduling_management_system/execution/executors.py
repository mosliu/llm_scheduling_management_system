from __future__ import annotations

import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse

from llm_scheduling_management_system.domain.models import Artifact, StepRun, TaskRun
from llm_scheduling_management_system.execution.types import FetchInvocationRecord, LLMInvocationRecord, SearchInvocationRecord, StepExecutionResult, ToolInvocationRecord
from llm_scheduling_management_system.mcp.registry import MCPRegistry
from llm_scheduling_management_system.providers.factory import LLMProviderFactory, SearchProviderFactory
from llm_scheduling_management_system.source_registry import SourceRegistry


DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
CHINA_REGION_HINT = "cn"
SEARCH_API_PROVIDER_TYPES = {"search_with_inline_content", "search_only"}
MODEL_EMBEDDED_SEARCH_PROVIDER_TYPE = "model_embedded_search"
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "spm",
    "src",
}


def _find_upstream_artifacts(task: TaskRun, step: StepRun) -> list[Artifact]:
    """寻找当前步骤的上游生成物（Artifacts）。

    用途:
        根据步骤中关联的上游生成物引用 ID，从任务的全部生成物列表中查找并返回对应的实体对象。

    用法:
        artifacts = _find_upstream_artifacts(task, step)

    @Author: mosliu
    """
    artifact_by_id = {artifact.id: artifact for artifact in task.artifacts}
    return [artifact_by_id[artifact_id] for artifact_id in step.input_artifact_refs if artifact_id in artifact_by_id]


def _first_upstream_artifact(task: TaskRun, step: StepRun) -> Artifact | None:
    """获取当前步骤的第一个上游生成物。

    用途:
        辅助方法，用于快速获取步骤所需的第一个上游输入实体。

    用法:
        artifact = _first_upstream_artifact(task, step)

    @Author: mosliu
    """
    artifacts = _find_upstream_artifacts(task, step)
    return artifacts[0] if artifacts else None


def _normalize_document_preview(text: str, limit: int = 220) -> str:
    """规范化并截取文档预览文本。

    用途:
        将文本中的多余空白字符合并，并截断至指定长度，主要用于生成文摘或预览。

    用法:
        preview = _normalize_document_preview(long_text, limit=150)

    @Author: mosliu
    """
    collapsed = " ".join((text or "").split())
    return collapsed[:limit]


def _build_bulleted_key_points(text: str | None, limit: int = 3) -> list[str]:
    """提取文本关键点列表。

    用途:
        对输入的文本进行断句，并提取前 limit 个非空语句作为项目符号关键点。

    用法:
        points = _build_bulleted_key_points(content_text, limit=3)

    @Author: mosliu
    """
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
    """规范化 URL。

    用途:
        统一 URL 的格式（如小写协议和域名，去除末尾斜杠等），便于进行去重对比。

    用法:
        clean_url = _canonicalize_url(raw_url)

    @Author: mosliu
    """
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


def _search_dedup_url_key(url: str | None) -> str:
    """生成搜索阶段跨渠道 URL 去重键，忽略常见追踪参数。"""

    if not url:
        return ""
    candidate = url.strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    query = urlencode(sorted(query_pairs), doseq=True)
    return f"{scheme}://{netloc}{path}" + (f"?{query}" if query else "")


def _choose_longer_text(left: str | None, right: str | None) -> str | None:
    """选择较长的文本。

    用途:
        比较两个字符串的长度，返回非空且长度较长的那一个，常用于多源数据字段合并时的信息最大化。

    用法:
        best_title = _choose_longer_text(title_a, title_b)

    @Author: mosliu
    """
    left = (left or "").strip()
    right = (right or "").strip()
    if not left:
        return right or None
    if not right:
        return left or None
    return right if len(right) > len(left) else left


def _search_provider_priority(provider_type: str | None) -> int:
    """搜索命中主记录优先级，数值越小越优先。"""

    if provider_type in SEARCH_API_PROVIDER_TYPES:
        return 0
    if provider_type == MODEL_EMBEDDED_SEARCH_PROVIDER_TYPE:
        return 1
    return 2


def _prefer_incoming_hit(existing: dict, incoming: dict) -> bool:
    """判断重复搜索命中合并时是否应将 incoming 作为主记录。"""

    existing_priority = _search_provider_priority(existing.get("provider_type"))
    incoming_priority = _search_provider_priority(incoming.get("provider_type"))
    return incoming_priority < existing_priority


def _source_policy_from_task(task: TaskRun) -> dict:
    """从任务选项中读取来源过滤策略。"""

    policy = task.options_payload.get("source_policy", {})
    return policy if isinstance(policy, dict) else {}


def _source_policy_include_regions(policy: dict) -> set[str]:
    """解析来源策略中的地域白名单。"""

    if any(
        bool(policy.get(key))
        for key in ("keep_china_sources_only", "china_sources_only", "only_china_sources")
    ):
        return {CHINA_REGION_HINT}
    include_regions = policy.get("include_regions", [])
    if isinstance(include_regions, str):
        include_regions = [include_regions]
    return {str(region).strip().lower() for region in include_regions if str(region).strip()}


def _source_policy_filter_metadata(policy: dict) -> dict:
    """生成可写入 artifact 的来源过滤摘要。"""

    include_regions = sorted(_source_policy_include_regions(policy))
    return {
        "include_regions": include_regions,
        "keep_china_sources_only": include_regions == [CHINA_REGION_HINT],
    }


def _filter_items_by_source_policy(items: list[dict], policy: dict) -> tuple[list[dict], int]:
    """按来源地域策略过滤记录。"""

    include_regions = _source_policy_include_regions(policy)
    if not include_regions:
        return list(items), 0
    filtered = [
        item
        for item in items
        if str(item.get("region_hint") or "").strip().lower() in include_regions
    ]
    return filtered, len(items) - len(filtered)


def _document_dedup_key(document: dict) -> str:
    """生成文档级去重键。"""

    url_key = _canonicalize_url(document.get("canonical_url") or document.get("url"))
    if url_key:
        return url_key
    title = (document.get("title") or "").strip().lower()
    return f"title:{title}" if title else ""


def _deduplicate_document_records(documents: list[dict]) -> list[dict]:
    """按 URL/标题对文档记录去重，保留首次出现的记录。"""

    deduplicated = []
    seen_keys: set[str] = set()
    for document in documents:
        key = _document_dedup_key(document)
        if key:
            if key in seen_keys:
                continue
            seen_keys.add(key)
        deduplicated.append(document)
    return deduplicated


def _merge_hit_records(existing: dict, incoming: dict) -> dict:
    """合并搜索命中（Hit）记录。

    用途:
        在去重过程中，合并两个相同 URL 的命中条目，保留更长（信息更全）的标题、摘要等，并聚合匹配到的提供商和域名。

    用法:
        merged_hit = _merge_hit_records(existing_hit, new_hit)

    @Author: mosliu
    """
    primary = incoming if _prefer_incoming_hit(existing, incoming) else existing
    secondary = existing if primary is incoming else incoming
    merged = dict(primary)
    merged["title"] = _choose_longer_text(primary.get("title"), secondary.get("title")) or ""
    merged["snippet"] = _choose_longer_text(primary.get("snippet"), secondary.get("snippet"))
    merged["published_at_utc"] = primary.get("published_at_utc") or secondary.get("published_at_utc")
    merged["author"] = primary.get("author") or secondary.get("author")
    merged["publisher"] = primary.get("publisher") or secondary.get("publisher")
    merged["language"] = primary.get("language") or secondary.get("language")
    merged["region_hint"] = primary.get("region_hint") or secondary.get("region_hint")
    merged["publisher_type"] = primary.get("publisher_type") or secondary.get("publisher_type")
    merged["source_type"] = primary.get("source_type") or secondary.get("source_type")
    merged["provider_type"] = primary.get("provider_type") or secondary.get("provider_type")
    merged["inline_content_text"] = _choose_longer_text(
        primary.get("inline_content_text"),
        secondary.get("inline_content_text"),
    )
    merged["inline_content_format"] = primary.get("inline_content_format") or secondary.get("inline_content_format")
    merged["inline_content_provider"] = primary.get("inline_content_provider") or secondary.get("inline_content_provider")

    matched_provider_names = list(merged.get("matched_provider_names", []))
    for provider in [existing.get("provider"), incoming.get("provider")]:
        if provider and provider not in matched_provider_names:
            matched_provider_names.append(provider)
    merged["matched_provider_names"] = matched_provider_names

    matched_provider_types = list(merged.get("matched_provider_types", []))
    for provider_type in [existing.get("provider_type"), incoming.get("provider_type")]:
        if provider_type and provider_type not in matched_provider_types:
            matched_provider_types.append(provider_type)
    merged["matched_provider_types"] = matched_provider_types

    matched_source_domains = list(merged.get("matched_source_domains", []))
    for source_domain in [existing.get("source_domain"), incoming.get("source_domain")]:
        if source_domain and source_domain not in matched_source_domains:
            matched_source_domains.append(source_domain)
    merged["matched_source_domains"] = matched_source_domains

    source_urls = list(merged.get("matched_source_urls", []))
    for source_url in [existing.get("source_url"), incoming.get("source_url")]:
        if source_url and source_url not in source_urls:
            source_urls.append(source_url)
    merged["matched_source_urls"] = source_urls
    merged["duplicate_count"] = len(matched_provider_names)
    return merged


def _merge_document_records(existing: dict, incoming: dict) -> dict:
    """合并已获取的文档记录。

    用途:
        在抓取去重过程中，合并两个相同 URL 的抓取文档记录，最大化保留正文内容和元数据。

    用法:
        merged_doc = _merge_document_records(existing_doc, new_doc)

    @Author: mosliu
    """
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
    """步骤执行器基类。

    用途:
        定义所有具体工作流步骤执行器的抽象接口。

    用法:
        作为一个抽象基类被继承，具体执行器需要实现 `execute` 方法。

    @Author: mosliu
    """
    @abstractmethod
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行该步骤的具体逻辑。

        用途:
            抽象方法，定义单步任务执行的接口，由具体的执行器子类实现。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
        raise NotImplementedError


class SearchFanoutExecutor(StepExecutor):
    """多引擎并行检索执行器。

    用途:
        用于并行调用多个搜索服务提供商检索相关的主题文章，并对检索结果进行 URL 规范化和初步去重合并。

    用法:
        executor = SearchFanoutExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def __init__(self, search_provider_factory: SearchProviderFactory | None = None) -> None:
        """初始化多引擎并行检索执行器。

        用途:
            初始化搜索工厂和来源网站元数据注册表。

        用法:
            在创建 SearchFanoutExecutor 实例时传入可选的工厂。

        @Author: mosliu
        """
        self.search_provider_factory = search_provider_factory or SearchProviderFactory()
        self.source_registry = SourceRegistry()

    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行多引擎并行检索与结果合并去重。

        用途:
            获取搜索词和引擎配置，并行执行检索，调用 `_canonicalize_url` 和 `_merge_hit_records` 合并检索结果。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
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
            bundle_provider_type = bundle.request_metadata.get("provider_type", "")
            for hit in bundle.hits:
                source_info = self.source_registry.lookup(hit.source_domain)
                metadata = hit.metadata or {}
                provider_type = metadata.get("provider_type") or bundle_provider_type
                normalized_hit = {
                    "provider": hit.provider,
                    "provider_type": provider_type,
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
                    "matched_provider_types": [provider_type] if provider_type else [],
                    "matched_source_domains": [hit.source_domain] if hit.source_domain else [],
                    "matched_source_urls": [hit.url] if hit.url else [],
                    "duplicate_count": 1,
                }
                if metadata.get("inline_content_text"):
                    normalized_hit["inline_content_text"] = metadata.get("inline_content_text")
                    normalized_hit["inline_content_format"] = metadata.get("inline_content_format")
                    normalized_hit["inline_content_provider"] = metadata.get("inline_content_provider") or hit.provider
                dedup_key = _search_dedup_url_key(normalized_hit["source_url"])
                if dedup_key:
                    normalized_hit["search_dedup_url_key"] = dedup_key
                    existing = hits_by_url.get(dedup_key)
                    hits_by_url[dedup_key] = (
                        _merge_hit_records(existing, normalized_hit) if existing is not None else normalized_hit
                    )
                else:
                    fallback_hits.append(normalized_hit)
        unfiltered_hits = list(hits_by_url.values()) + fallback_hits
        source_policy = _source_policy_from_task(task)
        hits, filtered_out_hit_count = _filter_items_by_source_policy(unfiltered_hits, source_policy)
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
                "filtered_out_hit_count": filtered_out_hit_count,
                "source_filter_applied": filtered_out_hit_count > 0,
                "source_filter_policy": _source_policy_filter_metadata(source_policy),
                "hits": hits,
            },
            checkpoint_type="retrieval_search_completed",
            search_invocations=search_invocations,
        )


class FetchDocumentsExecutor(StepExecutor):
    """文档正文抓取执行器。

    用途:
        针对上游检索得到的网页链接，调用网页抓取服务提取网页内容（正文、作者等），并再次按 canonical_url 进行去重和合并。

    用法:
        executor = FetchDocumentsExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def __init__(self, search_provider_factory: SearchProviderFactory | None = None) -> None:
        """初始化文档正文抓取执行器。

        用途:
            配置抓取所需的搜索提供商工厂和来源网站元数据注册表。

        用法:
            实例化 FetchDocumentsExecutor 时，可指定自定义工厂。

        @Author: mosliu
        """
        self.search_provider_factory = search_provider_factory or SearchProviderFactory()
        self.source_registry = SourceRegistry()

    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行文档正文提取和去重。

        用途:
            从上游生成物中获取 URL 列表，调用网页抓取服务获取文本内容，并合并重复项。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
        fetch_provider_name = task.options_payload.get("fetch_provider_name")
        fetch_provider = (
            self.search_provider_factory.build_fetch_provider_by_name(fetch_provider_name)
            if fetch_provider_name
            else self.search_provider_factory.build_default_fetch_provider()
        )
        upstream = list(step.input_artifact_refs)
        docs = []
        docs_by_url: dict[str, dict] = {}
        fetch_invocations = []
        inline_document_count = 0
        fetch_skipped_count = 0
        available_artifact = _first_upstream_artifact(task, step)
        hits = available_artifact.content_json.get("hits", []) if available_artifact else []
        source_policy = _source_policy_from_task(task)
        hits, filtered_out_hit_count = _filter_items_by_source_policy(hits, source_policy)
        for hit in hits:
            source_url = hit.get("source_url") or f"https://{hit.get('source_domain', 'example.com')}/"
            source_info = self.source_registry.lookup(hit.get("source_domain", ""))
            inline_content = (hit.get("inline_content_text") or "").strip()
            if inline_content:
                document_record = {
                    "provider": hit.get("inline_content_provider") or hit.get("provider"),
                    "url": source_url,
                    "canonical_url": source_url,
                    "title": hit.get("title"),
                    "author": hit.get("author"),
                    "language": hit.get("language"),
                    "source_domain": hit.get("source_domain"),
                    "source_type": hit.get("source_type"),
                    "region_hint": hit.get("region_hint") or source_info["region_hint"],
                    "publisher_type": hit.get("publisher_type") or source_info["publisher_type"],
                    "published_at_utc": hit.get("published_at_utc"),
                    "content_text": inline_content,
                    "metadata": {
                        "source_url": source_url,
                        "publisher": hit.get("publisher"),
                        "matched_provider_names": list(hit.get("matched_provider_names", [hit.get("provider")])),
                        "duplicate_count": hit.get("duplicate_count", 1),
                        "inline_content": True,
                        "inline_content_format": hit.get("inline_content_format"),
                        "fetch_skipped": True,
                    },
                }
                inline_document_count += 1
                fetch_skipped_count += 1
                dedup_key = _canonicalize_url(document_record.get("canonical_url") or document_record.get("url"))
                if dedup_key:
                    existing = docs_by_url.get(dedup_key)
                    docs_by_url[dedup_key] = (
                        _merge_document_records(existing, document_record) if existing is not None else document_record
                    )
                else:
                    docs.append(document_record)
                continue

            if fetch_provider is None:
                fetch_skipped_count += 1
                continue

            fetched = fetch_provider.fetch(source_url)
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
                "inline_document_count": inline_document_count,
                "fetch_skipped_count": fetch_skipped_count,
                "document_count": len(docs),
                "filtered_out_hit_count": filtered_out_hit_count,
                "source_filter_applied": filtered_out_hit_count > 0,
                "source_filter_policy": _source_policy_filter_metadata(source_policy),
                "documents": docs,
            },
            checkpoint_type="fetch_documents_completed",
            input_artifact_ids=upstream,
            fetch_invocations=fetch_invocations,
        )


class MCPToolExecutor(StepExecutor):
    """MCP 工具执行器。

    用途:
        用于调用外部 Model Context Protocol (MCP) 服务器提供的工具，获取特定上下文信息（如本地文档、参考文件等）。

    用法:
        executor = MCPToolExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def __init__(self, registry: MCPRegistry | None = None) -> None:
        """初始化 MCP 工具执行器。

        用途:
            配置用于构建 MCP 客户端的注册表对象。

        用法:
            实例化 MCPToolExecutor 时可传入自定义 MCP 注册表。

        @Author: mosliu
        """
        self.registry = registry or MCPRegistry()

    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行 MCP 工具调用。

        用途:
            根据配置构建客户端，调用指定的 MCP 工具，并将返回的结果格式化为步骤执行结果。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
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
    """检索结果合并执行器。

    用途:
        合并来自不同渠道的数据生成物（如已抓取的网络文档和 MCP 工具返回的本地上下文文档），生成统一的合并结果集。

    用法:
        executor = MergeSearchResultsExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行上游数据生成物的合并。

        用途:
            遍历上游生成物，提取网络文档和 MCP 文档，对其格式化并进行文本规范化预览。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
        upstream = list(step.input_artifact_refs)
        source_artifacts = _find_upstream_artifacts(task, step)
        documents = []
        mcp_context_documents = []
        for source_artifact in source_artifacts:
            if source_artifact.schema_name == "fetched_documents_bundle":
                documents.extend(source_artifact.content_json.get("documents", []))
            if source_artifact.schema_name == "mcp_tool_result":
                mcp_context_documents.extend(source_artifact.content_json.get("context_documents", []))
        source_policy = _source_policy_from_task(task)
        documents, filtered_out_document_count = _filter_items_by_source_policy(documents, source_policy)
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
                "filtered_out_document_count": filtered_out_document_count,
                "source_filter_applied": filtered_out_document_count > 0,
                "source_filter_policy": _source_policy_filter_metadata(source_policy),
                "documents": merged_documents,
                "mcp_context_documents": mcp_context_documents,
            },
            checkpoint_type="retrieval_merge_completed",
            input_artifact_ids=upstream,
        )


class NormalizeAndFilterExecutor(StepExecutor):
    """规范化与过滤执行器。

    用途:
        根据配置的源策略（如要求非空正文、限制特定地域等）对上游文档进行过滤筛选。

    用法:
        executor = NormalizeAndFilterExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行规范化与过滤。

        用途:
            基于配置过滤无效或不需要的文档记录。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
        policy = _source_policy_from_task(task)
        upstream = list(step.input_artifact_refs)
        source_artifact = _first_upstream_artifact(task, step)
        documents = source_artifact.content_json.get("documents", []) if source_artifact else []

        require_non_empty = policy.get("require_non_empty", True)
        include_regions = _source_policy_include_regions(policy)
        filtered = []
        filtered_out_document_count = 0
        source_filtered_out_document_count = 0
        for item in documents:
            if require_non_empty and not item.get("content_preview"):
                filtered_out_document_count += 1
                continue
            if include_regions and str(item.get("region_hint") or "").strip().lower() not in include_regions:
                filtered_out_document_count += 1
                source_filtered_out_document_count += 1
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
                "filtered_out_document_count": filtered_out_document_count,
                "source_filtered_out_document_count": source_filtered_out_document_count,
                "source_filter_applied": source_filtered_out_document_count > 0,
                "source_filter_policy": _source_policy_filter_metadata(policy),
                "documents": filtered,
            },
            checkpoint_type="retrieval_bundle_completed",
            input_artifact_ids=upstream,
        )


class ClassifyAndFilterSourcesExecutor(StepExecutor):
    """源分类与统计执行器。

    用途:
        对上游文档进行多维度统计（如地域分布、出版物类型、源类型），辅助生成分析报告。

    用法:
        executor = ClassifyAndFilterSourcesExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行文档源的统计与维度分析。

        用途:
            统计不同地域、发布类型、源类型下的文档数量。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
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
    """官方回应提取执行器。

    用途:
        从检索到的所有文档中识别并提取带有官方/政府/调查等关键字的公告或通报。

    用法:
        executor = ExtractOfficialResponsesExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行官方回应提取。

        用途:
            分析文档标题与内容，对符合官方通报特征的文档生成摘要与要点。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
        upstream = list(step.input_artifact_refs)
        source_artifacts = _find_upstream_artifacts(task, step)
        documents = []
        for artifact in source_artifacts:
            if artifact.schema_name in {"merged_results_bundle", "fetched_documents_bundle"}:
                documents.extend(artifact.content_json.get("documents", []))
        if not documents:
            for schema_name in ["merged_results_bundle", "fetched_documents_bundle"]:
                for artifact in reversed(task.artifacts):
                    if artifact.schema_name == schema_name:
                        documents.extend(artifact.content_json.get("documents", []))
                        break
                if documents:
                    break
        documents = _deduplicate_document_records(documents)
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
    """舆情观点分段执行器。

    用途:
        对上游合并的文档和官方回应进行分类，区分媒体观点和网民/社交媒体观点，提供结构化舆情输入。

    用法:
        executor = SegmentPublicOpinionExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行舆情观点分类与切片。

        用途:
            将文档区分为社会化媒体（网民观点）与其他媒体，格式化为舆情分析所需的数据集。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
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
    """事件发生时间提取执行器。

    用途:
        利用正则表达式或元数据，从已获取文档的文本预览中识别并提取事件相关候选时间戳。

    用法:
        executor = ExtractEventTimeExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行候选事件时间戳提取。

        用途:
            遍历文档并通过正则匹配识别年份时间节点，生成时间线候选集。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
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
    """时间线构建执行器。

    用途:
        对上游提取出来的所有候选事件时间节点进行排序，构建按时间顺序排列的事件脉络/时间线。

    用法:
        executor = BuildTimelineExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行时间线构建与排序。

        用途:
            从上游获取时间候选，按事件发生时间升序排列。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
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
    """大模型报告生成执行器。

    用途:
        根据舆情分析的结构化数据（时间线、官方回应、舆情观点等），构建提示词并调用大语言模型（LLM）生成最终报告。

    用法:
        executor = LLMReportExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def __init__(self, llm_provider_factory: LLMProviderFactory | None = None, profile_name: str = "advanced_reasoning_cn") -> None:
        """初始化大模型报告生成执行器。

        用途:
            配置 LLM 厂商工厂和默认的配置模型标识符。

        用法:
            实例化 LLMReportExecutor 时可指定自定义工厂和默认配置模板。

        @Author: mosliu
        """
        self.llm_provider_factory = llm_provider_factory or LLMProviderFactory()
        self.profile_name = profile_name

    @staticmethod
    def _provider_runtime_details(provider) -> tuple[str, str, str, bool]:
        """获取服务提供商运行时信息。

        用途:
            辅助方法，用于提取 LLM Provider 的名称、类型、具体使用的模型名以及是否处于模拟状态。

        用法:
            name, type_str, model, simulated = LLMReportExecutor._provider_runtime_details(provider)

        @Author: mosliu
        """
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
    def _provider_http_exchange(provider) -> tuple[dict, dict]:
        """获取最近一次 HTTP 请求与响应报文快照。

        用途:
            辅助方法，用于获取 provider 内部记录的上一次网络请求与应答快照。

        用法:
            req, resp = LLMReportExecutor._provider_http_exchange(provider)

        @Author: mosliu
        """
        request_snapshot = getattr(provider, "last_request_snapshot", {}) or {}
        response_snapshot = getattr(provider, "last_response_snapshot", {}) or {}
        return request_snapshot, response_snapshot

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
        """构建确定性报告备用文本。

        用途:
            在 LLM 多次重试生成失败时，通过已整理的结构化中间数据（时间线、舆情切片等），降级自动生成一份确定性的基础舆情报告。

        用法:
            report_text = LLMReportExecutor._build_deterministic_report_fallback(...)

        @Author: mosliu
        """
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
        """执行带有重试和降级策略的报告生成。

        用途:
            根据配置的重试次数、备用模型链，在生成失败或返回空值时进行自动重试和模型轮转，全部失败时降级生成确定性报告。

        用法:
            text, records, final_profile = self._generate_with_retry(...)

        @Author: mosliu
        """
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
                        request_snapshot, response_snapshot = self._provider_http_exchange(provider)
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
                                    "http_request": request_snapshot,
                                },
                                response_metadata={
                                    "simulated": simulated,
                                    "error": str(exc),
                                    "empty": True,
                                    "http_response": response_snapshot,
                                },
                            )
                        )
                        continue

                    request_snapshot, response_snapshot = self._provider_http_exchange(provider)
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
                                "http_request": request_snapshot,
                            },
                            response_metadata={
                                "simulated": simulated,
                                "empty": not bool((generated_text or "").strip()),
                                "http_response": response_snapshot,
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
        """执行报告生成任务。

        用途:
            从任务的全部生成物中聚合所需信息，拼装提示词，调用大语言模型，并返回包含生成报告和 LLM 调用日志的结果。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
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
    """默认步骤执行器。

    用途:
        用于对未匹配到特定执行器的节点进行模拟执行。

    用法:
        executor = DefaultStepExecutor()
        result = executor.execute(task, step)

    @Author: mosliu
    """
    def execute(self, task: TaskRun, step: StepRun) -> StepExecutionResult:
        """执行模拟步骤逻辑。

        用途:
            返回一个包含模拟完成信息的生成物，避免流程中断。

        用法:
            result = executor.execute(task, step)

        @Author: mosliu
        """
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
