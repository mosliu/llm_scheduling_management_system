from llm_scheduling_management_system.config_models import SearchProviderConfig
from llm_scheduling_management_system.providers.http_client import HTTPProviderClient, ProviderRequest
from llm_scheduling_management_system.providers.interfaces import FetchProvider
from llm_scheduling_management_system.providers.types import FetchDocument


class BaseConfiguredFetchProvider(FetchProvider):
    def __init__(self, config: SearchProviderConfig) -> None:
        self.config = config
        self.http_client = HTTPProviderClient(config.base_url, config.timeout_seconds)

    def build_request(self, url: str) -> ProviderRequest:
        raise NotImplementedError

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        raise NotImplementedError

    def fetch(self, url: str) -> FetchDocument:
        if not self.config.simulate:
            response = self.http_client.execute(self.build_request(url))
            return self.parse_response(url, response.payload)
        return FetchDocument(
            provider=self.config.name,
            url=url,
            title=f"Fetched by {self.config.vendor}",
            content_text=f"Simulated fetched content from {url}",
            canonical_url=url,
            author=self.config.vendor,
            language="en",
            metadata={
                "vendor": self.config.vendor,
                "provider_type": self.config.provider_type,
                "base_url": self.config.base_url,
            },
        )


class ExaFetchProvider(BaseConfiguredFetchProvider):
    def build_request(self, url: str) -> ProviderRequest:
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/contents"),
            headers={"x-api-key": self.config.api_key, **self.config.extra_headers},
            json_body={"urls": [url], "text": True},
        )

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        result = (response_payload.get("results") or [{}])[0] if isinstance(response_payload, dict) else {}
        return FetchDocument(
            provider=self.config.name,
            url=result.get("url", url),
            canonical_url=result.get("url", url),
            title=result.get("title"),
            author=result.get("author"),
            language="unknown",
            content_text=result.get("text", ""),
            metadata={"vendor": self.config.vendor, "publishedDate": result.get("publishedDate"), "simulated": False},
        )


class FirecrawlFetchProvider(BaseConfiguredFetchProvider):
    def build_request(self, url: str) -> ProviderRequest:
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/v2/scrape"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body={"url": url, "formats": ["markdown"]},
        )

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        data = response_payload.get("data", {}) if isinstance(response_payload, dict) else {}
        metadata = data.get("metadata", {})
        return FetchDocument(
            provider=self.config.name,
            url=metadata.get("url", url),
            canonical_url=metadata.get("sourceURL", metadata.get("url", url)),
            title=metadata.get("title"),
            author=None,
            language=metadata.get("language"),
            content_text=data.get("markdown", ""),
            metadata={"vendor": self.config.vendor, "statusCode": metadata.get("statusCode"), "simulated": False},
        )


class TavilyFetchProvider(BaseConfiguredFetchProvider):
    def build_request(self, url: str) -> ProviderRequest:
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/extract"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body={"urls": [url], "format": "markdown"},
        )

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        result = (response_payload.get("results") or [{}])[0] if isinstance(response_payload, dict) else {}
        return FetchDocument(
            provider=self.config.name,
            url=result.get("url", url),
            canonical_url=result.get("url", url),
            title=None,
            author=None,
            language="unknown",
            content_text=result.get("raw_content", ""),
            metadata={"vendor": self.config.vendor, "simulated": False},
        )


class TinyFishFetchProvider(BaseConfiguredFetchProvider):
    def build_request(self, url: str) -> ProviderRequest:
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/"),
            headers={"X-API-Key": self.config.api_key, **self.config.extra_headers},
            json_body={"urls": [url], "format": "markdown"},
        )

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        result = (response_payload.get("results") or [{}])[0] if isinstance(response_payload, dict) else {}
        return FetchDocument(
            provider=self.config.name,
            url=result.get("final_url", result.get("url", url)),
            canonical_url=result.get("final_url", result.get("url", url)),
            title=result.get("title"),
            author=result.get("author"),
            language=result.get("language"),
            content_text=result.get("text", ""),
            metadata={"vendor": self.config.vendor, "published_date": result.get("published_date"), "simulated": False},
        )
