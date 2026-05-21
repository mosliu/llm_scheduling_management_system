from __future__ import annotations

from abc import ABC, abstractmethod

from llm_scheduling_management_system.providers.types import FetchDocument, SearchResultBundle


class SearchProvider(ABC):
    """搜索引擎服务商接口。

    用途:
        定义所有搜索引擎集成实现必须遵循的抽象基类。

    用法:
        class TavilySearchProvider(SearchProvider):
            ...

    @Author: mosliu
    """

    @abstractmethod
    def search(self, query: str, *, limit: int = 10) -> SearchResultBundle:
        """执行网络搜索。

        用途:
            根据给定的查询词和限制条数，调用具体的搜索引擎接口。

        用法:
            bundle = provider.search("LLM orchestration", limit=5)

        @Author: mosliu
        """
        raise NotImplementedError


class FetchProvider(ABC):
    """内容抓取服务商接口。

    用途:
        定义所有网页正文/数据抓取集成实现必须遵循的抽象基类。

    用法:
        class ExaFetchProvider(FetchProvider):
            ...

    @Author: mosliu
    """

    @abstractmethod
    def fetch(self, url: str) -> FetchDocument:
        """抓取指定 URL 的网页内容。

        用途:
            拉取指定网页的正文，并将其格式化为标准的文档对象。

        用法:
            doc = provider.fetch("http://example.com")

        @Author: mosliu
        """
        raise NotImplementedError


class LLMProvider(ABC):
    """大语言模型服务商接口。

    用途:
        定义所有大语言模型调用实现必须遵循的抽象基类。

    用法:
        class OpenAIProvider(LLMProvider):
            ...

    @Author: mosliu
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """发送提示词并获取模型生成的文本。

        用途:
            向大语言模型提交提示词并同步等待文本生成回复。

        用法:
            response_text = provider.generate("Translate: Hello")

        @Author: mosliu
        """
        raise NotImplementedError
