from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchHit:
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
    provider: str
    hits: list[SearchHit]
    request_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchDocument:
    provider: str
    url: str
    title: str | None
    content_text: str
    canonical_url: str | None = None
    author: str | None = None
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
