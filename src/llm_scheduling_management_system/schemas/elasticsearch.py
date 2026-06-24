from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ElasticsearchIndexNameResponse(BaseModel):
    index_name: str
    year: int
    month: int
    sequence: int


class ElasticsearchMappingsResponse(BaseModel):
    path: str
    mappings: dict[str, Any]


class ElasticsearchHealthResponse(BaseModel):
    ok: bool
    version: str
    compatible: bool
    simulated: bool
    cluster_name: str | None = None
    message: str = ""


class ElasticsearchEnsureIndexRequest(BaseModel):
    year: int | None = None
    month: int | None = None
    sequence: int = 1
    index_name: str | None = None
    mappings: dict[str, Any] | None = None
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_index_target(self) -> "ElasticsearchEnsureIndexRequest":
        if self.index_name:
            return self
        if self.year is None or self.month is None:
            raise ValueError("year and month are required when index_name is not provided")
        return self


class ElasticsearchEnsureIndexResponse(BaseModel):
    index_name: str
    acknowledged: bool
    created: bool
    simulated: bool
    payload: dict[str, Any] = Field(default_factory=dict)


class AnalyzeQueryRequest(BaseModel):
    text: str
    max_phrases: int = 8


class AnalyzeQueryResponse(BaseModel):
    text: str
    query_phrases: list[str] = Field(default_factory=list)
    simulated: bool
    strategy: str


class ResolveEventRequest(BaseModel):
    text: str


class ResolveEventResponse(BaseModel):
    event_name: str
    summary: str
    start_date: date | None = None
    end_date: date | None = None
    query_phrases: list[str] = Field(default_factory=list)
    simulated: bool
    strategy: str


class ElasticsearchSearchRequest(BaseModel):
    query: str | None = None
    query_phrases: list[str] = Field(default_factory=list)
    event_text: str | None = None
    index_names: list[str] = Field(default_factory=list)
    year: int | None = None
    month: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    size: int = 10
    offset: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: list[dict[str, Any]] = Field(default_factory=list)
    query_dsl: dict[str, Any] | None = None
    source_includes: list[str] = Field(default_factory=list)
    source_excludes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_search_payload(self) -> "ElasticsearchSearchRequest":
        if not any([self.query, self.query_phrases, self.event_text, self.query_dsl]):
            raise ValueError("one of query, query_phrases, event_text, or query_dsl is required")
        if (self.year is None) ^ (self.month is None):
            raise ValueError("year and month must be provided together")
        return self


class ElasticsearchHitResponse(BaseModel):
    document_id: str
    score: float | None = None
    index_name: str
    source: dict[str, Any] = Field(default_factory=dict)


class ElasticsearchSearchResponse(BaseModel):
    index_names: list[str] = Field(default_factory=list)
    total: int
    took: int
    timed_out: bool
    hits: list[ElasticsearchHitResponse] = Field(default_factory=list)
    query_phrases: list[str] = Field(default_factory=list)
    query_body: dict[str, Any] = Field(default_factory=dict)
    resolved_event: ResolveEventResponse | None = None
    simulated: bool
