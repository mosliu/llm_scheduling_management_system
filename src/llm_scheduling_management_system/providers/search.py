import json
import re
from urllib.parse import urlparse

from llm_scheduling_management_system.config_models import SearchProviderConfig
from llm_scheduling_management_system.providers.http_client import HTTPProviderClient, ProviderRequest
from llm_scheduling_management_system.providers.interfaces import SearchProvider
from llm_scheduling_management_system.providers.types import SearchHit, SearchResultBundle


SEARCH_RESULT_JSON_SHAPE = (
    '{"results":[{"title":"","url":"","content":"","releaseDate":"","author":"","sourceType":"",'
    '"publisher":"","language":"","regionHint":""}]}'
)
DEFAULT_WEB_RESEARCH_SYSTEM_PROMPT = (
    "You are a web intelligence retrieval engine for event analysis and public-opinion research. "
    "Use the web search tool to gather factual, source-attributed results. Prioritize official sources, "
    "primary sources, major media, and representative public discussion when relevant. Pay attention to "
    "publication time and freshness. Never fabricate missing metadata. Return only strict JSON with shape "
    f"{SEARCH_RESULT_JSON_SHAPE}. No markdown."
)
DEFAULT_WEB_RESEARCH_USER_PROMPT_TEMPLATE = (
    "Search the web for: {query}\n"
    "Return up to {limit} high-quality, non-duplicate results as strict JSON only.\n"
    "Each result must include title, url, content, releaseDate, author, sourceType, publisher, language, regionHint.\n"
    "Rules:\n"
    "- content must be a concise factual summary of the source, not your final analysis\n"
    "- preserve the source publication time when available\n"
    "- sourceType must be one of: official, mainstream_media, local_media, self_media, social, encyclopedia, forum, other\n"
    "- publisher should be the organization, outlet, platform, or agency name when available\n"
    "- language should be the source language when available\n"
    "- regionHint should be cn, overseas, global, or empty if unknown\n"
    "- if a field is unknown, return an empty string rather than inventing it\n"
    "- return JSON only, with no markdown fences and no prose"
)


def _extract_domain(url: str | None) -> str:
    """提取 URL 中的域名。

    用途:
        从给定的 URL 字符串中解析并返回主机域名 (netloc)，如果解析失败或 URL 为空，则返回 'unknown'。

    用法:
        domain = _extract_domain("https://example.com/path")

    @Author: mosliu
    """
    if not url:
        return "unknown"
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def _has_configured_api_key(api_key: str | None) -> bool:
    """Return whether a provider API key looks intentionally configured."""

    normalized = (api_key or "").strip().lower()
    return bool(normalized) and normalized not in {"replace-me", "your-api-key", "your_api_key", "test-key"}


def _extract_provider_error_message(response_payload) -> str:
    """Extract a concise provider error message without exposing request secrets."""

    if isinstance(response_payload, str):
        return response_payload[:500]
    if not isinstance(response_payload, dict):
        return ""
    error = response_payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or error)[:500]
    if error:
        return str(error)[:500]
    return str(response_payload.get("message") or response_payload.get("msg") or response_payload)[:500]


def _is_blank_authorization_header(value: str | None) -> bool:
    """Detect empty Authorization values that httpx rejects, such as 'Bearer '."""

    normalized = (value or "").strip().lower()
    return normalized in {"", "bearer"}


