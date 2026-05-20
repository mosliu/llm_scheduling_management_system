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
    if not url:
        return "unknown"
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def _render_prompt_template(template: str, *, query: str, limit: int) -> str:
    try:
        return template.format(query=query, limit=limit, schema=SEARCH_RESULT_JSON_SHAPE)
    except Exception:
        return template


def _extract_text_payload(response_payload) -> str:
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
    def __init__(self, config: SearchProviderConfig) -> None:
        self.config = config
        self.http_client = HTTPProviderClient(config.base_url, config.timeout_seconds)

    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        raise NotImplementedError

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        raise NotImplementedError

    def _simulate_search(self, query: str, *, limit: int, request: ProviderRequest) -> SearchResultBundle:
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
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/search"),
            headers={"x-api-key": self.config.api_key, **self.config.extra_headers},
            json_body={"query": query, "numResults": limit},
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
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
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
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
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/v2/search"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body={"query": query, "limit": limit},
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
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
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
        return ProviderRequest(
            method="GET",
            url=self.http_client.build_url("/"),
            headers={"X-API-Key": self.config.api_key, **self.config.extra_headers},
            params={"query": query, "page": 0},
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
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
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
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
        hits = _parse_search_results_text(
            self.config.name,
            query,
            _extract_text_payload(response_payload),
            limit=limit,
            default_source_type="web_search",
        )
        return SearchResultBundle(provider=self.config.name, hits=hits)


class OpenAIWebSearchProvider(BaseConfiguredSearchProvider):
    def build_request(self, query: str, *, limit: int = 10) -> ProviderRequest:
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
        hits = _parse_search_results_text(
            self.config.name,
            query,
            _extract_text_payload(response_payload),
            limit=limit,
            default_source_type="web_search",
        )
        return SearchResultBundle(provider=self.config.name, hits=hits)
