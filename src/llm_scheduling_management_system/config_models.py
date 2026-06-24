from pydantic import BaseModel, Field


class AppCORSConfig(BaseModel):
    """HTTP CORS 配置。

    用途:
        控制浏览器跨域访问 API 的放行策略，支持单文件静态页通过 `file://` 或其他域访问服务端接口。

    用法:
        通过 `config/app.toml` 中的 `[api.cors]` 段进行配置。

    @Author: mosliu
    """
    enabled: bool = False
    allow_origins: list[str] = Field(default_factory=list)
    allow_origin_regex: str | None = None
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    expose_headers: list[str] = Field(default_factory=list)
    allow_credentials: bool = False
    max_age: int = 600


class AppAPIConfig(BaseModel):
    """HTTP API 运行配置。"""

    host: str = "0.0.0.0"
    port: int = 8000
    cors: AppCORSConfig = Field(default_factory=AppCORSConfig)


class AppConfig(BaseModel):
    """应用级配置聚合。

    用途:
        读取 `config/app.toml` 中与 HTTP 服务相关的运行选项，目前主要用于管理 CORS。

    用法:
        app_config = load_app_config()

    @Author: mosliu
    """

    api: AppAPIConfig = Field(default_factory=AppAPIConfig)


class AccessCredentialConfig(BaseModel):
    """用户访问凭证配置。

    用途:
        保存访问控制的用户名称和密码。

    用法:
        作为 AccessConfig 中 credentials 列表的元素。

    @Author: mosliu
    """
    user: str
    password: str


class AccessConfig(BaseModel):
    """系统全局访问控制/鉴权配置。

    用途:
        用于管理 API 的开启状态、密码请求头、Basic Auth Realm、会话 Cookie 名称以及允许的用户凭证列表。

    用法:
        通过 config_loader 中的 load_access_config 方法进行加载。

    @Author: mosliu
    """
    enabled: bool = False
    password_header_name: str = "X-LSMS-Password"
    basic_auth_realm: str = "llm-scheduling-management-system"
    session_cookie_name: str = "lsms_access_session"
    credentials: list[AccessCredentialConfig] = Field(default_factory=list)


class SearchProviderConfig(BaseModel):
    """搜索/爬取/抓取服务提供商的详细配置。

    用途:
        保存搜索提供商的名称、类型、开发商、基准 URL、API Key、超时时间、是否启用/模拟以及默认选项等。

    用法:
        作为 SearchConfig 中的 providers、fetch_providers 或 crawl_providers 列表的元素。

    @Author: mosliu
    """
    name: str
    provider_type: str
    vendor: str
    base_url: str
    api_key: str
    timeout_seconds: int
    enabled: bool = True
    simulate: bool = True
    extra_headers: dict[str, str] = Field(default_factory=dict)
    default_options: dict = Field(default_factory=dict)


class EmbeddedSearchProviderConfig(BaseModel):
    """嵌入式搜索提供商的配置。

    用途:
        保存嵌入式/本地化搜索服务的名称、类型、开发商、模式以及启用状态。

    用法:
        作为 SearchConfig 中 embedded_search_providers 列表的元素。

    @Author: mosliu
    """
    name: str
    provider_type: str
    vendor: str
    mode: str
    enabled: bool = True


class SearchPolicyConfig(BaseModel):
    """搜索策略/限制配置。

    用途:
        配置默认的时间窗口天数、每个提供商的最大结果数，以及默认的搜索、提取和爬取提供商名称。

    用法:
        作为 SearchConfig 里的 policy 属性。

    @Author: mosliu
    """
    default_time_window_days: int = 7
    max_results_per_provider: int = 30
    default_search_providers: list[str] = Field(default_factory=list)
    default_fetch_provider: str | None = None
    default_crawl_provider: str | None = None


class SearchConfig(BaseModel):
    """全局搜索相关服务的综合配置。

    用途:
        集成普通搜索、提取、爬取、嵌入式搜索的提供商配置列表以及相应的全局搜索策略。

    用法:
        通过 config_loader 中的 load_search_config 方法进行加载。

    @Author: mosliu
    """
    providers: list[SearchProviderConfig] = Field(default_factory=list)
    fetch_providers: list[SearchProviderConfig] = Field(default_factory=list)
    crawl_providers: list[SearchProviderConfig] = Field(default_factory=list)
    embedded_search_providers: list[EmbeddedSearchProviderConfig] = Field(default_factory=list)
    policy: SearchPolicyConfig = Field(default_factory=SearchPolicyConfig)


