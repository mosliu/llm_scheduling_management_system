from pydantic import BaseModel, Field


class SearchProviderConfig(BaseModel):
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
    name: str
    provider_type: str
    vendor: str
    mode: str
    enabled: bool = True


class SearchPolicyConfig(BaseModel):
    default_time_window_days: int = 7
    max_results_per_provider: int = 50
    default_search_providers: list[str] = Field(default_factory=list)
    default_fetch_provider: str | None = None
    default_crawl_provider: str | None = None


class SearchConfig(BaseModel):
    providers: list[SearchProviderConfig] = Field(default_factory=list)
    fetch_providers: list[SearchProviderConfig] = Field(default_factory=list)
    crawl_providers: list[SearchProviderConfig] = Field(default_factory=list)
    embedded_search_providers: list[EmbeddedSearchProviderConfig] = Field(default_factory=list)
    policy: SearchPolicyConfig = Field(default_factory=SearchPolicyConfig)


class LLMProviderConfig(BaseModel):
    name: str
    provider_type: str
    base_url: str
    api_key: str
    timeout_seconds: int
    simulate: bool = True
    extra_headers: dict[str, str] = Field(default_factory=dict)


class LLMProfileConfig(BaseModel):
    name: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    structured_output: bool
    fallback_profiles: list[str] = Field(default_factory=list)
    default_options: dict = Field(default_factory=dict)


class LLMConfig(BaseModel):
    providers: list[LLMProviderConfig] = Field(default_factory=list)
    profiles: list[LLMProfileConfig] = Field(default_factory=list)


class SourceRegistryEntry(BaseModel):
    domain: str
    region_hint: str
    publisher_type: str
    language: str
    official: bool = False


class SourceRegistryConfig(BaseModel):
    sources: list[SourceRegistryEntry] = Field(default_factory=list)


class MCPServerConfig(BaseModel):
    name: str
    transport: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    timeout_seconds: int = 30
    enabled: bool = True
    simulate: bool = True


class MCPConfig(BaseModel):
    servers: list[MCPServerConfig] = Field(default_factory=list)
