from llm_scheduling_management_system.config_models import LLMProfileConfig, LLMProviderConfig, SearchProviderConfig
from llm_scheduling_management_system.providers.http_client import ProviderResponse
from llm_scheduling_management_system.providers.llms import AnthropicProvider, OpenAIProvider
from llm_scheduling_management_system.providers.fetch import FirecrawlFetchProvider
from llm_scheduling_management_system.providers.search import (
    BochaSearchProvider,
    ExaSearchProvider,
    FirecrawlSearchProvider,
    GeminiSearchProvider,
    GrokSearchProvider,
    OpenAIWebSearchProvider,
    TavilySearchProvider,
    TinyFishSearchProvider,
)


def _search_config(vendor: str, name: str, base_url: str) -> SearchProviderConfig:
    return SearchProviderConfig(
        name=name,
        provider_type="search_with_inline_content",
        vendor=vendor,
        base_url=base_url,
        api_key="test-key",
        timeout_seconds=30,
        enabled=True,
        simulate=True,
    )


def test_search_providers_build_expected_requests():
    exa = ExaSearchProvider(_search_config("exa", "exa_search", "https://api.exa.ai"))
    tavily = TavilySearchProvider(_search_config("tavily", "tavily_search", "https://api.tavily.com"))
    firecrawl = FirecrawlSearchProvider(_search_config("firecrawl", "firecrawl_search", "https://api.firecrawl.dev"))
    tinyfish = TinyFishSearchProvider(_search_config("tinyfish", "tinyfish_search", "https://api.search.tinyfish.ai"))
    bocha = BochaSearchProvider(_search_config("bocha", "bocha_search", "https://api.bochaai.com"))
    gemini = GeminiSearchProvider(_search_config("gemini", "gemini_search", "https://generativelanguage.googleapis.com/v1beta"))

    exa_request = exa.build_request("test query", limit=5)
    tavily_request = tavily.build_request("test query", limit=5)
    firecrawl_request = firecrawl.build_request("test query", limit=5)
    tinyfish_request = tinyfish.build_request("test query", limit=5)
    bocha_request = bocha.build_request("test query", limit=5)
    gemini_request = gemini.build_request("test query", limit=5)

    assert exa_request.method == "POST"
    assert exa_request.url.endswith("/search")
    assert tavily_request.headers["Authorization"].startswith("Bearer ")
    assert tavily_request.json_body["max_results"] == 5
    assert firecrawl_request.url.endswith("/v2/search")
    assert firecrawl_request.json_body["limit"] == 5
    assert tinyfish_request.method == "GET"
    assert tinyfish_request.params["query"] == "test query"
    assert bocha_request.url.endswith("/v1/web-search")
    assert bocha_request.headers["Authorization"] == "Bearer test-key"
    assert bocha_request.json_body["query"] == "test query"
    assert bocha_request.json_body["count"] == 5
    assert gemini_request.url.endswith("/models/gemini-3.5-flash:generateContent")
    assert gemini_request.headers["x-goog-api-key"] == "test-key"
    assert gemini_request.json_body["tools"][0]["google_search"] == {}


def test_tavily_request_includes_default_options():
    config = SearchProviderConfig(
        name="tavily_search",
        provider_type="search_with_inline_content",
        vendor="tavily",
        base_url="https://api.tavily.com",
        api_key="test-key",
        timeout_seconds=30,
        enabled=True,
        simulate=True,
        default_options={"topic": "general", "search_depth": "basic", "include_answer": True},
    )
    provider = TavilySearchProvider(config)

    request = provider.build_request("hello", limit=3)

    assert request.json_body["query"] == "hello"
    assert request.json_body["max_results"] == 3
    assert request.json_body["topic"] == "general"
    assert request.json_body["search_depth"] == "basic"
    assert request.json_body["include_answer"] is True


