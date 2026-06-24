from __future__ import annotations

import json
import re
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

from llm_scheduling_management_system.config_loader import load_elasticsearch_config
from llm_scheduling_management_system.config_models import ElasticsearchConfig
from llm_scheduling_management_system.providers.factory import LLMProviderFactory
from llm_scheduling_management_system.schemas.elasticsearch import (
    AnalyzeQueryResponse,
    ElasticsearchEnsureIndexRequest,
    ElasticsearchEnsureIndexResponse,
    ElasticsearchHealthResponse,
    ElasticsearchHitResponse,
    ElasticsearchIndexNameResponse,
    ElasticsearchMappingsResponse,
    ElasticsearchSearchRequest,
    ElasticsearchSearchResponse,
    ResolveEventResponse,
)

TEXT_FILTER_KEYWORD_FIELDS = {
    "media_name",
    "author",
    "retweeted_source",
    "content_media_name",
    "u_nickname",
}

DEFAULT_SORT = [
    {"_score": {"order": "desc"}},
    {"release_date": {"order": "desc", "unmapped_type": "date"}},
    {"capture_time": {"order": "desc", "unmapped_type": "date"}},
    {"add_time": {"order": "desc", "unmapped_type": "date"}},
]


class ElasticsearchServiceError(Exception):
    """Elasticsearch 服务异常基类。"""


class ElasticsearchConfigError(ElasticsearchServiceError):
    """Elasticsearch 配置异常。"""


class ElasticsearchRequestError(ElasticsearchServiceError):
    """Elasticsearch 请求异常。"""