class ElasticsearchConfig(BaseModel):
    """Elasticsearch 7.10 配置。"""

    base_url: str = "http://localhost:9200"
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 30
    enabled: bool = True
    simulate: bool = True
    verify_ssl: bool = True
    version: str = "7.10"
    index_prefix: str = "qb"
    default_index_sequence: int = 1
    default_mappings_path: str = "docs/es_mappings.json"
    analysis_llm_profile: str = "cheap_structured_cn"
    fallback_search_month_window: int = 3
    date_field: str = "release_date"
    default_search_fields: list[str] = Field(
        default_factory=lambda: [
            "title^6",
            "bak1^5",
            "content^3",
            "navigation^2",
            "media_name^2",
            "author^2",
            "retweeted_source^2",
            "content_media_name^2",
            "listname^1.5",
            "information_source_area^1.5",
            "post_place^1.5",
            "ocr",
        ]
    )
    extra_headers: dict[str, str] = Field(default_factory=dict)


class LLMProviderConfig(BaseModel):
    """LLM 服务提供商的连接配置。

    用途:
        保存大模型提供商的名称、类型、接口 URL、密钥、超时时间、模拟模式及额外请求头。

    用法:
        作为 LLMConfig 中 providers 列表的元素。

    @Author: mosliu
    """
    name: str
    provider_type: str
    base_url: str
    api_key: str
    timeout_seconds: int
    simulate: bool = True
    extra_headers: dict[str, str] = Field(default_factory=dict)


class LLMProfileConfig(BaseModel):
    """LLM 运行配置 Profile。

    用途:
        指定具体使用的提供商、模型名称、温度(temperature)、最大 Token 数、是否使用结构化输出、备用 Profile 及默认选项。

    用法:
        作为 LLMConfig 中 profiles 列表的元素。

    @Author: mosliu
    """
    name: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    structured_output: bool
    fallback_profiles: list[str] = Field(default_factory=list)
    default_options: dict = Field(default_factory=dict)


class LLMConfig(BaseModel):
    """全局大语言模型配置。

    用途:
        用于聚合所有的 LLM 提供商配置以及 LLM 运行配置 Profile。

    用法:
        通过 config_loader 中的 load_llm_config 方法进行加载。

    @Author: mosliu
    """
    providers: list[LLMProviderConfig] = Field(default_factory=list)
    profiles: list[LLMProfileConfig] = Field(default_factory=list)


class SourceRegistryEntry(BaseModel):
    """数据源注册项。

    用途:
        存储单个数据源域名的元数据，包括所属区域提示、出版物类型、语言及是否官方。

    用法:
        作为 SourceRegistryConfig 中 sources 列表的元素。

    @Author: mosliu
    """
    domain: str
    region_hint: str
    publisher_type: str
    language: str
    official: bool = False


class SourceRegistryConfig(BaseModel):
    """数据源全局注册表配置。

    用途:
        聚合所有注册的源站点实体，提供对各种网站源的基本属性归档。

    用法:
        通过 config_loader 中的 load_source_registry_config 方法进行加载。

    @Author: mosliu
    """
    sources: list[SourceRegistryEntry] = Field(default_factory=list)


class MCPServerConfig(BaseModel):
    """模型控制协议 (MCP) 服务端配置。

    用途:
        保存单个 MCP 服务的传输协议(transport)、启动命令行(command)、参数列表(args)、URL地址、超时时间及可用状态。

    用法:
        作为 MCPConfig 中 servers 列表的元素。

    @Author: mosliu
    """
    name: str
    transport: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    timeout_seconds: int = 30
    enabled: bool = True
    simulate: bool = True


class MCPConfig(BaseModel):
    """全局模型控制协议 (MCP) 配置。

    用途:
        聚合所有已注册/配置的 MCP 服务端信息。

    用法:
        通过 config_loader 中的 load_mcp_config 方法进行加载。

    @Author: mosliu
    """
    servers: list[MCPServerConfig] = Field(default_factory=list)