def test_firecrawl_request_includes_default_options():
    config = SearchProviderConfig(
        name="firecrawl_search",
        provider_type="search_with_inline_content",
        vendor="firecrawl",
        base_url="https://api.firecrawl.dev",
        api_key="test-key",
        timeout_seconds=30,
        enabled=True,
        simulate=True,
        default_options={
            "sources": ["web", "news"],
            "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True},
        },
    )
    provider = FirecrawlSearchProvider(config)

    request = provider.build_request("hello", limit=3)

    assert request.json_body["query"] == "hello"
    assert request.json_body["limit"] == 3
    assert request.json_body["sources"] == ["web", "news"]
    assert request.json_body["scrapeOptions"]["formats"] == ["markdown"]


def test_firecrawl_request_omits_authorization_when_key_is_not_configured():
    config = SearchProviderConfig(
        name="firecrawl_search",
        provider_type="search_with_inline_content",
        vendor="firecrawl",
        base_url="https://api.firecrawl.dev",
        api_key="",
        timeout_seconds=30,
        enabled=True,
        simulate=False,
        default_options={"sources": ["web"]},
    )
    provider = FirecrawlSearchProvider(config)

    request = provider.build_request("hello", limit=3)

    assert "Authorization" not in request.headers
    assert request.json_body["query"] == "hello"
    assert request.json_body["limit"] == 3


def test_firecrawl_request_drops_blank_authorization_extra_header():
    config = SearchProviderConfig(
        name="firecrawl_search",
        provider_type="search_with_inline_content",
        vendor="firecrawl",
        base_url="https://api.firecrawl.dev",
        api_key="",
        timeout_seconds=30,
        enabled=True,
        simulate=False,
        extra_headers={"Authorization": "Bearer "},
    )
    provider = FirecrawlSearchProvider(config)

    request = provider.build_request("hello", limit=3)

    assert "Authorization" not in request.headers


def test_firecrawl_request_sends_authorization_when_key_is_configured():
    config = SearchProviderConfig(
        name="firecrawl_search",
        provider_type="search_with_inline_content",
        vendor="firecrawl",
        base_url="https://api.firecrawl.dev",
        api_key="fc-test-key",
        timeout_seconds=30,
        enabled=True,
        simulate=False,
    )
    provider = FirecrawlSearchProvider(config)

    request = provider.build_request("hello", limit=3)

    assert request.headers["Authorization"] == "Bearer fc-test-key"


def test_bocha_request_includes_default_options():
    config = SearchProviderConfig(
        name="bocha_search",
        provider_type="search_with_inline_content",
        vendor="bocha",
        base_url="https://api.bochaai.com",
        api_key="test-key",
        timeout_seconds=30,
        enabled=True,
        simulate=True,
        default_options={"freshness": "oneDay", "summary": True},
    )
    provider = BochaSearchProvider(config)

    request = provider.build_request("hello", limit=3)

    assert request.url.endswith("/v1/web-search")
    assert request.json_body["query"] == "hello"
    assert request.json_body["count"] == 3
    assert request.json_body["freshness"] == "oneDay"
    assert request.json_body["summary"] is True


def test_openai_web_search_provider_builds_responses_request():
    config = SearchProviderConfig(
        name="gpt_search",
        provider_type="model_embedded_search",
        vendor="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        enabled=True,
        simulate=True,
        default_options={
            "api_mode": "responses",
            "model": "gpt-5.5",
            "tools": [{"type": "web_search"}],
            "reasoning": {"effort": "low", "summary": "detailed"},
        },
    )

    provider = OpenAIWebSearchProvider(config)
    request = provider.build_request("hello", limit=3)

    assert request.url.endswith("/responses")
    assert request.json_body["model"] == "gpt-5.5"
    assert request.json_body["tools"][0]["type"] == "web_search"
    assert request.json_body["tool_choice"] == "required"
    assert "Return up to 3" in request.json_body["input"]


