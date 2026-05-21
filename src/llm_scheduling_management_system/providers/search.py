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

    choices = response_payload.get("choices")
    if choices:
        try:
            return choices[0]["message"]["content"]
        except Exception:
            pass

    output = response_payload.get("output", [])
    for item in output:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                return text
    return ""


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
        response = self.http_client.execute(request)
        bundle = self.parse_response(query, response.payload, limit=limit)
        bundle.request_metadata.update(
            {
                "simulated": False,
                "vendor": self.config.vendor,
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
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        """构建 Firecrawl 搜索请求。

        用途:
            构造指向 Firecrawl 搜索 API 的 POST 请求。

        用法:
            req = provider.build_request("query", limit=5)

        @Author: mosliu
        """
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/v2/search"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body={"query": query, "limit": limit},
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        """解析 Firecrawl 搜索响应。

        用途:
            将 Firecrawl 返回的 JSON 数据映射为 SearchResultBundle。

        用法:
            bundle = provider.parse_response("query", response_payload)

        @Author: mosliu
        """
        web_results = response_payload.get("data", {}).get("web", []) if isinstance(response_payload, dict) else []
        hits = [
            SearchHit(
                provider=self.config.name,
                title=item.get("title", ""),
                url=item.get("url"),
                source_domain=_extract_domain(item.get("url")),
                source_type="news",
                query=query,
                snippet=item.get("description") or item.get("markdown"),
                metadata={"url": item.get("url"), "statusCode": item.get("metadata", {}).get("statusCode")},
            )
            for item in web_results[:limit]
        ]
        return SearchResultBundle(provider=self.config.name, hits=hits)


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
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": _render_prompt_template(user_prompt_template, query=query, limit=limit),
            },
        ]
        json_body = {
            "model": self.config.default_options.get("model", "grok-4.20-beta"),
            "messages": messages,
            "tools": self.config.default_options.get("tools", [{"type": "web_search", "name": "web_search"}]),
            "temperature": self.config.default_options.get("temperature", 0),
            **{
                key: value
                for key, value in self.config.default_options.items()
                if key not in {"model", "system", "user_prompt_template", "tools", "temperature"}
            },
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/chat/completions"),
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
        return SearchResultBundle(provider=self.config.name, hits=hits)


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
        tools = self.config.default_options.get("tools", [{"type": "web_search"}])

        if api_mode == "chat_completions":
            json_body = {
                "model": self.config.default_options.get("model", "gpt-5.5"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "tools": tools,
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
        return SearchResultBundle(provider=self.config.name, hits=hits)
