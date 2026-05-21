from llm_scheduling_management_system.providers.interfaces import FetchProvider, LLMProvider, SearchProvider
from llm_scheduling_management_system.providers.types import FetchDocument, SearchHit, SearchResultBundle


class MockSearchProvider(SearchProvider):
    """模拟的搜索服务提供商。

    用途:
        在测试或非真实调用环境下，模拟执行网络搜索并返回虚构的搜索结果包。

    用法:
        provider = MockSearchProvider("mock_search")
        results = provider.search("test query")

    @Author: mosliu
    """
    def __init__(self, provider_name: str) -> None:
        """初始化模拟搜索提供商。

        用途:
            存储提供商名称。

        用法:
            provider = MockSearchProvider("mock_search")

        @Author: mosliu
        """
        self.provider_name = provider_name

    def search(self, query: str, *, limit: int = 10) -> SearchResultBundle:
        """模拟搜索。

        用途:
            根据传入的查询词和数量上限限制，生成并返回模拟的搜索结果。

        用法:
            results = provider.search("python")

        @Author: mosliu
        """
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
    """模拟的内容抓取服务提供商。

    用途:
        在测试或非真实调用环境下，模拟抓取指定 URL 的网页内容。

    用法:
        provider = MockFetchProvider("mock_fetch")
        doc = provider.fetch("http://example.com")

    @Author: mosliu
    """
    def __init__(self, provider_name: str) -> None:
        """初始化模拟网页抓取提供商。

        用途:
            存储提供商名称。

        用法:
            provider = MockFetchProvider("mock_fetch")

        @Author: mosliu
        """
        self.provider_name = provider_name

    def fetch(self, url: str) -> FetchDocument:
        """模拟抓取网页。

        用途:
            直接返回包含指定 URL 的模拟抓取文档。

        用法:
            doc = provider.fetch("http://example.com")

        @Author: mosliu
        """
        return FetchDocument(
            provider=self.provider_name,
            url=url,
            title=f"Fetched {url}",
            content_text=f"Simulated fetched content for {url}",
            metadata={"simulated": True},
        )


class MockLLMProvider(LLMProvider):
    """模拟的大语言模型服务提供商。

    用途:
        在测试或非真实调用环境下，模拟大语言模型的生成功能。

    用法:
        provider = MockLLMProvider("mock_llm")
        response = provider.generate("hello")

    @Author: mosliu
    """
    def __init__(self, provider_name: str) -> None:
        """初始化模拟大语言模型提供商。

        用途:
            存储提供商名称。

        用法:
            provider = MockLLMProvider("mock_llm")

        @Author: mosliu
        """
        self.provider_name = provider_name

    def generate(self, prompt: str) -> str:
        """模拟生成文本。

        用途:
            返回包含提供商名称和原提示词的模拟响应文本。

        用法:
            response = provider.generate("hello")

        @Author: mosliu
        """
        return f"[{self.provider_name}] simulated generation for prompt: {prompt}"
