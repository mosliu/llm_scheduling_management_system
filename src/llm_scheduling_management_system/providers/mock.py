from llm_scheduling_management_system.providers.interfaces import FetchProvider, LLMProvider, SearchProvider
from llm_scheduling_management_system.providers.types import FetchDocument, SearchHit, SearchResultBundle


class MockSearchProvider(SearchProvider):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def search(self, query: str, *, limit: int = 10) -> SearchResultBundle:
        hits = [
            SearchHit(
                provider=self.provider_name,
                title=f"{query} headline {index + 1}",
                source_domain=f"{self.provider_name}.example.com",
                source_type="news" if index == 0 else "social",
                query=query,
                published_at_utc=None,
                snippet=f"Simulated snippet {index + 1} for {query}",
            )
            for index in range(min(limit, 2))
        ]
        return SearchResultBundle(
            provider=self.provider_name,
            hits=hits,
            request_metadata={"simulated": True, "limit": limit},
        )


class MockFetchProvider(FetchProvider):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def fetch(self, url: str) -> FetchDocument:
        return FetchDocument(
            provider=self.provider_name,
            url=url,
            title=f"Fetched {url}",
            content_text=f"Simulated fetched content for {url}",
            metadata={"simulated": True},
        )


class MockLLMProvider(LLMProvider):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def generate(self, prompt: str) -> str:
        return f"[{self.provider_name}] simulated generation for prompt: {prompt}"
