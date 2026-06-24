from llm_scheduling_management_system.providers.factory import LLMProviderFactory, SearchProviderFactory


def test_search_provider_factory_builds_default_search_providers():
    factory = SearchProviderFactory()

    providers = factory.build_default_search_providers()

    assert providers
    assert [type(provider).__name__ for provider in providers] == [
        "ExaSearchProvider",
        "TavilySearchProvider",
        "BochaSearchProvider",
        "FirecrawlSearchProvider",
    ]


def test_search_provider_factory_builds_default_fetch_and_crawl_providers():
    factory = SearchProviderFactory()

    fetch_provider = factory.build_default_fetch_provider()
    crawl_provider = factory.build_default_crawl_provider()

    assert fetch_provider is not None
    assert crawl_provider is not None
    assert type(fetch_provider).__name__ == "FirecrawlFetchProvider"
    assert type(crawl_provider).__name__ == "FirecrawlCrawlProvider"


def test_search_provider_factory_builds_gemini_search_provider_by_name():
    factory = SearchProviderFactory()

    provider = factory.build_provider_by_name("gemini_search")

    assert provider is not None
    assert type(provider).__name__ == "GeminiSearchProvider"


def test_search_provider_factory_builds_bocha_search_provider_by_name():
    factory = SearchProviderFactory()

    provider = factory.build_provider_by_name("bocha_search")

    assert provider is not None
    assert type(provider).__name__ == "BochaSearchProvider"


def test_llm_provider_factory_builds_profile_provider():
    factory = LLMProviderFactory()

    provider = factory.build_profile_provider("advanced_reasoning_cn")

    assert type(provider).__name__ == "AnthropicProvider"
