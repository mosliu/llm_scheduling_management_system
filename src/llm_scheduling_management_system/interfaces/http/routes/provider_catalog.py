from fastapi import APIRouter
from pydantic import BaseModel, Field

from llm_scheduling_management_system.config_loader import load_llm_config, load_mcp_config, load_search_config, load_source_registry_config
from llm_scheduling_management_system.services.config_test_service import ConfigTestService
from llm_scheduling_management_system.interfaces.http.mappers import (
    map_configured_llm_profile,
    map_configured_llm_provider,
    map_configured_provider,
    map_mcp_server,
    map_source_registry_entry,
)
from llm_scheduling_management_system.schemas.tasks import (
    ConfiguredLLMProfileResponse,
    ConfiguredLLMProviderResponse,
    ConfiguredProviderResponse,
    MCPServerResponse,
    SourceRegistryEntryResponse,
)

router = APIRouter(prefix="/api/v1/provider-catalog", tags=["provider-catalog"])
test_service = ConfigTestService()


class SearchProviderTestRequest(BaseModel):
    """Payload for testing a single configured search provider."""

    provider_name: str
    query: str = "sanity check"
    limit: int = Field(default=3, ge=1, le=20)


@router.get("/search", response_model=list[ConfiguredProviderResponse])
def list_search_providers() -> list[ConfiguredProviderResponse]:
    """获取已配置的搜索服务提供商列表。

    用途:
        列出当前系统中加载的搜索（Search）提供商的配置与状态。

    用法:
        GET /api/v1/provider-catalog/search

    @Author: mosliu
    """
    config = load_search_config()
    return [map_configured_provider(provider) for provider in config.providers]


@router.post("/search/test")
def test_search_provider(request: SearchProviderTestRequest) -> dict:
    """Run a one-off search against a selected provider for console diagnostics."""

    config = load_search_config()
    return test_service.test_search_provider(config, request.provider_name, request.query, request.limit)


@router.get("/fetch", response_model=list[ConfiguredProviderResponse])
def list_fetch_providers() -> list[ConfiguredProviderResponse]:
    """获取已配置的内容抓取服务提供商列表。

    用途:
        列出当前系统加载的网页抓取（Fetch）提供商的配置与状态。

    用法:
        GET /api/v1/provider-catalog/fetch

    @Author: mosliu
    """
    config = load_search_config()
    return [map_configured_provider(provider) for provider in config.fetch_providers]


@router.get("/crawl", response_model=list[ConfiguredProviderResponse])
def list_crawl_providers() -> list[ConfiguredProviderResponse]:
    """获取已配置的深度爬取服务提供商列表。

    用途:
        列出当前系统加载的深度爬虫（Crawl）提供商的配置与状态。

    用法:
        GET /api/v1/provider-catalog/crawl

    @Author: mosliu
    """
    config = load_search_config()
    return [map_configured_provider(provider) for provider in config.crawl_providers]


@router.get("/llm/providers", response_model=list[ConfiguredLLMProviderResponse])
def list_llm_providers() -> list[ConfiguredLLMProviderResponse]:
    """获取已配置的大模型服务商列表。

    用途:
        列出系统中所有配置好的大模型（LLM）提供商（如 OpenAI、Anthropic 等）。

    用法:
        GET /api/v1/provider-catalog/llm/providers

    @Author: mosliu
    """
    config = load_llm_config()
    return [map_configured_llm_provider(provider) for provider in config.providers]


@router.get("/llm/profiles", response_model=list[ConfiguredLLMProfileResponse])
def list_llm_profiles() -> list[ConfiguredLLMProfileResponse]:
    """获取已配置的大模型 Profile 列表。

    用途:
        列出系统中所有定义好的大模型调用配置文件（Profile），如默认模型、备用模型等。

    用法:
        GET /api/v1/provider-catalog/llm/profiles

    @Author: mosliu
    """
    config = load_llm_config()
    return [map_configured_llm_profile(profile) for profile in config.profiles]


@router.get("/source-registry", response_model=list[SourceRegistryEntryResponse])
def list_source_registry() -> list[SourceRegistryEntryResponse]:
    """获取信誉源站注册列表。

    用途:
        查询并列出目前已注册的、可信或权威的媒体/数据源站点。

    用法:
        GET /api/v1/provider-catalog/source-registry

    @Author: mosliu
    """
    config = load_source_registry_config()
    return [map_source_registry_entry(entry) for entry in config.sources]


@router.get("/mcp/servers", response_model=list[MCPServerResponse])
def list_mcp_servers() -> list[MCPServerResponse]:
    """获取已配置的 MCP 服务器列表。

    用途:
        列出当前注册的 Model Context Protocol (MCP) 服务器及其连通设置。

    用法:
        GET /api/v1/provider-catalog/mcp/servers

    @Author: mosliu
    """
    config = load_mcp_config()
    return [map_mcp_server(server) for server in config.servers]


@router.get("/health")
def get_provider_health() -> dict:
    """获取所有配置好的提供商/服务的连通性健康状况。

    用途:
        对已配置的搜索引擎、大模型和 MCP 服务进行连通性拨测，汇总并返回健康度报告。

    用法:
        GET /api/v1/provider-catalog/health

    @Author: mosliu
    """
    search = test_service.test_search_config(load_search_config())
    llm = test_service.test_llm_config(load_llm_config())
    mcp = test_service.test_mcp_config(load_mcp_config())
    return {
        "search": search["results"],
        "llm": llm["results"],
        "mcp": mcp["results"],
    }
