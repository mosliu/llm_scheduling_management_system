from pathlib import Path
import shutil


def test_configuration_endpoints_return_and_save_data(client):
    config_path = Path("config/search.toml")
    backup_path = Path("config/search.toml.bak-test")
    mcp_path = Path("config/mcp.toml")
    mcp_backup_path = Path("config/mcp.toml.bak-test")
    original_exists = config_path.exists()
    original_mcp_exists = mcp_path.exists()
    if config_path.exists():
        shutil.copyfile(config_path, backup_path)
    if mcp_path.exists():
        shutil.copyfile(mcp_path, mcp_backup_path)
    try:
        search_get = client.get("/api/v1/config/search")
        llm_get = client.get("/api/v1/config/llm")
        registry_get = client.get("/api/v1/config/source-registry")
        mcp_get = client.get("/api/v1/config/mcp")

        assert search_get.status_code == 200
        assert llm_get.status_code == 200
        assert registry_get.status_code == 200
        assert mcp_get.status_code == 200

        save_response = client.post(
            "/api/v1/config/search",
            json={"data": {"providers": [], "fetch_providers": [], "crawl_providers": [], "embedded_search_providers": [], "policy": {}}},
        )
        assert save_response.status_code == 200
        assert save_response.json()["saved"] is True
        mcp_save = client.post("/api/v1/config/mcp", json={"data": {"servers": []}})
        assert mcp_save.status_code == 200
        assert mcp_save.json()["saved"] is True
    finally:
        if backup_path.exists():
            shutil.move(backup_path, config_path)
        elif not original_exists and config_path.exists():
            config_path.unlink()
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
    assert payload["validated_model"] == "grok-4.20-beta"


def test_claude_model_note_endpoint(client):
    response = client.get("/api/v1/config/notes/claude-models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["compatible"] is True
    assert payload["validated_model"] == "claude-opus-4-7"
    assert payload["mode"] == "anthropic_messages"


def test_console_page_renders(client):
    response = client.get("/console")

    assert response.status_code == 200
    assert "Workflow Task Studio" in response.text
    assert "Selected Task" in response.text
