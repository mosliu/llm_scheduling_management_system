from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from llm_scheduling_management_system.config_editor import ConfigEditor
from llm_scheduling_management_system.config_models import LLMConfig, MCPConfig, SearchConfig
from llm_scheduling_management_system.services.config_test_service import ConfigTestService

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigPayload(BaseModel):
    data: dict


editor = ConfigEditor()
test_service = ConfigTestService()


@router.get("/search")
def get_search_config() -> dict:
    path, data = editor.get_search_config()
    return {"path": path, "data": data}


@router.post("/search")
def save_search_config(payload: ConfigPayload) -> dict:
    path = editor.save_search_config(payload.data)
    return {"path": path, "saved": True}


@router.post("/search/test")
def test_search_config(payload: ConfigPayload) -> dict:
    config = SearchConfig.model_validate(payload.data)
    return test_service.test_search_config(config)


@router.get("/llm")
def get_llm_config() -> dict:
    path, data = editor.get_llm_config()
    return {"path": path, "data": data}


@router.post("/llm")
def save_llm_config(payload: ConfigPayload) -> dict:
    path = editor.save_llm_config(payload.data)
    return {"path": path, "saved": True}


@router.post("/llm/test")
def test_llm_config(payload: ConfigPayload) -> dict:
    config = LLMConfig.model_validate(payload.data)
    return test_service.test_llm_config(config)


@router.get("/source-registry")
def get_source_registry() -> dict:
    path, data = editor.get_source_registry()
    return {"path": path, "data": data}


@router.post("/source-registry")
def save_source_registry(payload: ConfigPayload) -> dict:
    path = editor.save_source_registry(payload.data)
    return {"path": path, "saved": True}


@router.get("/mcp")
def get_mcp_config() -> dict:
    path, data = editor.get_mcp_config()
    return {"path": path, "data": data}


@router.post("/mcp")
def save_mcp_config(payload: ConfigPayload) -> dict:
    path = editor.save_mcp_config(payload.data)
    return {"path": path, "saved": True}


@router.post("/mcp/test")
def test_mcp_config(payload: ConfigPayload) -> dict:
    config = MCPConfig.model_validate(payload.data)
    return test_service.test_mcp_config(config)


@router.get("/notes/grok-search")
def get_grok_search_note() -> dict:
    return {
        "compatible": True,
        "mode": "model_embedded_search",
        "validated_model": "grok-4.20-beta",
        "note": "Grok should be configured as model-embedded search, not as a standalone search provider. The relay currently validates grok-4.20-beta.",
    }


@router.get("/notes/claude-models")
def get_claude_model_note() -> dict:
    return {
        "compatible": True,
        "validated_model": "claude-opus-4-7",
        "unsupported_models": ["claude-opus-4.7", "claude-4.6", "claude-sonnet-4-5"],
        "mode": "anthropic_messages",
        "note": "The current relay validates claude-opus-4-7 via /v1/messages. The tested claude-4.6-style names were not available on this relay.",
    }
