from llm_scheduling_management_system.config_models import SearchProviderConfig
from llm_scheduling_management_system.providers.http_client import HTTPProviderClient, ProviderRequest
from llm_scheduling_management_system.providers.interfaces import SearchProvider
from llm_scheduling_management_system.providers.types import SearchHit, SearchResultBundle
import json
import re


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
                source_domain=item.get("url", "").split("/")[2] if item.get("url") else "unknown",
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
                source_domain=item.get("url", "").split("/")[2] if item.get("url") else "unknown",
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
                source_domain=item.get("url", "").split("/")[2] if item.get("url") else "unknown",
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
        system_prompt = self.config.default_options.get(
            "system",
            "You are a web research model. Return only JSON with shape "
            '{"results":[{"title":"","url":"","content":"","releaseDate":"","author":""}]}.',
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Search the web for: {query}. Return up to {limit} high-quality results as strict JSON only. "
                    "Each result must include title, url, content, releaseDate, author."
                ),
            },
        ]
        json_body = {
            "model": self.config.default_options.get("model", "grok-4.20-beta"),
            "messages": messages,
            "tools": self.config.default_options.get("tools", [{"type": "web_search", "name": "web_search"}]),
            "temperature": self.config.default_options.get("temperature", 0),
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/chat/completions"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body=json_body,
        )

    def parse_response(self, query: str, response_payload, *, limit: int = 10) -> SearchResultBundle:
        content = ""
        if isinstance(response_payload, dict):
            try:
                content = response_payload["choices"][0]["message"]["content"]
            except Exception:
                content = ""
        parsed = {"results": []}
        if isinstance(content, str):
            stripped = content.strip()
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
        hits = [
            SearchHit(
                provider=self.config.name,
                title=item.get("title", ""),
                url=item.get("url"),
                source_domain=item.get("url", "").split("/")[2] if item.get("url") else "unknown",
                source_type="web_search",
                query=query,
                published_at_utc=item.get("releaseDate"),
                snippet=item.get("content"),
                metadata={"author": item.get("author")},
            )
            for item in results[:limit]
        ]
        return SearchResultBundle(provider=self.config.name, hits=hits)
