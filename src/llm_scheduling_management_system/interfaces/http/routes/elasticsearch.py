from fastapi import APIRouter, Depends, HTTPException, Query, status

from llm_scheduling_management_system.interfaces.http.dependencies import get_elasticsearch_service
from llm_scheduling_management_system.schemas.elasticsearch import (
    AnalyzeQueryRequest,
    AnalyzeQueryResponse,
    ElasticsearchEnsureIndexRequest,
    ElasticsearchEnsureIndexResponse,
    ElasticsearchHealthResponse,
    ElasticsearchIndexNameResponse,
    ElasticsearchMappingsResponse,
    ElasticsearchSearchRequest,
    ElasticsearchSearchResponse,
    ResolveEventRequest,
    ResolveEventResponse,
)
from llm_scheduling_management_system.services.elasticsearch_service import (
    ElasticsearchConfigError,
    ElasticsearchRequestError,
    ElasticsearchService,
)

router = APIRouter(prefix="/api/v1/es", tags=["elasticsearch"])


def _raise_es_http_error(exc: Exception) -> None:
    if isinstance(exc, ElasticsearchConfigError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "elasticsearch_config_error", "message": str(exc)},
        ) from exc
    if isinstance(exc, ElasticsearchRequestError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "elasticsearch_request_error", "message": str(exc)},
        ) from exc
    raise exc


@router.get("/health", response_model=ElasticsearchHealthResponse)
def get_elasticsearch_health(
    service: ElasticsearchService = Depends(get_elasticsearch_service),
) -> ElasticsearchHealthResponse:
    """获取 Elasticsearch 健康与版本兼容状态。"""

    try:
        return ElasticsearchHealthResponse.model_validate(service.test_connection())
    except Exception as exc:
        _raise_es_http_error(exc)


@router.get("/index-name", response_model=ElasticsearchIndexNameResponse)
def get_index_name(
    year: int = Query(...),
    month: int = Query(...),
    sequence: int = Query(default=1),
    service: ElasticsearchService = Depends(get_elasticsearch_service),
) -> ElasticsearchIndexNameResponse:
    """根据年月生成 ES 索引名。"""

    try:
        return service.build_index_name(year, month, sequence)
    except Exception as exc:
        _raise_es_http_error(exc)


@router.get("/default-mappings", response_model=ElasticsearchMappingsResponse)
def get_default_mappings(
    service: ElasticsearchService = Depends(get_elasticsearch_service),
) -> ElasticsearchMappingsResponse:
    """获取默认 ES mappings。"""

    try:
        return service.load_default_mappings()
    except Exception as exc:
        _raise_es_http_error(exc)


@router.post("/indexes/ensure", response_model=ElasticsearchEnsureIndexResponse)
def ensure_index(
    request: ElasticsearchEnsureIndexRequest,
    service: ElasticsearchService = Depends(get_elasticsearch_service),
) -> ElasticsearchEnsureIndexResponse:
    """按默认 mappings 创建或准备 ES 索引。"""

    try:
        return service.ensure_index(request)
    except Exception as exc:
        _raise_es_http_error(exc)


@router.post("/analyze-query", response_model=AnalyzeQueryResponse)
def analyze_query(
    request: AnalyzeQueryRequest,
    service: ElasticsearchService = Depends(get_elasticsearch_service),
) -> AnalyzeQueryResponse:
    """分析文本并返回用于 ES 查询的相关词组。"""

    try:
        return service.analyze_query_text(request.text, request.max_phrases)
    except Exception as exc:
        _raise_es_http_error(exc)


@router.post("/resolve-event", response_model=ResolveEventResponse)
def resolve_event(
    request: ResolveEventRequest,
    service: ElasticsearchService = Depends(get_elasticsearch_service),
) -> ResolveEventResponse:
    """根据事件名或描述提取时间范围和查询关键词。"""

    try:
        return service.resolve_event(request.text)
    except Exception as exc:
        _raise_es_http_error(exc)


@router.post("/search", response_model=ElasticsearchSearchResponse)
def search_documents(
    request: ElasticsearchSearchRequest,
    service: ElasticsearchService = Depends(get_elasticsearch_service),
) -> ElasticsearchSearchResponse:
    """执行 ES 搜索，支持跨月多索引查询。"""

    try:
        return service.search_documents(request)
    except Exception as exc:
        _raise_es_http_error(exc)