def test_grok_search_provider_builds_responses_request_and_normalizes_tools():
    config = SearchProviderConfig(
        name="grok_search",
        provider_type="model_embedded_search",
        vendor="grok",
        base_url="https://api.x.ai/v1",
        api_key="test-key",
        timeout_seconds=60,
        enabled=True,
        simulate=True,
        default_options={
            "model": "grok-4.3",
            "tools": [{"type": "web_search", "name": "web_search"}],
        },
    )

    provider = GrokSearchProvider(config)
    request = provider.build_request("hello", limit=3)

    assert request.url.endswith("/responses")
    assert request.json_body["model"] == "grok-4.3"
    assert request.json_body["tools"] == [{"type": "web_search"}]
    assert request.json_body["input"][0]["role"] == "user"
    assert "Return up to 3" in request.json_body["input"][0]["content"]


def test_openai_web_search_provider_builds_chat_completions_search_request():
    config = SearchProviderConfig(
        name="gpt_search",
        provider_type="model_embedded_search",
        vendor="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        enabled=True,
        simulate=True,
        default_options={
            "api_mode": "chat_completions",
            "model": "gpt-5-search-api",
            "web_search_options": {"search_context_size": "low"},
        },
    )

    provider = OpenAIWebSearchProvider(config)
    request = provider.build_request("hello", limit=3)

    assert request.url.endswith("/chat/completions")
    assert request.json_body["model"] == "gpt-5-search-api"
    assert request.json_body["web_search_options"]["search_context_size"] == "low"
    assert "tools" not in request.json_body


def test_openai_web_search_provider_parses_structured_results():
    config = SearchProviderConfig(
        name="gpt_search",
        provider_type="model_embedded_search",
        vendor="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        enabled=True,
        simulate=True,
    )
    provider = OpenAIWebSearchProvider(config)

    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "text": (
                            '{"results":[{"title":"T1","url":"https://openai.com/index/a",'
                            '"content":"C1","releaseDate":"2026-05-12","author":"OpenAI",'
                            '"sourceType":"official","publisher":"OpenAI","language":"en","regionHint":"global"}]}'
                        )
                    }
                ],
            }
        ]
    }

    bundle = provider.parse_response("q", payload, limit=5)

    assert bundle.hits[0].title == "T1"
    assert bundle.hits[0].source_domain == "openai.com"
    assert bundle.hits[0].source_type == "official"
    assert bundle.hits[0].metadata["publisher"] == "OpenAI"
    assert bundle.hits[0].metadata["region_hint"] == "global"


def test_model_embedded_search_parses_citations_when_json_is_missing():
    config = SearchProviderConfig(
        name="gpt_search",
        provider_type="model_embedded_search",
        vendor="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        enabled=True,
        simulate=True,
    )
    provider = OpenAIWebSearchProvider(config)

    payload = {
        "output_text": "A concise answer with citations.",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "A concise answer with citations.",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://platform.openai.com/docs/guides/tools-web-search",
                                "title": "Web search",
                            }
                        ],
                    }
                ],
            }
        ],
    }

    bundle = provider.parse_response("q", payload, limit=5)

    assert bundle.hits[0].title == "Web search"
    assert bundle.hits[0].source_domain == "platform.openai.com"
    assert bundle.hits[0].source_type == "web_search"


def test_gemini_search_provider_parses_grounding_chunks_when_json_is_missing():
    config = SearchProviderConfig(
        name="gemini_search",
        provider_type="model_embedded_search",
        vendor="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key="test-key",
        timeout_seconds=60,
        enabled=True,
        simulate=True,
    )
    provider = GeminiSearchProvider(config)

    payload = {
        "candidates": [
            {
                "content": {"parts": [{"text": "Grounded answer"}]},
                "groundingMetadata": {
                    "webSearchQueries": ["official docs"],
                    "groundingChunks": [
                        {
                            "web": {
                                "uri": "https://ai.google.dev/gemini-api/docs/google-search",
                                "title": "Google Search grounding",
                            }
                        }
                    ],
                },
            }
        ]
    }

    bundle = provider.parse_response("q", payload, limit=5)

    assert bundle.hits[0].title == "Google Search grounding"
    assert bundle.hits[0].source_domain == "ai.google.dev"
    assert bundle.hits[0].metadata["web_search_queries"] == ["official docs"]