class ElasticsearchService:
    """Elasticsearch 7.10 搜索与事件分析服务。"""

    def __init__(self, config: ElasticsearchConfig | None = None) -> None:
        self.config = config or load_elasticsearch_config()
        self.llm_factory = LLMProviderFactory()

    def ensure_enabled(self) -> None:
        if not self.config.enabled:
            raise ElasticsearchConfigError("Elasticsearch is disabled")

    def build_index_name(self, year: int, month: int, sequence: int | None = None) -> ElasticsearchIndexNameResponse:
        if month < 1 or month > 12:
            raise ElasticsearchConfigError("month must be between 1 and 12")
        index_sequence = sequence if sequence is not None else self.config.default_index_sequence
        return ElasticsearchIndexNameResponse(
            index_name=f"{self.config.index_prefix}{year:04d}{month:02d}{index_sequence}",
            year=year,
            month=month,
            sequence=index_sequence,
        )

    def build_index_names_for_range(self, start_date: date, end_date: date, sequence: int | None = None) -> list[str]:
        if end_date < start_date:
            raise ElasticsearchConfigError("end_date must be greater than or equal to start_date")
        cursor = date(start_date.year, start_date.month, 1)
        end_cursor = date(end_date.year, end_date.month, 1)
        index_names: list[str] = []
        while cursor <= end_cursor:
            index_names.append(self.build_index_name(cursor.year, cursor.month, sequence).index_name)
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
        return index_names

    def load_default_mappings(self) -> ElasticsearchMappingsResponse:
        path = Path(self.config.default_mappings_path)
        mappings = json.loads(path.read_text(encoding="utf-8"))
        return ElasticsearchMappingsResponse(path=path.as_posix(), mappings=mappings)

    def test_connection(self) -> dict[str, Any]:
        info = self.get_cluster_info()
        compatible = str(info.get("version", "")).startswith(self.config.version)
        message = "elasticsearch ok" if compatible else f"expected ES {self.config.version}, got {info.get('version', 'unknown')}"
        response = ElasticsearchHealthResponse(
            ok=compatible or info.get("simulated", False),
            version=str(info.get("version", "unknown")),
            compatible=compatible,
            simulated=bool(info.get("simulated", False)),
            cluster_name=info.get("cluster_name"),
            message=message,
        )
        return response.model_dump()

    def get_cluster_info(self) -> dict[str, Any]:
        self.ensure_enabled()
        if self.config.simulate:
            return {
                "cluster_name": "simulated-es",
                "version": "7.10.0",
                "simulated": True,
            }
        payload = self._request("GET", "/")
        version = payload.get("version", {}).get("number", "unknown") if isinstance(payload, dict) else "unknown"
        return {
            "cluster_name": payload.get("cluster_name") if isinstance(payload, dict) else None,
            "version": version,
            "simulated": False,
        }

    def ensure_index(self, request: ElasticsearchEnsureIndexRequest) -> ElasticsearchEnsureIndexResponse:
        self.ensure_enabled()
        index_name = request.index_name
        if not index_name:
            built = self.build_index_name(request.year or 0, request.month or 0, request.sequence)
            index_name = built.index_name
        mappings = request.mappings or self.load_default_mappings().mappings
        payload = {
            "mappings": mappings,
            "settings": request.settings,
        }
        if self.config.simulate:
            return ElasticsearchEnsureIndexResponse(
                index_name=index_name,
                acknowledged=True,
                created=True,
                simulated=True,
                payload=payload,
            )
        response = self._request("PUT", f"/{index_name}", json_body=payload)
        return ElasticsearchEnsureIndexResponse(
            index_name=index_name,
            acknowledged=bool(response.get("acknowledged", False)),
            created=bool(response.get("shards_acknowledged", response.get("acknowledged", False))),
            simulated=False,
            payload=response,
        )

    def analyze_query_text(self, text: str, max_phrases: int = 8) -> AnalyzeQueryResponse:
        llm_payload = self._try_llm_json(
            prompt=(
                "You are a search query analyst for Elasticsearch event retrieval.\n"
                "Extract high-signal Chinese query phrases for the given text.\n"
                "Return strict JSON only with shape "
                "{\"query_phrases\": [\"...\"]}.\n"
                f"Return at most {max_phrases} phrases."
            ),
            user_text=text,
        )
        if isinstance(llm_payload, dict):
            phrases = self._normalize_phrases(llm_payload.get("query_phrases", []), max_phrases)
            if phrases:
                return AnalyzeQueryResponse(text=text, query_phrases=phrases, simulated=self.config.simulate, strategy="llm")
        return AnalyzeQueryResponse(
            text=text,
            query_phrases=self._heuristic_query_phrases(text, max_phrases=max_phrases),
            simulated=self.config.simulate,
            strategy="heuristic",
        )

    def resolve_event(self, text: str) -> ResolveEventResponse:
        llm_payload = self._try_llm_json(
            prompt=(
                "You are an event extraction assistant for Elasticsearch retrieval.\n"
                "Given an event name or description, infer the event name, time range, and search phrases.\n"
                "Return strict JSON only with shape "
                "{\"event_name\":\"\",\"summary\":\"\",\"start_date\":\"YYYY-MM-DD or empty\",\"end_date\":\"YYYY-MM-DD or empty\",\"query_phrases\":[\"...\"]}."
            ),
            user_text=text,
        )
        if isinstance(llm_payload, dict):
            resolved = self._build_resolve_event_response(text, llm_payload, strategy="llm")
            if resolved.query_phrases:
                return resolved
        return self._heuristic_resolve_event(text)

    def search_documents(self, request: ElasticsearchSearchRequest) -> ElasticsearchSearchResponse:
        self.ensure_enabled()
        resolved_event = self.resolve_event(request.event_text) if request.event_text else None
        query_phrases = self._collect_query_phrases(request, resolved_event)
        effective_start = request.start_date or (resolved_event.start_date if resolved_event else None)
        effective_end = request.end_date or (resolved_event.end_date if resolved_event else None)
        index_names = self._resolve_index_names(request, effective_start, effective_end)
        query_body = request.query_dsl or self._build_search_body(
            query=request.query,
            query_phrases=query_phrases,
            start_date=effective_start,
            end_date=effective_end,
            filters=request.filters,
            size=request.size,
            offset=request.offset,
            sort=request.sort,
            source_includes=request.source_includes,
            source_excludes=request.source_excludes,
        )

        if self.config.simulate:
            return ElasticsearchSearchResponse(
                index_names=index_names,
                total=0,
                took=0,
                timed_out=False,
                hits=[],
                query_phrases=query_phrases,
                query_body=query_body,
                resolved_event=resolved_event,
                simulated=True,
            )

        payload = self._request("POST", f"/{','.join(index_names)}/_search", json_body=query_body)
        hits = payload.get("hits", {}) if isinstance(payload, dict) else {}
        total_payload = hits.get("total", 0)
        total = total_payload.get("value", 0) if isinstance(total_payload, dict) else int(total_payload)
        return ElasticsearchSearchResponse(
            index_names=index_names,
            total=total,
            took=int(payload.get("took", 0)),
            timed_out=bool(payload.get("timed_out", False)),
            hits=[
                ElasticsearchHitResponse(
                    document_id=str(item.get("_id", "")),
                    score=item.get("_score"),
                    index_name=str(item.get("_index", "")),
                    source=item.get("_source", {}) if isinstance(item.get("_source"), dict) else {},
                )
                for item in hits.get("hits", [])
            ],
            query_phrases=query_phrases,
            query_body=query_body,
            resolved_event=resolved_event,
            simulated=False,
        )

    def _resolve_index_names(
        self,
        request: ElasticsearchSearchRequest,
        start_date: date | None,
        end_date: date | None,
    ) -> list[str]:
        if request.index_names:
            return request.index_names
        if request.year is not None and request.month is not None:
            return [self.build_index_name(request.year, request.month).index_name]
        if start_date and end_date:
            return self.build_index_names_for_range(start_date, end_date)
        today = date.today()
        fallback_start = self._month_start(today, months_back=self.config.fallback_search_month_window - 1)
        return self.build_index_names_for_range(fallback_start, today)

    def _build_search_body(
        self,
        *,
        query: str | None,
        query_phrases: list[str],
        start_date: date | None,
        end_date: date | None,
        filters: dict[str, Any],
        size: int,
        offset: int,
        sort: list[dict[str, Any]],
        source_includes: list[str],
        source_excludes: list[str],
    ) -> dict[str, Any]:
        should_clauses = []
        merged_phrases = []
        if query:
            merged_phrases.append(query)
        merged_phrases.extend(query_phrases)
        for phrase in self._normalize_phrases(merged_phrases, max_phrases=12):
            should_clauses.extend(self._build_phrase_should_clauses(phrase))

        filter_clauses = []
        if start_date or end_date:
            range_payload: dict[str, str] = {}
            if start_date:
                range_payload["gte"] = f"{start_date.isoformat()} 00:00:00"
            if end_date:
                range_payload["lte"] = f"{end_date.isoformat()} 23:59:59"
            filter_clauses.append({"range": {self.config.date_field: range_payload}})

        for field_name, value in filters.items():
            filter_clauses.append(self._build_filter_clause(field_name, value))

        body: dict[str, Any] = {
            "from": offset,
            "size": size,
            "track_total_hits": True,
            "query": {
                "bool": {
                    "should": should_clauses or [{"match_all": {}}],
                    "minimum_should_match": 1 if should_clauses else 0,
                    "filter": filter_clauses,
                }
            },
        }
        body["sort"] = sort or DEFAULT_SORT
        if source_includes or source_excludes:
            body["_source"] = {}
            if source_includes:
                body["_source"]["includes"] = source_includes
            if source_excludes:
                body["_source"]["excludes"] = source_excludes
        return body

    def _build_phrase_should_clauses(self, phrase: str) -> list[dict[str, Any]]:
        return [
            {
                "dis_max": {
                    "tie_breaker": 0.2,
                    "queries": [
                        {"match_phrase": {"title": {"query": phrase, "boost": 8}}},
                        {"match_phrase": {"bak1": {"query": phrase, "boost": 6}}},
                        {"match_phrase": {"media_name": {"query": phrase, "boost": 4}}},
                        {"match_phrase": {"author": {"query": phrase, "boost": 3}}},
                    ],
                }
            },
            {
                "multi_match": {
                    "query": phrase,
                    "fields": self.config.default_search_fields,
                    "type": "best_fields",
                    "operator": "or",
                    "minimum_should_match": "60%",
                    "boost": 2,
                }
            },
            {
                "multi_match": {
                    "query": phrase,
                    "fields": self.config.default_search_fields,
                    "type": "phrase",
                    "slop": 1,
                    "boost": 3,
                }
            },
        ]

    def _build_filter_clause(self, field_name: str, value: Any) -> dict[str, Any]:
        normalized_field = self._normalize_filter_field(field_name, value)
        if isinstance(value, list):
            return {"terms": {normalized_field: value}}
        if isinstance(value, dict):
            return {"range": {normalized_field: value}}
        return {"term": {normalized_field: value}}

    def _normalize_filter_field(self, field_name: str, value: Any) -> str:
        if isinstance(value, dict):
            return field_name
        if field_name in TEXT_FILTER_KEYWORD_FIELDS and not field_name.endswith(".keyword"):
            return f"{field_name}.keyword"
        return field_name

    def _collect_query_phrases(
        self,
        request: ElasticsearchSearchRequest,
        resolved_event: ResolveEventResponse | None,
    ) -> list[str]:
        phrases = list(request.query_phrases)
        if resolved_event is not None:
            phrases.extend(resolved_event.query_phrases)
        if request.query:
            phrases.insert(0, request.query)
        return self._normalize_phrases(phrases, max_phrases=12)

    def _build_resolve_event_response(
        self,
        raw_text: str,
        payload: dict[str, Any],
        *,
        strategy: str,
    ) -> ResolveEventResponse:
        start_date = self._parse_date_value(payload.get("start_date"))
        end_date = self._parse_date_value(payload.get("end_date"))
        if start_date and end_date and end_date < start_date:
            start_date, end_date = end_date, start_date
        phrases = self._normalize_phrases(payload.get("query_phrases", []), max_phrases=12)
        if not phrases:
            phrases = self._heuristic_query_phrases(raw_text, max_phrases=8)
        return ResolveEventResponse(
            event_name=str(payload.get("event_name") or raw_text).strip(),
            summary=str(payload.get("summary") or raw_text).strip(),
            start_date=start_date,
            end_date=end_date,
            query_phrases=phrases,
            simulated=self.config.simulate,
            strategy=strategy,
        )

    def _heuristic_resolve_event(self, text: str) -> ResolveEventResponse:
        start_date, end_date = self._extract_date_range(text)
        phrases = self._heuristic_query_phrases(text, max_phrases=8)
        event_name = phrases[0] if phrases else text.strip()
        return ResolveEventResponse(
            event_name=event_name,
            summary=text.strip(),
            start_date=start_date,
            end_date=end_date,
            query_phrases=phrases,
            simulated=self.config.simulate,
            strategy="heuristic",
        )

    def _heuristic_query_phrases(self, text: str, max_phrases: int = 8) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        stripped = re.sub(r"\d{4}[年/-]\d{1,2}([月/-]\d{1,2}日?)?", "", normalized)
        pieces = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,24}", stripped)
        phrases = [normalized]
        if stripped and stripped != normalized:
            phrases.append(stripped.strip())
        phrases.extend(piece.strip() for piece in pieces if piece.strip())

        compact = stripped.replace("发生", " ").replace("事件", " ").replace("情况", " ").strip()
        if compact and compact not in phrases:
            phrases.append(compact)

        return self._normalize_phrases(phrases, max_phrases=max_phrases)

    def _normalize_phrases(self, values: list[Any], max_phrases: int) -> list[str]:
        phrases: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            normalized = re.sub(r"\s+", " ", value).strip(" ,，。；;")
            if len(normalized) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            phrases.append(normalized)
            if len(phrases) >= max_phrases:
                break
        return phrases

    def _extract_date_range(self, text: str) -> tuple[date | None, date | None]:
        full_dates = [
            date(int(year), int(month), int(day))
            for year, month, day in re.findall(r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?", text)
        ]
        if full_dates:
            return min(full_dates), max(full_dates)

        month_dates = [
            (int(year), int(month))
            for year, month in re.findall(r"(\d{4})[年/-](\d{1,2})月", text)
        ]
        if month_dates:
            start_year, start_month = min(month_dates)
            end_year, end_month = max(month_dates)
            start_date = date(start_year, start_month, 1)
            end_day = monthrange(end_year, end_month)[1]
            end_date = date(end_year, end_month, end_day)
            return start_date, end_date

        return None, None

    def _parse_date_value(self, value: Any) -> date | None:
        if not value or not isinstance(value, str):
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _month_start(self, base_date: date, months_back: int) -> date:
        year = base_date.year
        month = base_date.month - months_back
        while month <= 0:
            month += 12
            year -= 1
        return date(year, month, 1)

    def _try_llm_json(self, *, prompt: str, user_text: str) -> dict[str, Any] | None:
        try:
            provider = self.llm_factory.build_profile_provider(self.config.analysis_llm_profile)
            generated = provider.generate(f"{prompt}\n\nInput:\n{user_text}")
        except Exception:
            return None
        if "simulated generation for prompt" in generated:
            return None
        return self._parse_json_object(generated)

    def _parse_json_object(self, text: str) -> dict[str, Any] | None:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```json\s*|\s*```$", "", stripped, flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", **self.config.extra_headers}
        if self.config.api_key and "Authorization" not in headers:
            headers["Authorization"] = f"ApiKey {self.config.api_key}"
        auth = None
        if self.config.username and self.config.password:
            auth = (self.config.username, self.config.password)
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = httpx.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                timeout=self.config.timeout_seconds,
                verify=self.config.verify_ssl,
                auth=auth,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ElasticsearchRequestError(str(exc)) from exc
        payload = response.json()
        if not isinstance(payload, dict):
            raise ElasticsearchRequestError("unexpected Elasticsearch response payload")
        return payload