def _drop_blank_authorization_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove blank Authorization headers from user-provided extra headers."""

    cleaned = {}
    for key, value in headers.items():
        if key.lower() == "authorization" and _is_blank_authorization_header(value):
            continue
        cleaned[key] = value
    return cleaned


def _extract_inline_content(item: dict) -> tuple[str | None, str | None]:
    """Extract content returned inline by search APIs such as Firecrawl search+scrape."""

    for key, content_format in (
        ("markdown", "markdown"),
        ("raw_content", "text"),
        ("content", "text"),
        ("text", "text"),
        ("html", "html"),
    ):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value, content_format
    for nested_key in ("scrape", "scrapeResult", "scrape_result", "data"):
        nested = item.get(nested_key)
        if isinstance(nested, dict):
            content, content_format = _extract_inline_content(nested)
            if content:
                return content, content_format
    return None, None


def _render_prompt_template(template: str, *, query: str, limit: int) -> str:
    """渲染搜索提示词模板。

    用途:
        使用搜索查询词、数量限制和 JSON 结构定义填充提示词模板。如果填充失败，则返回原模板。

    用法:
        prompt = _render_prompt_template(template, query="python", limit=5)

    @Author: mosliu
    """
    try:
        return template.format(query=query, limit=limit, schema=SEARCH_RESULT_JSON_SHAPE)
    except Exception:
        return template


def _extract_text_payload(response_payload) -> str:
    """提取响应体中的文本内容。

    用途:
        从 LLM 服务返回的非结构化或流式（SSE）响应（如 OpenAI/Grok 格式的 choices 列表或 output 列表）中提取纯文本正文。

    用法:
        text = _extract_text_payload(response_payload)

    @Author: mosliu
    """
    if isinstance(response_payload, str):
        stripped = response_payload.strip()
        if stripped.startswith("data:"):
            parts: list[str] = []
            for line in response_payload.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                if payload == "[DONE]":
                    continue
                try:
                    parsed = json.loads(payload)
                except Exception:
                    continue
                choices = parsed.get("choices") or []
                for choice in choices:
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    if content:
                        parts.append(content)
                    message = choice.get("message") or {}
                    message_content = message.get("content")
                    if message_content:
                        parts.append(message_content)
            if parts:
                return "".join(parts)
        return response_payload
    if not isinstance(response_payload, dict):
        return ""

    output_text = response_payload.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text

    choices = response_payload.get("choices")
    if choices:
        try:
            return choices[0]["message"]["content"]
        except Exception:
            pass

    output = response_payload.get("output", [])
    for item in output:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if text:
                return text

    parts: list[str] = []
    for candidate in response_payload.get("candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        for part in content.get("parts", []) or []:
            if isinstance(part, dict) and part.get("text"):
                parts.append(part["text"])
    if parts:
        return "".join(parts)
    return ""


def _normalize_response_web_search_tools(tools: list[dict] | None) -> list[dict]:
    """Normalize model-embedded web-search tool definitions for Responses-style APIs."""

    normalized: list[dict] = []
    for item in tools or [{"type": "web_search"}]:
        if not isinstance(item, dict):
            continue
        tool = dict(item)
        if tool.get("type") == "web_search":
            tool.pop("name", None)
        normalized.append(tool)
    return normalized


def _collect_citation_items(value) -> list:
    """Collect citation-like objects from common OpenAI/xAI response shapes."""

    items: list = []
    if isinstance(value, dict):
        for key in ("citations", "sources", "annotations"):
            current = value.get(key)
            if isinstance(current, list):
                items.extend(current)
        for current in value.values():
            if isinstance(current, dict | list):
                items.extend(_collect_citation_items(current))
    elif isinstance(value, list):
        for current in value:
            if isinstance(current, dict | list):
                items.extend(_collect_citation_items(current))
    return items


def _citation_url_and_title(item) -> tuple[str | None, str]:
    if isinstance(item, str):
        return item, item
    if not isinstance(item, dict):
        return None, ""

    citation = item.get("url_citation") if isinstance(item.get("url_citation"), dict) else item
    url = citation.get("url") or citation.get("uri") or citation.get("link")
    title = citation.get("title") or citation.get("name") or url or ""
    return url, title


def _hits_from_citations(
    provider_name: str,
    query: str,
    response_payload,
    *,
    limit: int,
    default_source_type: str,
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    seen_urls: set[str] = set()
    for item in _collect_citation_items(response_payload):
        url, title = _citation_url_and_title(item)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        citation = item.get("url_citation") if isinstance(item, dict) and isinstance(item.get("url_citation"), dict) else item
        snippet = citation.get("snippet") or citation.get("content") or citation.get("description") if isinstance(citation, dict) else None
        hits.append(
            SearchHit(
                provider=provider_name,
                title=title,
                url=url,
                source_domain=_extract_domain(url),
                source_type=default_source_type,
                query=query,
                snippet=snippet,
                metadata={"citation": citation},
            )
        )
        if len(hits) >= limit:
            break
    return hits


def _hits_from_gemini_grounding(provider_name: str, query: str, response_payload, *, limit: int) -> list[SearchHit]:
    hits: list[SearchHit] = []
    seen_urls: set[str] = set()
    if not isinstance(response_payload, dict):
        return hits
    for candidate in response_payload.get("candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        metadata = candidate.get("groundingMetadata") or candidate.get("grounding_metadata") or {}
        queries = metadata.get("webSearchQueries") or metadata.get("web_search_queries") or []
        for chunk in metadata.get("groundingChunks") or metadata.get("grounding_chunks") or []:
            if not isinstance(chunk, dict):
                continue
            source = chunk.get("web") or chunk.get("retrievedContext") or chunk.get("retrieved_context") or {}
            url = source.get("uri") or source.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            hits.append(
                SearchHit(
                    provider=provider_name,
                    title=source.get("title") or url,
                    url=url,
                    source_domain=_extract_domain(url),
                    source_type="web_search",
                    query=query,
                    snippet=None,
                    metadata={
                        "grounding_chunk": chunk,
                        "web_search_queries": queries,
                    },
                )
            )
            if len(hits) >= limit:
                return hits
    return hits


def _parse_search_results_text(
    provider_name: str,
    query: str,
    response_text: str,
    *,
    limit: int,
    default_source_type: str,
) -> list[SearchHit]:
    """解析搜索结果文本为 SearchHit 列表。

    用途:
        将包含 JSON 字符串的文本解析为标准 SearchHit 列表，支持清理 Markdown 代码块标记（如 ```json）并进行鲁棒的正则查找。

    用法:
        hits = _parse_search_results_text("grok", "query", response_text, limit=5, default_source_type="social")

    @Author: mosliu
    """
    parsed = {"results": []}
    if isinstance(response_text, str):
        stripped = response_text.strip()
        stripped = re.sub(r"^```json\s*|\s*```$", "", stripped, flags=re.MULTILINE)
        try:
            parsed = json.loads(stripped)
        except Exception:
            match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except Exception:
                    parsed = {"results": []}

    results = parsed.get("results", []) if isinstance(parsed, dict) else []
    hits = []
    for item in results[:limit]:
        url = item.get("url")
        hits.append(
            SearchHit(
                provider=provider_name,
                title=item.get("title", ""),
                url=url,
                source_domain=_extract_domain(url),
                source_type=item.get("sourceType") or item.get("source_type") or default_source_type,
                query=query,
                published_at_utc=item.get("releaseDate") or item.get("publishedDate") or item.get("published_at_utc"),
                snippet=item.get("content") or item.get("snippet"),
                metadata={
                    "author": item.get("author"),
                    "publisher": item.get("publisher"),
                    "language": item.get("language"),
                    "region_hint": item.get("regionHint") or item.get("region_hint"),
                },
            )
        )
    return hits


class BaseConfiguredSearchProvider(SearchProvider):
    """基于配置的搜索服务提供商抽象类。

    用途:
        提供搜索请求构建、结果解析、模拟搜索执行的公共骨架实现，作为所有具体搜索提供商的基类。

    用法:
        继承自此类并实现 build_request 和 parse_response。

    @Author: mosliu
    """
    def __init__(self, config: SearchProviderConfig) -> None:
        """初始化基础搜索服务提供商。

        用途:
            存储提供商配置并初始化用于发送请求的 HTTP 客户端。

        用法:
            provider = BaseConfiguredSearchProvider(config)

        @Author: mosliu
        """
        self.config = config
        self.http_client = HTTPProviderClient(config.base_url, config.timeout_seconds)

    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key before making a real request."""

        return True

    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """构建搜索请求。

        用途:
            根据搜索词及数量限制构造 ProviderRequest 对象。子类必须实现此方法。

        用法:
            request = provider.build_request("query", limit=5)

        @Author: mosliu
        """
        raise NotImplementedError

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """解析搜索响应。

        用途:
            解析 API 响应载荷为结构化的 SearchResultBundle。子类必须实现此方法。

        用法:
            bundle = provider.parse_response("query", response_payload, limit=5)

        @Author: mosliu
        """
        raise NotImplementedError

    def _simulate_search(self, query: str, *, limit: int, request: ProviderRequest) -> SearchResultBundle:
        """执行模拟搜索。

        用途:
            在模拟模式下，根据输入的查询词和限制，构造并返回一个虚构的 SearchResultBundle，不发出实际网络请求。

        用法:
            bundle = provider._simulate_search("query", limit=5, request=request)

        @Author: mosliu
        """
        hits = [
            SearchHit(
                provider=self.config.name,
                title=f"{query} result {index + 1}",
                url=f"https://{self.config.vendor}.example.com/article-{index + 1}",
                source_domain=f"{self.config.vendor}.example.com",
                source_type="news" if index == 0 else "social",
                query=query,
                snippet=f"Simulated {self.config.vendor} snippet {index + 1}",
                metadata={
                    "vendor": self.config.vendor,
                    "provider_type": self.config.provider_type,
                    "base_url": self.config.base_url,
                },
            )
            for index in range(min(limit, 2))
        ]
        return SearchResultBundle(
            provider=self.config.name,
            hits=hits,
            request_metadata={
                "simulated": True,
                "vendor": self.config.vendor,
                "provider_type": self.config.provider_type,
                "base_url": self.config.base_url,
                "timeout_seconds": self.config.timeout_seconds,
                "limit": limit,
                "request": {
                    "method": request.method,
                    "url": request.url,
                },
            },
        )

    def search(self, query: str, *, limit: int = 10) -> SearchResultBundle:
        """执行实际搜索或模拟搜索。

        用途:
            如果配置了 simulate 模式则执行模拟搜索，否则构建并发送 HTTP 请求，最后将响应解析为 SearchResultBundle 并附带元数据。

        用法:
            bundle = provider.search("python", limit=5)

        @Author: mosliu
        """
        request = self.build_request(query, limit=limit)
        if self.config.simulate:
            return self._simulate_search(query, limit=limit, request=request)
        if self.requires_api_key() and not _has_configured_api_key(self.config.api_key):
            raise RuntimeError(f"{self.config.name} API key is not configured")
        response = self.http_client.execute(request)
        if response.status_code >= 400:
            message = _extract_provider_error_message(response.payload)
            detail = f": {message}" if message else ""
            raise RuntimeError(f"{self.config.name} search failed with HTTP {response.status_code}{detail}")
        bundle = self.parse_response(query, response.payload, limit=limit)
        bundle.request_metadata.update(
            {
                "simulated": False,
                "vendor": self.config.vendor,
                "provider_type": self.config.provider_type,
                "limit": limit,
                "request": {
                    "method": request.method,
                    "url": request.url,
                },
                "response_status_code": response.status_code,
            }
        )
        return bundle


class ExaSearchProvider(BaseConfiguredSearchProvider):
    """Exa 搜索服务提供商适配器。

    用途:
        对接 Exa.ai 的原生搜索 API。

    用法:
        provider = ExaSearchProvider(config)
        bundle = provider.search("query")

    @Author: mosliu
    """
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """构建 Exa 搜索请求。

        用途:
            构造指向 Exa 搜索 API 的 POST 请求及头部和载荷。

        用法:
            req = provider.build_request("query", limit=5)

        @Author: mosliu
        """
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/search"),
            headers={"x-api-key": self.config.api_key, **self.config.extra_headers},
            json_body={"query": query, "numResults": limit},
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """解析 Exa 搜索响应。

        用途:
            将 Exa 返回的 JSON 格式搜索结果映射为 SearchResultBundle。

        用法:
            bundle = provider.parse_response("query", response_payload)

        @Author: mosliu
        """
        results = response_payload.get("results", []) if isinstance(response_payload, dict) else []
        hits = [
            SearchHit(
                provider=self.config.name,
                title=item.get("title", ""),
                url=item.get("url"),
                source_domain=_extract_domain(item.get("url")),
                source_type="news",
                query=query,
                published_at_utc=item.get("publishedDate"),
                snippet=item.get("summary") or item.get("text"),
                metadata={"id": item.get("id"), "url": item.get("url")},
            )
            for item in results[:limit]
        ]
        return SearchResultBundle(provider=self.config.name, hits=hits)


class TavilySearchProvider(BaseConfiguredSearchProvider):
    """Tavily 搜索服务提供商适配器。

    用途:
        对接 Tavily 搜索 API。

    用法:
        provider = TavilySearchProvider(config)
        bundle = provider.search("query")

    @Author: mosliu
    """
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """构建 Tavily 搜索请求。

        用途:
            构造指向 Tavily 搜索 API 的 POST 请求及头部和载荷。

        用法:
            req = provider.build_request("query", limit=5)

        @Author: mosliu
        """
        json_body = {
            **self.config.default_options,
            "query": query,
            "max_results": limit,
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/search"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body=json_body,
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """解析 Tavily 搜索响应。

        用途:
            将 Tavily 返回的 JSON 格式搜索结果映射为 SearchResultBundle。

        用法:
            bundle = provider.parse_response("query", response_payload)

        @Author: mosliu
        """
        results = response_payload.get("results", []) if isinstance(response_payload, dict) else []
        hits = [
            SearchHit(
                provider=self.config.name,
                title=item.get("title", ""),
                url=item.get("url"),
                source_domain=_extract_domain(item.get("url")),
                source_type="news",
                query=query,
                snippet=item.get("content") or item.get("raw_content"),
                metadata={"url": item.get("url"), "score": item.get("score")},
            )
            for item in results[:limit]
        ]
        return SearchResultBundle(provider=self.config.name, hits=hits)


class FirecrawlSearchProvider(BaseConfiguredSearchProvider):
    """Firecrawl 搜索服务提供商适配器。

    用途:
        对接 Firecrawl.dev 的 v2 搜索 API。

    用法:
        provider = FirecrawlSearchProvider(config)
        bundle = provider.search("query")

    @Author: mosliu
    """
    def requires_api_key(self) -> bool:
        """Firecrawl search may be routed through keyless endpoints."""

        return False

    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """构建 Firecrawl 搜索请求。

        用途:
            构造指向 Firecrawl 搜索 API 的 POST 请求。

        用法:
            req = provider.build_request("query", limit=5)

        @Author: mosliu
        """
        json_body = {
            **self.config.default_options,
            "query": query,
            "limit": limit,
        }
        headers = _drop_blank_authorization_headers({**self.config.extra_headers})
        if _has_configured_api_key(self.config.api_key):
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/v2/search"),
            headers=headers,
            json_body=json_body,
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """解析 Firecrawl 搜索响应。

        用途:
            将 Firecrawl 返回的 JSON 数据映射为 SearchResultBundle。

        用法:
            bundle = provider.parse_response("query", response_payload)

        @Author: mosliu
        """
        data = response_payload.get("data", {}) if isinstance(response_payload, dict) else {}
        sections = [
            ("web", data.get("web", []) or []),
            ("news", data.get("news", []) or []),
            ("images", data.get("images", []) or []),
        ]
        hits: list[SearchHit] = []
        for section, results in sections:
            for item in results:
                if not isinstance(item, dict):
                    continue
                url = item.get("url") or item.get("sourceURL")
                metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
                inline_content, inline_content_format = _extract_inline_content(item)
                hits.append(
                    SearchHit(
                        provider=self.config.name,
                        title=item.get("title") or metadata.get("title") or url or "",
                        url=url,
                        source_domain=_extract_domain(url),
                        source_type=item.get("sourceType") or item.get("source_type") or section,
                        query=query,
                        published_at_utc=item.get("publishedDate") or item.get("published_at") or metadata.get("publishedDate"),
                        snippet=item.get("description") or item.get("snippet") or inline_content,
                        metadata={
                            "url": url,
                            "section": section,
                            "statusCode": metadata.get("statusCode"),
                            "metadata": metadata,
                            "inline_content_text": inline_content,
                            "inline_content_format": inline_content_format,
                            "inline_content_provider": self.config.name,
                        },
                    )
                )
                if len(hits) >= limit:
                    break
            if len(hits) >= limit:
                break
        return SearchResultBundle(
            provider=self.config.name,
            hits=hits,
            request_metadata={
                "response_id": response_payload.get("id") if isinstance(response_payload, dict) else None,
                "credits_used": response_payload.get("creditsUsed") if isinstance(response_payload, dict) else None,
                "warning": response_payload.get("warning") if isinstance(response_payload, dict) else None,
            },
        )


class TinyFishSearchProvider(BaseConfiguredSearchProvider):
    """TinyFish 搜索服务提供商适配器。

    用途:
        对接 TinyFish 搜索 API。

    用法:
        provider = TinyFishSearchProvider(config)
        bundle = provider.search("query")

    @Author: mosliu
    """
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """构建 TinyFish 搜索请求。

        用途:
            构造指向 TinyFish API 的 GET 请求，包含 URL 参数。

        用法:
            req = provider.build_request("query", limit=5)

        @Author: mosliu
        """
        return ProviderRequest(
            method="GET",
            url=self.http_client.build_url("/"),
            headers={"X-API-Key": self.config.api_key, **self.config.extra_headers},
            params={"query": query, "page": 0},
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """解析 TinyFish 搜索响应。

        用途:
            将 TinyFish 响应数据映射为 SearchResultBundle。

        用法:
            bundle = provider.parse_response("query", response_payload)

        @Author: mosliu
        """
        results = response_payload.get("results", []) if isinstance(response_payload, dict) else []
        hits = [
            SearchHit(
                provider=self.config.name,
                title=item.get("title", ""),
                url=item.get("url"),
                source_domain=item.get("site_name", "unknown"),
                source_type="news",
                query=query,
                snippet=item.get("snippet"),
                metadata={"url": item.get("url"), "position": item.get("position")},
            )
            for item in results[:limit]
        ]
        return SearchResultBundle(provider=self.config.name, hits=hits)


class BochaSearchProvider(BaseConfiguredSearchProvider):
    """Bocha Web Search API provider adapter."""

    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """Build a Bocha Web Search request."""

        json_body = {
            **self.config.default_options,
            "query": query,
            "count": limit,
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/v1/web-search"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body=json_body,
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """Parse Bocha's Bing-compatible web search response into normalized hits."""

        payload = response_payload if isinstance(response_payload, dict) else {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        web_pages = (
            data.get("webPages")
            or data.get("webpages")
            or data.get("web_pages")
            or {}
            if isinstance(data, dict)
            else {}
        )
        if isinstance(web_pages, dict):
            results = web_pages.get("value") or web_pages.get("results") or []
        else:
            results = web_pages if isinstance(web_pages, list) else []
        if not results and isinstance(data, dict):
            results = data.get("results") or data.get("value") or []

        hits: list[SearchHit] = []
        for item in results[:limit]:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("link")
            hits.append(
                SearchHit(
                    provider=self.config.name,
                    title=item.get("name") or item.get("title") or url or "",
                    url=url,
                    source_domain=_extract_domain(url),
                    source_type=item.get("sourceType") or item.get("source_type") or "web_search",
                    query=query,
                    published_at_utc=(
                        item.get("datePublished")
                        or item.get("datePublishedDisplayText")
                        or item.get("publishedDate")
                        or item.get("published_at_utc")
                    ),
                    snippet=item.get("summary") or item.get("snippet") or item.get("description"),
                    metadata={
                        "id": item.get("id"),
                        "display_url": item.get("displayUrl") or item.get("display_url"),
                        "site_name": item.get("siteName") or item.get("site_name"),
                        "site_icon": item.get("siteIcon") or item.get("site_icon"),
                        "deep_links": item.get("deepLinks") or item.get("deep_links"),
                    },
                )
            )
        return SearchResultBundle(
            provider=self.config.name,
            hits=hits,
            request_metadata={
                "code": payload.get("code"),
                "message": payload.get("msg") or payload.get("message"),
                "web_search_url": web_pages.get("webSearchUrl") if isinstance(web_pages, dict) else None,
                "total_estimated_matches": (
                    web_pages.get("totalEstimatedMatches") if isinstance(web_pages, dict) else None
                ),
            },
        )


class GrokSearchProvider(BaseConfiguredSearchProvider):
    """Grok 搜索服务提供商适配器。

    用途:
        对接 Grok 大模型及其自带的 web_search 工具进行网络检索。

    用法:
        provider = GrokSearchProvider(config)
        bundle = provider.search("query")

    @Author: mosliu
    """
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """构建 Grok 大模型及搜索工具调用请求。

        用途:
            构造发送给 Grok 聊天补全接口的 POST 请求，启用 web_search 工具并附带系统及用户提示词。

        用法:
            req = provider.build_request("query", limit=5)

        @Author: mosliu
        """
        system_prompt = self.config.default_options.get("system", DEFAULT_WEB_RESEARCH_SYSTEM_PROMPT)
        user_prompt_template = self.config.default_options.get(
            "user_prompt_template",
            DEFAULT_WEB_RESEARCH_USER_PROMPT_TEMPLATE,
        )
        user_prompt = _render_prompt_template(user_prompt_template, query=query, limit=limit)
        json_body = {
            "model": self.config.default_options.get("model", "grok-4.3"),
            "instructions": self.config.default_options.get("instructions", system_prompt),
            "input": [{"role": "user", "content": user_prompt}],
            "tools": _normalize_response_web_search_tools(self.config.default_options.get("tools")),
            **{
                key: value
                for key, value in self.config.default_options.items()
                if key not in {"model", "system", "instructions", "user_prompt_template", "tools"}
            },
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/responses"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body=json_body,
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """解析 Grok 大模型搜索响应。

        用途:
            解析 Grok 的模型响应文本，并使用 _parse_search_results_text 还原为 SearchResultBundle。

        用法:
            bundle = provider.parse_response("query", response_payload)

        @Author: mosliu
        """
        hits = _parse_search_results_text(
            self.config.name,
            query,
            _extract_text_payload(response_payload),
            limit=limit,
            default_source_type="web_search",
        )
        if not hits:
            hits = _hits_from_citations(
                self.config.name,
                query,
                response_payload,
                limit=limit,
                default_source_type="web_search",
            )
        return SearchResultBundle(
            provider=self.config.name,
            hits=hits,
            request_metadata={
                "response_id": response_payload.get("id") if isinstance(response_payload, dict) else None,
                "status": response_payload.get("status") if isinstance(response_payload, dict) else None,
            },
        )


class OpenAIWebSearchProvider(BaseConfiguredSearchProvider):
    """OpenAI 风格的 LLM web_search 提供商适配器。

    用途:
        对接兼容 OpenAI 接口规范的大模型搜索扩展（如启用 web_search 的模型），通过提示词和内置工具获取搜索结果。

    用法:
        provider = OpenAIWebSearchProvider(config)
        bundle = provider.search("query")

    @Author: mosliu
    """
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """构建 OpenAI 风格大模型搜索请求。

        用途:
            根据配置的 api_mode，构造 /chat/completions 或 /responses 的 POST 请求。

        用法:
            req = provider.build_request("query", limit=5)

        @Author: mosliu
        """
        api_mode = self.config.default_options.get("api_mode", "responses")
        system_prompt = self.config.default_options.get("system", DEFAULT_WEB_RESEARCH_SYSTEM_PROMPT)
        user_prompt_template = self.config.default_options.get(
            "user_prompt_template",
            DEFAULT_WEB_RESEARCH_USER_PROMPT_TEMPLATE,
        )
        user_prompt = _render_prompt_template(user_prompt_template, query=query, limit=limit)
        tools = _normalize_response_web_search_tools(self.config.default_options.get("tools"))

        if api_mode == "chat_completions":
            json_body = {
                "model": self.config.default_options.get("model", "gpt-5-search-api"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "web_search_options": self.config.default_options.get("web_search_options", {}),
                "stream": False,
                "temperature": self.config.default_options.get("temperature", 0),
                **{
                    key: value
                    for key, value in self.config.default_options.items()
                    if key
                    not in {
                        "api_mode",
                        "model",
                        "system",
                        "user_prompt_template",
                        "tools",
                        "web_search_options",
                        "temperature",
                    }
                },
            }
            return ProviderRequest(
                method="POST",
                url=self.http_client.build_url("/chat/completions"),
                headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
                json_body=json_body,
            )

        json_body = {
            "model": self.config.default_options.get("model", "gpt-5.5"),
            "instructions": self.config.default_options.get("instructions", system_prompt),
            "input": user_prompt,
            "tools": tools,
            "tool_choice": self.config.default_options.get("tool_choice", "required"),
            "reasoning": self.config.default_options.get("reasoning", {"effort": "low", "summary": "detailed"}),
            "max_output_tokens": self.config.default_options.get("max_output_tokens", 2500),
            **{
                key: value
                for key, value in self.config.default_options.items()
                if key
                not in {
                    "api_mode",
                    "model",
                    "system",
                    "instructions",
                    "user_prompt_template",
                    "tools",
                    "tool_choice",
                    "reasoning",
                    "max_output_tokens",
                }
            },
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/responses"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body=json_body,
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """解析 OpenAI 风格大模型搜索响应。

        用途:
            解析 OpenAI 格式模型返回的文本段并还原为 SearchResultBundle。

        用法:
            bundle = provider.parse_response("query", response_payload)

        @Author: mosliu
        """
        hits = _parse_search_results_text(
            self.config.name,
            query,
            _extract_text_payload(response_payload),
            limit=limit,
            default_source_type="web_search",
        )
        if not hits:
            hits = _hits_from_citations(
                self.config.name,
                query,
                response_payload,
                limit=limit,
                default_source_type="web_search",
            )
        return SearchResultBundle(
            provider=self.config.name,
            hits=hits,
            request_metadata={
                "response_id": response_payload.get("id") if isinstance(response_payload, dict) else None,
                "status": response_payload.get("status") if isinstance(response_payload, dict) else None,
            },
        )


class GeminiSearchProvider(BaseConfiguredSearchProvider):
    """Gemini Google Search grounding provider adapter."""

    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """Build a Gemini GenerateContent request with Google Search grounding enabled."""

        system_prompt = self.config.default_options.get("system", DEFAULT_WEB_RESEARCH_SYSTEM_PROMPT)
        user_prompt_template = self.config.default_options.get(
            "user_prompt_template",
            DEFAULT_WEB_RESEARCH_USER_PROMPT_TEMPLATE,
        )
        user_prompt = _render_prompt_template(user_prompt_template, query=query, limit=limit)
        model = self.config.default_options.get("model", "gemini-3.5-flash")
        json_body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "tools": self.config.default_options.get("tools", [{"google_search": {}}]),
            "generationConfig": self.config.default_options.get("generation_config", {"temperature": 0}),
            **{
                key: value
                for key, value in self.config.default_options.items()
                if key
                not in {
                    "model",
                    "system",
                    "user_prompt_template",
                    "tools",
                    "generation_config",
                }
            },
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url(f"/models/{model}:generateContent"),
            headers={"x-goog-api-key": self.config.api_key, **self.config.extra_headers},
            json_body=json_body,
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """Parse Gemini grounded output into normalized search hits."""

        hits = _parse_search_results_text(
            self.config.name,
            query,
            _extract_text_payload(response_payload),
            limit=limit,
            default_source_type="web_search",
        )
        if not hits:
            hits = _hits_from_gemini_grounding(self.config.name, query, response_payload, limit=limit)
        return SearchResultBundle(
            provider=self.config.name,
            hits=hits,
            request_metadata={
                "model_version": response_payload.get("modelVersion") if isinstance(response_payload, dict) else None,
                "usage_metadata": response_payload.get("usageMetadata") if isinstance(response_payload, dict) else None,
            },
        )