def test_llm_providers_build_expected_requests():
    openai_provider = LLMProviderConfig(
        name="openai_primary",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        simulate=True,
    )
    anthropic_provider = LLMProviderConfig(
        name="anthropic_primary",
        provider_type="anthropic",
        base_url="https://api.anthropic.com",
        api_key="test-key",
        timeout_seconds=60,
        simulate=True,
    )
    openai_profile = LLMProfileConfig(
        name="cheap_structured_cn",
        provider="openai_primary",
        model="gpt-4.1-mini",
        temperature=0.1,
        max_tokens=4000,
        structured_output=True,
        fallback_profiles=[],
        default_options={},
    )
    anthropic_profile = LLMProfileConfig(
        name="advanced_reasoning_cn",
        provider="anthropic_primary",
        model="claude-sonnet",
        temperature=0.2,
        max_tokens=8000,
        structured_output=False,
        fallback_profiles=["cheap_structured_cn"],
        default_options={},
    )

    openai = OpenAIProvider(openai_provider, openai_profile)
    anthropic = AnthropicProvider(anthropic_provider, anthropic_profile)

    openai_request = openai.build_request("hello")
    anthropic_request = anthropic.build_request("hello")

    assert openai_request.url.endswith("/responses")
    assert openai_request.json_body["model"] == "gpt-4.1-mini"
    assert anthropic_request.url.endswith("/v1/messages")
    assert anthropic_request.json_body["model"] == "claude-sonnet"
    assert anthropic_request.json_body["temperature"] == 0.2


def test_openai_chat_completions_request_includes_profile_runtime_parameters():
    openai_provider = LLMProviderConfig(
        name="openai_primary",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        simulate=True,
    )
    openai_profile = LLMProfileConfig(
        name="advanced_reasoning_cn",
        provider="openai_primary",
        model="gpt-5.4",
        temperature=0.2,
        max_tokens=8000,
        structured_output=False,
        fallback_profiles=[],
        default_options={"api_mode": "chat_completions"},
    )

    openai = OpenAIProvider(openai_provider, openai_profile)
    request = openai.build_request("hello")

    assert request.url.endswith("/chat/completions")
    assert request.json_body["model"] == "gpt-5.4"
    assert request.json_body["temperature"] == 0.2
    assert request.json_body["max_tokens"] == 8000


def test_openai_chat_completions_request_allows_stream_override():
    openai_provider = LLMProviderConfig(
        name="openai_primary",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        simulate=True,
    )
    openai_profile = LLMProfileConfig(
        name="advanced_reasoning_cn",
        provider="openai_primary",
        model="gpt-5.4",
        temperature=0.2,
        max_tokens=8000,
        structured_output=False,
        fallback_profiles=[],
        default_options={"api_mode": "chat_completions", "stream": True},
    )

    openai = OpenAIProvider(openai_provider, openai_profile)
    request = openai.build_request("hello")

    assert request.json_body["stream"] is True


def test_openai_generate_captures_raw_http_exchange(monkeypatch):
    openai_provider = LLMProviderConfig(
        name="openai_primary",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        simulate=False,
    )
    openai_profile = LLMProfileConfig(
        name="advanced_reasoning_cn",
        provider="openai_primary",
        model="gpt-5.4",
        temperature=0.2,
        max_tokens=8000,
        structured_output=False,
        fallback_profiles=[],
        default_options={"api_mode": "chat_completions"},
    )

    openai = OpenAIProvider(openai_provider, openai_profile)

    def fake_execute(request):
        return ProviderResponse(
            status_code=504,
            payload={"error": {"message": "openai_error"}},
            headers={"content-type": "application/json"},
            raw_text='{"error":{"message":"openai_error"}}',
            request_snapshot={
                "method": request.method,
                "url": request.url,
                "headers": {"Authorization": "***redacted***"},
                "json_body": request.json_body,
                "params": request.params,
            },
            response_snapshot={
                "status_code": 504,
                "headers": {"content-type": "application/json"},
                "body_text": '{"error":{"message":"openai_error"}}',
                "parsed_payload": {"error": {"message": "openai_error"}},
            },
        )

    monkeypatch.setattr(openai.http_client, "execute", fake_execute)

    text = openai.generate("hello")

    assert text == ""
    assert openai.last_request_snapshot["url"].endswith("/chat/completions")
    assert openai.last_request_snapshot["headers"]["Authorization"] == "***redacted***"
    assert openai.last_response_snapshot["status_code"] == 504
    assert "openai_error" in openai.last_response_snapshot["body_text"]


