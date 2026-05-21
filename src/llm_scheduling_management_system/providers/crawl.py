from llm_scheduling_management_system.config_models import SearchProviderConfig


class BaseConfiguredCrawlProvider:
    """基础配置的爬虫提供商基类。

    用途:
        提供通过配置初始化的通用爬虫接口及默认模拟方法。

    用法:
        provider = BaseConfiguredCrawlProvider(config)
        result = provider.crawl("http://example.com")

    @Author: mosliu
    """

    def __init__(self, config: SearchProviderConfig) -> None:
        """初始化 BaseConfiguredCrawlProvider 实例。

        用途:
            加载爬虫服务商的具体配置信息。

        用法:
            provider = BaseConfiguredCrawlProvider(config)

        @Author: mosliu
        """
        self.config = config

    def crawl(self, url: str) -> dict:
        """对指定 URL 进行爬取。

        用途:
            模拟抓取并分析特定网址的内容，返回爬取结果字典。

        用法:
            data = provider.crawl("http://example.com")

        @Author: mosliu
        """
        return {
            "provider": self.config.name,
            "vendor": self.config.vendor,
            "url": url,
            "status": "simulated",
        }


class FirecrawlCrawlProvider(BaseConfiguredCrawlProvider):
    """Firecrawl 爬虫服务商实现。

    用途:
        继承自 BaseConfiguredCrawlProvider，专门用于对接 Firecrawl 深度网页爬取平台。

    用法:
        provider = FirecrawlCrawlProvider(config)

    @Author: mosliu
    """
    pass


class TavilyCrawlProvider(BaseConfiguredCrawlProvider):
    """Tavily 爬虫服务商实现。

    用途:
        继承自 BaseConfiguredCrawlProvider，通过 Tavily 的爬虫 API 提取深度信息。

    用法:
        provider = TavilyCrawlProvider(config)

    @Author: mosliu
    """
    pass
