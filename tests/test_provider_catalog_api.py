def test_provider_catalog_endpoints_return_configured_items(client):
    search_response = client.get("/api/v1/provider-catalog/search")
    fetch_response = client.get("/api/v1/provider-catalog/fetch")
    crawl_response = client.get("/api/v1/provider-catalog/crawl")
    llm_providers_response = client.get("/api/v1/provider-catalog/llm/providers")
    llm_profiles_response = client.get("/api/v1/provider-catalog/llm/profiles")
    source_registry_response = client.get("/api/v1/provider-catalog/source-registry")
    mcp_servers_response = client.get("/api/v1/provider-catalog/mcp/servers")

    assert search_response.status_code == 200
    assert fetch_response.status_code == 200
    assert crawl_response.status_code == 200
    assert llm_providers_response.status_code == 200
    assert llm_profiles_response.status_code == 200
    assert source_registry_response.status_code == 200
    assert mcp_servers_response.status_code == 200

    assert any(item["name"] == "exa_search" for item in search_response.json())
    assert any(item["name"] == "bocha_search" for item in search_response.json())
    assert any(item["name"] == "gemini_search" for item in search_response.json())
    assert any(item["name"] == "firecrawl_scrape" for item in fetch_response.json())
    assert any(item["name"] == "firecrawl_crawl" for item in crawl_response.json())
    assert any(item["name"] == "openai_primary" for item in llm_providers_response.json())
    assert any(item["name"] == "advanced_reasoning_cn" for item in llm_profiles_response.json())
    assert any(item["domain"] == "exa.example.com" for item in source_registry_response.json())
    assert any(item["name"] == "internal_tools" for item in mcp_servers_response.json())


def test_provider_catalog_search_test_endpoint_rejects_simulated_provider(client):
    response = client.post(
        "/api/v1/provider-catalog/search/test",
        json={"provider_name": "gemini_search", "query": "official docs", "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["provider"] == "gemini_search"
    assert payload["vendor"] == "gemini"
    assert payload["simulated"] is True
    assert "simulate=true" in payload["message"]