def test_openai_parse_response_text_supports_streaming_chat_completions_sse():
    provider = LLMProviderConfig(
        name="openai_primary",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        simulate=True,
    )
    profile = LLMProfileConfig(
        name="advanced_reasoning_cn",
        provider="openai_primary",
        model="gpt-5.4",
        temperature=0.2,
        max_tokens=8000,
        structured_output=False,
        fallback_profiles=[],
        default_options={"api_mode": "chat_completions", "stream": True},
    )
    openai = OpenAIProvider(provider, profile)

    payload = "\n".join(
        [
            'data: {"choices":[{"delta":{"role":"assistant","content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" world"}}]}',
            'data: {"choices":[{"finish_reason":"stop"}]}',
            'data: [DONE]',
        ]
    )

    assert openai.parse_response_text(payload) == "Hello world"


def test_anthropic_request_can_carry_web_search_options():
    provider = LLMProviderConfig(
        name="anthropic_primary",
        provider_type="anthropic",
        base_url="https://api.anthropic.com",
        api_key="test-key",
        timeout_seconds=60,
        simulate=True,
    )
    profile = LLMProfileConfig(
        name="claude_opus_web_search_optional",
        provider="anthropic_primary",
        model="claude-opus-4-7",
        temperature=0.2,
        max_tokens=8000,
        structured_output=False,
        fallback_profiles=[],
        default_options={
            "system": "system prompt",
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": "high"},
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        },
    )
    anthropic = AnthropicProvider(provider, profile)

    request = anthropic.build_request("hello")

    assert request.json_body["model"] == "claude-opus-4-7"
    assert request.json_body["system"] == "system prompt"
    assert request.json_body["thinking"]["type"] == "adaptive"
    assert request.json_body["tools"][0]["type"] == "web_search_20250305"


