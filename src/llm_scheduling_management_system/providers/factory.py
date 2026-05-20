from llm_scheduling_management_system.config_loader import load_llm_config, load_search_config
from llm_scheduling_management_system.config_models import LLMConfig, LLMProfileConfig, SearchConfig
from llm_scheduling_management_system.providers.crawl import FirecrawlCrawlProvider, TavilyCrawlProvider
from llm_scheduling_management_system.providers.fetch import (
    ExaFetchProvider,
    FirecrawlFetchProvider,
    TavilyFetchProvider,
    TinyFishFetchProvider,
)
from llm_scheduling_management_system.providers.interfaces import FetchProvider, LLMProvider, SearchProvider
from llm_scheduling_management_system.providers.llms import AnthropicProvider, OpenAIProvider
from llm_scheduling_management_system.providers.mock import MockLLMProvider
from llm_scheduling_management_system.providers.search import (
    ExaSearchProvider,
    FirecrawlSearchProvider,
    GrokSearchProvider,
    OpenAIWebSearchProvider,
    TavilySearchProvider,
    TinyFishSearchProvider,
)


class SearchProviderFactory:
    def __init__(self, config: SearchConfig | None = None) -> None:
        self.config = config or load_search_config()

    def build_provider_by_name(self, provider_name: str) -> SearchProvider | None:
        provider = next((item for item in self.config.providers if item.name == provider_name and item.enabled), None)
        if provider is None:
            return None
        if provider.vendor == "exa":
            return ExaSearchProvider(provider)
        if provider.vendor == "tavily":
            return TavilySearchProvider(provider)
        if provider.vendor == "firecrawl":
            return FirecrawlSearchProvider(provider)
        if provider.vendor == "tinyfish":
            return TinyFishSearchProvider(provider)
        if provider.vendor == "grok":
            return GrokSearchProvider(provider)
        if provider.vendor == "openai":
            return OpenAIWebSearchProvider(provider)
        return None

    def build_default_search_providers(self) -> list[SearchProvider]:
        selected = []
        for provider_name in self.config.policy.default_search_providers:
            provider = self.build_provider_by_name(provider_name)
            if provider is not None:
                selected.append(provider)
        return selected

    def build_search_providers(self, provider_names: list[str]) -> list[SearchProvider]:
        selected = []
        for provider_name in provider_names:
            provider = self.build_provider_by_name(provider_name)
            if provider is not None:
                selected.append(provider)
        return selected

    def build_default_fetch_provider(self) -> FetchProvider | None:
        provider_name = self.config.policy.default_fetch_provider
        if provider_name is None:
            return None
        return self.build_fetch_provider_by_name(provider_name)

    def build_fetch_provider_by_name(self, provider_name: str) -> FetchProvider | None:
        provider = next((item for item in self.config.fetch_providers if item.name == provider_name and item.enabled), None)
        if provider is None:
            return None
        if provider.vendor == "exa":
            return ExaFetchProvider(provider)
        if provider.vendor == "firecrawl":
            return FirecrawlFetchProvider(provider)
        if provider.vendor == "tavily":
            return TavilyFetchProvider(provider)
        if provider.vendor == "tinyfish":
            return TinyFishFetchProvider(provider)
        return None

    def build_default_crawl_provider(self):
        provider_name = self.config.policy.default_crawl_provider
        if provider_name is None:
            return None
        provider = next((item for item in self.config.crawl_providers if item.name == provider_name and item.enabled), None)
        if provider is None:
            return None
        if provider.vendor == "firecrawl":
            return FirecrawlCrawlProvider(provider)
        if provider.vendor == "tavily":
            return TavilyCrawlProvider(provider)
        return None


class LLMProviderFactory:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or load_llm_config()

    def get_profile_config(self, profile_name: str) -> LLMProfileConfig | None:
        return next((item for item in self.config.profiles if item.name == profile_name), None)

    def resolve_profile_chain(self, primary_profile_name: str, extra_profile_names: list[str] | None = None) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()

        def append_profile(profile_name: str) -> None:
            if not profile_name or profile_name in seen:
                return
            seen.add(profile_name)
            ordered.append(profile_name)

        append_profile(primary_profile_name)
        profile = self.get_profile_config(primary_profile_name)
        if profile is not None:
            for fallback in profile.fallback_profiles:
                append_profile(fallback)

        for profile_name in extra_profile_names or []:
            append_profile(profile_name)

        return ordered

    def build_profile_provider(self, profile_name: str) -> LLMProvider:
        profile = self.get_profile_config(profile_name)
        if profile is None:
            return MockLLMProvider("mock_llm_default")
        provider = next((item for item in self.config.providers if item.name == profile.provider), None)
        if provider is None:
            return MockLLMProvider(profile.provider)
        if provider.provider_type == "openai":
            return OpenAIProvider(provider, profile)
        if provider.provider_type == "anthropic":
            return AnthropicProvider(provider, profile)
        return MockLLMProvider(provider.name)
