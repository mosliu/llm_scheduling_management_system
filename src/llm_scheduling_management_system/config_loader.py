from pathlib import Path
import os
import tomllib

from llm_scheduling_management_system.config_models import (
    AccessConfig,
    AppConfig,
    LLMConfig,
    MCPConfig,
    SearchConfig,
    SourceRegistryConfig,
)


def _load_toml(path: Path) -> dict:
    """载入并解析指定的 TOML 文件。

    用途:
        内部辅助方法，若文件存在则以二进制模式打开并使用 tomllib 载入，否则返回空字典。

    用法:
        data = _load_toml(Path("config.toml"))

    @Author: mosliu
    """
    if not path.exists():
        return {}
    with path.open("rb") as file:
        return tomllib.load(file)


def resolve_config_path(primary: str | Path, fallback: str | Path) -> Path:
    """解析并确定配置文件的最终使用路径。

    用途:
        在主路径文件存在时优先选择它，否则回退到备用路径。

    用法:
        config_path = resolve_config_path("config/app.toml", "config/app.example.toml")

    @Author: mosliu
    """
    primary_path = Path(primary)
    if primary_path.exists():
        return primary_path
    return Path(fallback)


def load_search_config(path: str | Path | None = None) -> SearchConfig:
    """加载搜索相关服务提供商的配置。

    用途:
        读取并验证搜索配置文件，将其转化为 Pydantic 数据模型对象。支持环境变量、自定义路径以及默认路径解析。

    用法:
        search_config = load_search_config()

    @Author: mosliu
    """
    env_path = os.getenv("LSMS_SEARCH_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/search.toml", "config/search.example.toml")
    return SearchConfig.model_validate(_load_toml(config_path))


def load_app_config(path: str | Path | None = None) -> AppConfig:
    """加载应用级 HTTP 配置。

    用途:
        读取 `config/app.toml` 或示例配置中的 API 运行参数，当前主要用于 CORS 配置。

    用法:
        app_config = load_app_config()

    @Author: mosliu
    """
    env_path = os.getenv("LSMS_APP_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/app.toml", "config/app.example.toml")
    return AppConfig.model_validate(_load_toml(config_path))



def load_access_config(path: str | Path | None = None) -> AccessConfig:
    """加载系统身份验证与访问控制的配置。

    用途:
        读取并验证访问控制配置文件（如密码、请求头名称等），返回验证后的 AccessConfig 对象。

    用法:
        access_config = load_access_config()

    @Author: mosliu
    """
    env_path = os.getenv("LSMS_ACCESS_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/access.toml", "config/access.example.toml")
    return AccessConfig.model_validate(_load_toml(config_path))


def load_llm_config(path: str | Path | None = None) -> LLMConfig:
    """加载大语言模型 (LLM) 服务提供商及 Profile 配置。

    用途:
        读取并验证 LLM 配置文件，返回验证后的 LLMConfig 实体。

    用法:
        llm_config = load_llm_config()

    @Author: mosliu
    """
    env_path = os.getenv("LSMS_LLM_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/llm.toml", "config/llm.example.toml")
    return LLMConfig.model_validate(_load_toml(config_path))


def load_source_registry_config(path: str | Path | None = None) -> SourceRegistryConfig:
    """加载数据源注册表配置。

    用途:
        读取并验证数据源（如网站域名、语言、发布类型等）的信息，返回 SourceRegistryConfig。

    用法:
        registry_config = load_source_registry_config()

    @Author: mosliu
    """
    env_path = os.getenv("LSMS_SOURCE_REGISTRY_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/source_registry.toml", "config/source_registry.example.toml")
    return SourceRegistryConfig.model_validate(_load_toml(config_path))


def load_mcp_config(path: str | Path | None = None) -> MCPConfig:
    """加载模型控制协议 (MCP) 服务端连接配置。

    用途:
        读取并验证 MCP 配置文件（支持各种 MCP 服务端的命令行、参数和连接地址），返回 MCPConfig 实体。

    用法:
        mcp_config = load_mcp_config()

    @Author: mosliu
    """
    env_path = os.getenv("LSMS_MCP_CONFIG_PATH")
    config_path = Path(path) if path is not None else Path(env_path) if env_path else resolve_config_path("config/mcp.toml", "config/mcp.example.toml")
    return MCPConfig.model_validate(_load_toml(config_path))

