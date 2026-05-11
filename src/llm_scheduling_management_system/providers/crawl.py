from llm_scheduling_management_system.config_models import SearchProviderConfig


class BaseConfiguredCrawlProvider:
    def __init__(self, config: SearchProviderConfig) -> None:
        self.config = config

    def crawl(self, url: str) -> dict:
        return {
            "provider": self.config.name,
            "vendor": self.config.vendor,
            "url": url,
            "status": "simulated",
        }


class FirecrawlCrawlProvider(BaseConfiguredCrawlProvider):
    pass


class TavilyCrawlProvider(BaseConfiguredCrawlProvider):
    pass
