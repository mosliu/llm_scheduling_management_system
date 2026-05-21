from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from llm_scheduling_management_system.config_editor import ConfigEditor
from llm_scheduling_management_system.config_models import LLMConfig, MCPConfig, SearchConfig
from llm_scheduling_management_system.services.config_test_service import ConfigTestService

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigPayload(BaseModel):
    """配置有效负载数据模型。

    用途:
        在保存或测试配置的 API 请求中承载配置字典。

    用法:
        payload = ConfigPayload(data={"key": "value"})

    @Author: mosliu
    """
    data: dict


editor = ConfigEditor()
test_service = ConfigTestService()


@router.get("/search")
def get_search_config() -> dict:
    """获取当前的搜索服务配置。

    用途:
        从配置文件读取并返回当前已配置的搜索服务信息。

    用法:
        GET /api/v1/config/search

    @Author: mosliu
    """
    path, data = editor.get_search_config()
    return {"path": path, "data": data}


@router.post("/search")
def save_search_config(payload: ConfigPayload) -> dict:
    """保存搜索服务配置。

    用途:
        将客户端提交的搜索服务配置字典持久化写入配置文件。

    用法:
        POST /api/v1/config/search
        Body: ConfigPayload

    @Author: mosliu
    """
    path = editor.save_search_config(payload.data)
    return {"path": path, "saved": True}


@router.post("/search/test")
def test_search_config(payload: ConfigPayload) -> dict:
    """测试指定的搜索服务配置。

    用途:
        在不修改文件的情况下，临时验证所提交的搜索配置是否有效。

    用法:
        POST /api/v1/config/search/test
        Body: ConfigPayload

    @Author: mosliu
    """
    config = SearchConfig.model_validate(payload.data)
    return test_service.test_search_config(config)


@router.get("/llm")
def get_llm_config() -> dict:
    """获取当前的 LLM 服务配置。

    用途:
        从配置文件读取并返回当前已配置的 LLM 服务信息。

    用法:
        GET /api/v1/config/llm

    @Author: mosliu
    """
    path, data = editor.get_llm_config()
    return {"path": path, "data": data}


@router.post("/llm")
def save_llm_config(payload: ConfigPayload) -> dict:
    """保存 LLM 服务配置。

    用途:
        将客户端提交的 LLM 服务配置字典持久化写入配置文件。

    用法:
        POST /api/v1/config/llm
        Body: ConfigPayload

    @Author: mosliu
    """
    path = editor.save_llm_config(payload.data)
    return {"path": path, "saved": True}


@router.post("/llm/test")
def test_llm_config(payload: ConfigPayload) -> dict:
    """测试指定的 LLM 服务配置。

    用途:
        临时验证所提交的 LLM 服务配置（如 API 密钥、接口地址、模型可用性等）是否有效。

    用法:
        POST /api/v1/config/llm/test
        Body: ConfigPayload

    @Author: mosliu
    """
    config = LLMConfig.model_validate(payload.data)
    return test_service.test_llm_config(config)


@router.get("/source-registry")
def get_source_registry() -> dict:
    """获取当前信誉网站源配置。

    用途:
        读取当前的信誉网站列表配置及文件路径。

    用法:
        GET /api/v1/config/source-registry

    @Author: mosliu
    """
    path, data = editor.get_source_registry()
    return {"path": path, "data": data}


@router.post("/source-registry")
def save_source_registry(payload: ConfigPayload) -> dict:
    """保存信誉网站源配置。

    用途:
        保存传入的信誉网站配置字典。

    用法:
        POST /api/v1/config/source-registry
        Body: ConfigPayload

    @Author: mosliu
    """
    path = editor.save_source_registry(payload.data)
    return {"path": path, "saved": True}


@router.get("/mcp")
def get_mcp_config() -> dict:
    """获取当前的 MCP 服务配置。

    用途:
        读取已配置的 MCP 服务器列表和参数。

    用法:
        GET /api/v1/config/mcp

    @Author: mosliu
    """
    path, data = editor.get_mcp_config()
    return {"path": path, "data": data}


@router.post("/mcp")
def save_mcp_config(payload: ConfigPayload) -> dict:
    """保存 MCP 服务配置。

    用途:
        持久化保存 MCP 服务器的配置信息。

    用法:
        POST /api/v1/config/mcp
        Body: ConfigPayload

    @Author: mosliu
    """
    path = editor.save_mcp_config(payload.data)
    return {"path": path, "saved": True}


@router.post("/mcp/test")
def test_mcp_config(payload: ConfigPayload) -> dict:
    """测试指定的 MCP 服务配置。

    用途:
        测试给定的 MCP 服务器配置，检查通信是否正常。

    用法:
        POST /api/v1/config/mcp/test
        Body: ConfigPayload

    @Author: mosliu
    """
    config = MCPConfig.model_validate(payload.data)
    return test_service.test_mcp_config(config)


@router.get("/notes/grok-search")
def get_grok_search_note() -> dict:
    """获取 Grok 搜索的兼容性备注。

    用途:
        获取关于 Grok 搜索服务集成与验证的说明信息。

    用法:
        GET /api/v1/config/notes/grok-search

    @Author: mosliu
    """
    return {
        "compatible": True,
        "mode": "model_embedded_search",
        "validated_model": "grok-4.20-beta",
        "note": "Grok should be configured as model-embedded search, not as a standalone search provider. The relay currently validates grok-4.20-beta.",
    }


@router.get("/notes/claude-models")
def get_claude_model_note() -> dict:
    """获取 Claude 模型的兼容性备注。

    用途:
        获取关于 Claude 模型在当前网关中验证与兼容的特别提示。

    用法:
        GET /api/v1/config/notes/claude-models

    @Author: mosliu
    """
    return {
        "compatible": True,
        "validated_model": "claude-opus-4-7",
        "unsupported_models": ["claude-opus-4.7", "claude-4.6", "claude-sonnet-4-5"],
        "mode": "anthropic_messages",
        "note": "The current relay validates claude-opus-4-7 via /v1/messages. The tested claude-4.6-style names were not available on this relay.",
    }
