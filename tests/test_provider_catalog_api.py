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
    assert any(item["name"] == "firecrawl_scrape" for item in fetch_response.json())
    assert any(item["name"] == "firecrawl_crawl" for item in crawl_response.json())
    assert any(item["name"] == "openai_primary" for item in llm_providers_response.json())
    assert any(item["name"] == "advanced_reasoning_cn" for item in llm_profiles_response.json())
    assert any(item["domain"] == "exa.example.com" for item in source_registry_response.json())
    assert any(item["name"] == "internal_tools" for item in mcp_servers_response.json())
