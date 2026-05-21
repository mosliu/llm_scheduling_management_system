from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchHit:
    """搜索引擎返回的单条命中记录。

    用途:
        保存网络搜索中单个网页或文献的元数据（标题、链接、来源域名、发布时间等）。

    用法:
        hit = SearchHit(
            provider="tavily",
            title="Python Tutorial",
            url="https://python.org",
            source_domain="python.org",
            source_type="official",
            query="python tutorial"
        )

    @Author: mosliu
    """
    provider: str
    title: str
    url: str | None
    source_domain: str
    source_type: str
    query: str
    published_at_utc: str | None = None
    snippet: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResultBundle:
    """搜索结果包。

    用途:
        保存一次搜索请求产生的全部命中记录（SearchHit 列表）以及相关的请求元数据。

    用法:
        bundle = SearchResultBundle(provider="exa", hits=[hit1, hit2])

    @Author: mosliu
    """
    provider: str
    hits: list[SearchHit]
    request_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchDocument:
    """抓取到的网页文档内容。

    用途:
        保存内容抓取服务（Fetch Provider）拉取到的网页正文、标题、作者、语言及元数据。

    用法:
        doc = FetchDocument(
            provider="exa",
            url="http://example.com",
            title="Example Page",
            content_text="Hello World"
        )

    @Author: mosliu
    """
    provider: str
    url: str
    title: str | None
    content_text: str
    canonical_url: str | None = None
    author: str | None = None
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
