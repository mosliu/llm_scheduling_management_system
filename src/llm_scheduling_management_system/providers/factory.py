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
    BochaSearchProvider,
    ExaSearchProvider,
    FirecrawlSearchProvider,
    GeminiSearchProvider,
    GrokSearchProvider,
    OpenAIWebSearchProvider,
    TavilySearchProvider,
    TinyFishSearchProvider,
)


class SearchProviderFactory:
    """搜索与爬虫服务商工厂类。

    用途:
        用于根据配置以及指定的服务商名称构建搜索引擎（SearchProvider）、内容抓取服务（FetchProvider）和爬虫（Crawl）的具体实现。

    用法:
        factory = SearchProviderFactory()
        provider = factory.build_provider_by_name("tavily_search")

    @Author: mosliu
    """

    def __init__(self, config: SearchConfig | None = None) -> None:
        """初始化 SearchProviderFactory 实例。

        用途:
            加载搜索和抓取的全局配置，可指定或自动加载。

        用法:
            factory = SearchProviderFactory()

        @Author: mosliu
        """
        self.config = config or load_search_config()

    def build_provider_by_name(self, provider_name: str) -> SearchProvider | None:
        """根据名称构建已启用的搜索引擎实例。

        用途:
            解析名称匹配且处于启用状态的配置，返回对应的具体实现（如 ExaSearchProvider 或 TavilySearchProvider）。

        用法:
            provider = factory.build_provider_by_name("tavily_search")

        @Author: mosliu
        """
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
        if provider.vendor == "bocha":
            return BochaSearchProvider(provider)
        if provider.vendor == "grok":
            return GrokSearchProvider(provider)
        if provider.vendor == "openai":
            return OpenAIWebSearchProvider(provider)
        if provider.vendor == "gemini":
            return GeminiSearchProvider(provider)
        return None

    def build_default_search_providers(self) -> list[SearchProvider]:
        """构建策略配置中默认的所有搜索引擎实例列表。

        用途:
            根据配置中的 default_search_providers 列表，依次构建并返回启用的引擎对象列表。

        用法:
            providers = factory.build_default_search_providers()

        @Author: mosliu
        """
        selected = []
        for provider_name in self.config.policy.default_search_providers:
            provider = self.build_provider_by_name(provider_name)
            if provider is not None:
                selected.append(provider)
        return selected

    def build_search_providers(self, provider_names: list[str]) -> list[SearchProvider]:
        """构建指定名称列表的搜索引擎实例列表。

        用途:
            根据传入的名称列表过滤并实例化多个启用中的搜索引擎。

        用法:
            providers = factory.build_search_providers(["tavily_search", "exa_search"])

        @Author: mosliu
        """
        selected = []
        for provider_name in provider_names:
            provider = self.build_provider_by_name(provider_name)
            if provider is not None:
                selected.append(provider)
        return selected

    def build_default_fetch_provider(self) -> FetchProvider | None:
        """构建默认的内容抓取服务商实例。

        用途:
            读取并构建默认策略里配置的抓取服务（如 exa_contents）。

        用法:
            fetch_provider = factory.build_default_fetch_provider()

        @Author: mosliu
        """
        provider_name = self.config.policy.default_fetch_provider
        if provider_name is None:
            return None
        return self.build_fetch_provider_by_name(provider_name)

    def build_fetch_provider_by_name(self, provider_name: str) -> FetchProvider | None:
        """根据名称构建已启用的网页抓取服务商实例。

        用途:
            解析名称匹配的网页抓取配置，返回对应的具体实现（如 ExaFetchProvider 或 TavilyFetchProvider）。

        用法:
            fetch_provider = factory.build_fetch_provider_by_name("exa_contents")

        @Author: mosliu
        """
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
        """构建默认的深度网页爬虫提供商实例。

        用途:
            读取并构建默认策略里配置的爬虫（Crawl）服务。

        用法:
            crawl_provider = factory.build_default_crawl_provider()

        @Author: mosliu
        """
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
    """大语言模型提供商工厂类。

    用途:
        用于根据配置和大模型 Profile 名称构建与管理具体的 LLM 调用实例（如 OpenAIProvider 或 AnthropicProvider），以及解析 Profile 回退链。

    用法:
        factory = LLMProviderFactory()
        provider = factory.build_profile_provider("advanced_reasoning_cn")

    @Author: mosliu
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        """初始化 LLMProviderFactory 实例。

        用途:
            加载大模型集成及 Profile 的全局配置。

        用法:
            factory = LLMProviderFactory()

        @Author: mosliu
        """
        self.config = config or load_llm_config()

    def get_profile_config(self, profile_name: str) -> LLMProfileConfig | None:
        """获取大语言模型 Profile 的配置。

        用途:
            在配置中查找与传入 Profile 名称相对应的数据。

        用法:
            profile_config = factory.get_profile_config("cheap_structured_cn")

        @Author: mosliu
        """
        return next((item for item in self.config.profiles if item.name == profile_name), None)

    def resolve_profile_chain(self, primary_profile_name: str, extra_profile_names: list[str] | None = None) -> list[str]:
        """解析 Profile 执行与回退（Fallback）的调用链顺序。

        用途:
            从主要 Profile 开始，将其自带的回退 Profile 和额外的 Profile 依次排序去重，以构成应对模型故障的备用 Profile 链。

        用法:
            chain = factory.resolve_profile_chain("advanced_reasoning", ["backup_profile"])

        @Author: mosliu
        """
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
        """根据指定的 Profile 名称构建对应的 LLMProvider。

        用途:
            查找该 Profile 关联的底层大模型服务商配置并实例化。如果配置不存在，自动回退到模拟的 Mock 客户端。

        用法:
            llm_provider = factory.build_profile_provider("advanced_reasoning_cn")

        @Author: mosliu
        """
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
