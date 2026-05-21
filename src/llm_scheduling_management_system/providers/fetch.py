from llm_scheduling_management_system.config_models import SearchProviderConfig
from llm_scheduling_management_system.providers.http_client import HTTPProviderClient, ProviderRequest
from llm_scheduling_management_system.providers.interfaces import FetchProvider
from llm_scheduling_management_system.providers.types import FetchDocument


class BaseConfiguredFetchProvider(FetchProvider):
    """基于配置的抓取提供商抽象基类。

    用途:
        继承自 FetchProvider，提供通用的 HTTP 客户端初始化和抓取策略骨架（包括模拟抓取流程）。

    用法:
        作为具体抓取服务商的基类，子类需实现 build_request 和 parse_response。

    @Author: mosliu
    """

    def __init__(self, config: SearchProviderConfig) -> None:
        """初始化 BaseConfiguredFetchProvider 实例。

        用途:
            配置抓取选项，并初始化内部 HTTPProviderClient。

        用法:
            provider = BaseConfiguredFetchProvider(config)

        @Author: mosliu
        """
        self.config = config
        self.http_client = HTTPProviderClient(config.base_url, config.timeout_seconds)

    def build_request(self, url: str) -> ProviderRequest:
        """构建向抓取服务商发送的 HTTP 请求。

        用途:
            抽象方法，定义子类需要构造出的具体 ProviderRequest。

        用法:
            req = provider.build_request("http://example.com")

        @Author: mosliu
        """
        raise NotImplementedError

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        """解析抓取服务商返回的响应数据。

        用途:
            抽象方法，定义子类如何将 API 响应解析为标准的 FetchDocument。

        用法:
            doc = provider.parse_response(url, payload)

        @Author: mosliu
        """
        raise NotImplementedError

    def fetch(self, url: str) -> FetchDocument:
        """拉取指定 URL 的网页内容。

        用途:
            实现外部网页抓取，若启用 simulate 则直接生成模拟文档，否则通过 HTTPClient 发起请求并解析。

        用法:
            doc = provider.fetch("http://example.com")

        @Author: mosliu
        """
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
    """Exa 抓取服务商实现。

    用途:
        使用 Exa 的 /contents 接口进行网页文本和元数据抓取。

    用法:
        provider = ExaFetchProvider(config)
        doc = provider.fetch("http://example.com")

    @Author: mosliu
    """

    def build_request(self, url: str) -> ProviderRequest:
        """构建 Exa 抓取 API 请求。

        用途:
            构造请求体，包含待抓取的 url，请求正文格式为 text。

        用法:
            req = provider.build_request(url)

        @Author: mosliu
        """
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/contents"),
            headers={"x-api-key": self.config.api_key, **self.config.extra_headers},
            json_body={"urls": [url], "text": True},
        )

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        """解析 Exa API 返回的内容。

        用途:
            将 Exa 返回的 results 列表映射为标准的 FetchDocument。

        用法:
            doc = provider.parse_response(url, payload)

        @Author: mosliu
        """
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
    """Firecrawl 网页内容刮取实现。

    用途:
        使用 Firecrawl /v2/scrape 接口将网页转化为 markdown 格式文档。

    用法:
        provider = FirecrawlFetchProvider(config)
        doc = provider.fetch("http://example.com")

    @Author: mosliu
    """

    def build_request(self, url: str) -> ProviderRequest:
        """构建 Firecrawl Scrape API 请求。

        用途:
            构造 POST 请求，指定输出格式为 markdown。

        用法:
            req = provider.build_request(url)

        @Author: mosliu
        """
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/v2/scrape"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body={"url": url, "formats": ["markdown"]},
        )

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        """解析 Firecrawl 响应的 markdown 及其元数据。

        用途:
            从返回的 json 中抽取网页标题、语言、markdown 正文等字段。

        用法:
            doc = provider.parse_response(url, payload)

        @Author: mosliu
        """
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
    """Tavily 正文提取服务商实现。

    用途:
        使用 Tavily 的 /extract 接口将指定网页解析并转换为 markdown 文本。

    用法:
        provider = TavilyFetchProvider(config)
        doc = provider.fetch("http://example.com")

    @Author: mosliu
    """

    def build_request(self, url: str) -> ProviderRequest:
        """构建 Tavily Extract API 请求。

        用途:
            构造 POST 请求，传递 urls 列表及 markdown 格式化要求。

        用法:
            req = provider.build_request(url)

        @Author: mosliu
        """
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/extract"),
            headers={"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers},
            json_body={"urls": [url], "format": "markdown"},
        )

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        """解析 Tavily Extract 接口的响应结果。

        用途:
            将 Tavily 返回的 raw_content 抽取出来构造 FetchDocument。

        用法:
            doc = provider.parse_response(url, payload)

        @Author: mosliu
        """
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
    """TinyFish 极简网页正文提取实现。

    用途:
        通过 TinyFish 服务解析并提取网页。

    用法:
        provider = TinyFishFetchProvider(config)
        doc = provider.fetch("http://example.com")

    @Author: mosliu
    """

    def build_request(self, url: str) -> ProviderRequest:
        """构建 TinyFish 抓取 API 请求。

        用途:
            配置请求头和请求体。

        用法:
            req = provider.build_request(url)

        @Author: mosliu
        """
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/"),
            headers={"X-API-Key": self.config.api_key, **self.config.extra_headers},
            json_body={"urls": [url], "format": "markdown"},
        )

    def parse_response(self, url: str, response_payload) -> FetchDocument:
        """解析 TinyFish 的网页抓取结果。

        用途:
            将抓取到的内容文本及发表时间映射为标准的 FetchDocument。

        用法:
            doc = provider.parse_response(url, payload)

        @Author: mosliu
        """
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
