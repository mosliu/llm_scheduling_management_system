from pathlib import Path
import shutil


def test_configuration_endpoints_return_and_save_data(client):
    config_path = Path("config/search.toml")
    backup_path = Path("config/search.toml.bak-test")
    es_path = Path("config/es.toml")
    es_backup_path = Path("config/es.toml.bak-test")
    mcp_path = Path("config/mcp.toml")
    mcp_backup_path = Path("config/mcp.toml.bak-test")
    original_exists = config_path.exists()
    original_es_exists = es_path.exists()
    original_mcp_exists = mcp_path.exists()
    if config_path.exists():
        shutil.copyfile(config_path, backup_path)
    if es_path.exists():
        shutil.copyfile(es_path, es_backup_path)
    if mcp_path.exists():
        shutil.copyfile(mcp_path, mcp_backup_path)
    try:
        search_get = client.get("/api/v1/config/search")
        es_get = client.get("/api/v1/config/es")
        llm_get = client.get("/api/v1/config/llm")
        registry_get = client.get("/api/v1/config/source-registry")
        mcp_get = client.get("/api/v1/config/mcp")

        assert search_get.status_code == 200
        assert es_get.status_code == 200
        assert llm_get.status_code == 200
        assert registry_get.status_code == 200
        assert mcp_get.status_code == 200

        save_response = client.post(
            "/api/v1/config/search",
            json={"data": {"providers": [], "fetch_providers": [], "crawl_providers": [], "embedded_search_providers": [], "policy": {}}},
        )
        assert save_response.status_code == 200
        assert save_response.json()["saved"] is True
        es_save = client.post(
            "/api/v1/config/es",
            json={
                "data": {
                    "base_url": "http://localhost:9200",
                    "simulate": True,
                    "version": "7.10",
                    "index_prefix": "qb",
                    "default_index_sequence": 1,
                    "default_mappings_path": "docs/es_mappings.json",
                    "analysis_llm_profile": "cheap_structured_cn",
                    "fallback_search_month_window": 3,
                    "date_field": "release_date",
                    "default_search_fields": ["title^4", "content^3"],
                }
            },
        )
        assert es_save.status_code == 200
        assert es_save.json()["saved"] is True
        mcp_save = client.post("/api/v1/config/mcp", json={"data": {"servers": []}})
        assert mcp_save.status_code == 200
        assert mcp_save.json()["saved"] is True
    finally:
        if backup_path.exists():
            shutil.move(backup_path, config_path)
        elif not original_exists and config_path.exists():
            config_path.unlink()
        if es_backup_path.exists():
            shutil.move(es_backup_path, es_path)
        elif not original_es_exists and es_path.exists():
            es_path.unlink()
        if mcp_backup_path.exists():
            shutil.move(mcp_backup_path, mcp_path)
        elif not original_mcp_exists and mcp_path.exists():
            mcp_path.unlink()


def test_grok_search_note_endpoint(client):
    response = client.get("/api/v1/config/notes/grok-search")

    assert response.status_code == 200
    payload = response.json()
    assert payload["compatible"] is True
    assert payload["mode"] == "model_embedded_search"
    assert payload["validated_model"] == "grok-4.3"
    assert payload["endpoint"] == "/v1/responses"


def test_claude_model_note_endpoint(client):
    response = client.get("/api/v1/config/notes/claude-models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["compatible"] is True
    assert payload["validated_model"] == "claude-opus-4-7"
    assert payload["mode"] == "anthropic_messages"


def test_elasticsearch_config_test_endpoint(client):
    response = client.post(
        "/api/v1/config/es/test",
        json={
            "data": {
                "base_url": "http://localhost:9200",
                "simulate": True,
                "version": "7.10",
                "index_prefix": "qb",
                "default_index_sequence": 1,
                "default_mappings_path": "docs/es_mappings.json",
                "analysis_llm_profile": "cheap_structured_cn",
                "fallback_search_month_window": 3,
                "date_field": "release_date",
                "default_search_fields": ["title^4", "content^3"],
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["compatible"] is True
    assert payload["version"] == "7.10.0"


def test_console_page_renders(client):
    response = client.get("/console")

    assert response.status_code == 200
    assert "Workflow Task Studio" in response.text
    assert "Selected Task" in response.text
    assert "Search Provider Test" in response.text
