from pathlib import Path
import os
import tomllib

from llm_scheduling_management_system.config_models import AccessConfig, LLMConfig, MCPConfig, SearchConfig, SourceRegistryConfig


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as file:
        return tomllib.load(file)


def resolve_config_path(primary: str | Path, fallback: str | Path) -> Path:
    primary_path = Path(primary)
    if primary_path.exists():
        return primary_path
    return Path(fallback)


def load_search_config(path: str | Path | None = None) -> SearchConfig:
    env_path = os.getenv("LSMS_SEARCH_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/search.toml", "config/search.example.toml")
    return SearchConfig.model_validate(_load_toml(config_path))


def load_access_config(path: str | Path | None = None) -> AccessConfig:
    env_path = os.getenv("LSMS_ACCESS_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/access.toml", "config/access.example.toml")
    return AccessConfig.model_validate(_load_toml(config_path))


def load_llm_config(path: str | Path | None = None) -> LLMConfig:
    env_path = os.getenv("LSMS_LLM_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/llm.toml", "config/llm.example.toml")
    return LLMConfig.model_validate(_load_toml(config_path))


def load_source_registry_config(path: str | Path | None = None) -> SourceRegistryConfig:
    env_path = os.getenv("LSMS_SOURCE_REGISTRY_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/source_registry.toml", "config/source_registry.example.toml")
    return SourceRegistryConfig.model_validate(_load_toml(config_path))


def load_mcp_config(path: str | Path | None = None) -> MCPConfig:
    env_path = os.getenv("LSMS_MCP_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/mcp.toml", "config/mcp.example.toml")
    return MCPConfig.model_validate(_load_toml(config_path))