def test_search_provider_response_parsers():
    exa = ExaSearchProvider(_search_config("exa", "exa_search", "https://api.exa.ai"))
    tavily = TavilySearchProvider(_search_config("tavily", "tavily_search", "https://api.tavily.com"))
    firecrawl = FirecrawlSearchProvider(_search_config("firecrawl", "firecrawl_search", "https://api.firecrawl.dev"))
    tinyfish = TinyFishSearchProvider(_search_config("tinyfish", "tinyfish_search", "https://api.search.tinyfish.ai"))
    bocha = BochaSearchProvider(_search_config("bocha", "bocha_search", "https://api.bochaai.com"))
    gemini = GeminiSearchProvider(_search_config("gemini", "gemini_search", "https://generativelanguage.googleapis.com/v1beta"))

    exa_bundle = exa.parse_response("q", {"results": [{"title": "T1", "url": "https://exa.example.com/a", "publishedDate": "2026-01-01", "summary": "S"}]}, limit=5)
    tavily_bundle = tavily.parse_response("q", {"results": [{"title": "T2", "url": "https://tavily.example.com/b", "content": "C"}]}, limit=5)
    firecrawl_bundle = firecrawl.parse_response(
        "q",
        {
            "data": {
                "web": [
                    {
                        "title": "T3",
                        "url": "https://firecrawl.example.com/c",
                        "description": "D",
                        "markdown": "# Full Firecrawl body",
                        "metadata": {"statusCode": 200},
                    }
                ]
            }
        },
        limit=5,
    )
    tinyfish_bundle = tinyfish.parse_response("q", {"results": [{"title": "T4", "site_name": "tinyfish.example.com", "snippet": "S4", "url": "https://tinyfish.example.com/d"}]}, limit=5)
    bocha_bundle = bocha.parse_response(
        "q",
        {
            "code": 200,
            "msg": "success",
            "data": {
                "webPages": {
                    "webSearchUrl": "https://bocha.example.com/search?q=q",
                    "totalEstimatedMatches": 10,
                    "value": [
                        {
                            "id": "bocha-1",
                            "name": "T5",
                            "url": "https://bocha.example.com/e",
                            "displayUrl": "bocha.example.com/e",
                            "snippet": "Snippet",
                            "summary": "Summary",
                            "datePublished": "2026-01-02",
                        }
                    ],
                }
            },
        },
        limit=5,
    )
    gemini_bundle = gemini.parse_response(
        "q",
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"results":[{"title":"T6","url":"https://gemini.example.com/e",'
                                    '"content":"S6","sourceType":"official"}]}'
                                )
                            }
                        ]
                    }
                }
            ]
        },
        limit=5,
    )

    assert exa_bundle.hits[0].published_at_utc == "2026-01-01"
    assert exa_bundle.hits[0].url == "https://exa.example.com/a"
    assert tavily_bundle.hits[0].snippet == "C"
    assert firecrawl_bundle.hits[0].metadata["statusCode"] == 200
    assert firecrawl_bundle.hits[0].snippet == "D"
    assert firecrawl_bundle.hits[0].metadata["inline_content_text"] == "# Full Firecrawl body"
    assert firecrawl_bundle.hits[0].metadata["inline_content_format"] == "markdown"
    assert tinyfish_bundle.hits[0].source_domain == "tinyfish.example.com"
    assert bocha_bundle.hits[0].title == "T5"
    assert bocha_bundle.hits[0].snippet == "Summary"
    assert bocha_bundle.hits[0].published_at_utc == "2026-01-02"
    assert bocha_bundle.request_metadata["total_estimated_matches"] == 10
    assert gemini_bundle.hits[0].title == "T6"


def test_fetch_and_llm_provider_response_parsers():
    fetch_config = SearchProviderConfig(
        name="firecrawl_scrape",
        provider_type="fetch_only",
        vendor="firecrawl",
        base_url="https://api.firecrawl.dev",
        api_key="test-key",
        timeout_seconds=60,
        enabled=True,
        simulate=True,
    )
    fetch_provider = FirecrawlFetchProvider(fetch_config)
    fetch_document = fetch_provider.parse_response(
        "https://example.com",
        {"data": {"markdown": "# Title", "metadata": {"url": "https://example.com", "sourceURL": "https://example.com", "title": "Page", "statusCode": 200}}},
    )

    openai_provider = LLMProviderConfig(
        name="openai_primary",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        timeout_seconds=60,
        simulate=True,
    )
    openai_profile = LLMProfileConfig(
        name="cheap_structured_cn",
        provider="openai_primary",
        model="gpt-4.1-mini",
        temperature=0.1,
        max_tokens=4000,
        structured_output=True,
        fallback_profiles=[],
    )
    openai = OpenAIProvider(openai_provider, openai_profile)
    anthropic_provider = LLMProviderConfig(
        name="anthropic_primary",
        provider_type="anthropic",
        base_url="https://api.anthropic.com",
        api_key="test-key",
        timeout_seconds=60,
        simulate=True,
    )
    anthropic_profile = LLMProfileConfig(
        name="advanced_reasoning_cn",
        provider="anthropic_primary",
        model="claude-sonnet",
        temperature=0.2,
        max_tokens=8000,
        structured_output=False,
        fallback_profiles=[],
    )
    anthropic = AnthropicProvider(anthropic_provider, anthropic_profile)

    openai_text = openai.parse_response_text({"output": [{"content": [{"text": "hello"}]}]})
    anthropic_text = anthropic.parse_response_text({"content": [{"text": "world"}]})

    assert fetch_document.title == "Page"
    assert fetch_document.content_text == "# Title"
    assert openai_text == "hello"
    assert anthropic_text == "world"
