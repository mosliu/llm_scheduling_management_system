from fastapi import APIRouter

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


@router.get("/search", response_model=list[ConfiguredProviderResponse])
def list_search_providers() -> list[ConfiguredProviderResponse]:
    config = load_search_config()
    return [map_configured_provider(provider) for provider in config.providers]


@router.get("/fetch", response_model=list[ConfiguredProviderResponse])
def list_fetch_providers() -> list[ConfiguredProviderResponse]:
    config = load_search_config()
    return [map_configured_provider(provider) for provider in config.fetch_providers]


@router.get("/crawl", response_model=list[ConfiguredProviderResponse])
def list_crawl_providers() -> list[ConfiguredProviderResponse]:
    config = load_search_config()
    return [map_configured_provider(provider) for provider in config.crawl_providers]


@router.get("/llm/providers", response_model=list[ConfiguredLLMProviderResponse])
def list_llm_providers() -> list[ConfiguredLLMProviderResponse]:
    config = load_llm_config()
    return [map_configured_llm_provider(provider) for provider in config.providers]


@router.get("/llm/profiles", response_model=list[ConfiguredLLMProfileResponse])
def list_llm_profiles() -> list[ConfiguredLLMProfileResponse]:
    config = load_llm_config()
    return [map_configured_llm_profile(profile) for profile in config.profiles]


@router.get("/source-registry", response_model=list[SourceRegistryEntryResponse])
def list_source_registry() -> list[SourceRegistryEntryResponse]:
    config = load_source_registry_config()
    return [map_source_registry_entry(entry) for entry in config.sources]


@router.get("/mcp/servers", response_model=list[MCPServerResponse])
def list_mcp_servers() -> list[MCPServerResponse]:
    config = load_mcp_config()
    return [map_mcp_server(server) for server in config.servers]


@router.get("/health")
def get_provider_health() -> dict:
    search = test_service.test_search_config(load_search_config())
    llm = test_service.test_llm_config(load_llm_config())
    mcp = test_service.test_mcp_config(load_mcp_config())
    return {
        "search": search["results"],
        "llm": llm["results"],
        "mcp": mcp["results"],
    }
