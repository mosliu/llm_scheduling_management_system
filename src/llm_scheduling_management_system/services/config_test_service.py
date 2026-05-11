from __future__ import annotations

from llm_scheduling_management_system.config_models import LLMConfig, MCPConfig, SearchConfig
from llm_scheduling_management_system.mcp.client import MCPClient
from llm_scheduling_management_system.providers.factory import LLMProviderFactory, SearchProviderFactory


class ConfigTestService:
    def test_search_config(self, config: SearchConfig) -> dict:
        factory = SearchProviderFactory(config=config)
        results = []
        for provider_cfg in config.providers:
            if not provider_cfg.enabled:
                continue
            provider = factory.build_provider_by_name(provider_cfg.name)
            if provider is None:
                results.append({"name": provider_cfg.name, "ok": False, "message": "provider not buildable"})
                continue
            try:
                bundle = provider.search("sanity check", limit=1)
                results.append(
                    {
                        "name": provider_cfg.name,
                        "ok": True,
                        "message": "search ok",
                        "result_count": len(bundle.hits),
                        "simulated": bundle.request_metadata.get("simulated", True),
                    }
                )
            except Exception as exc:  # pragma: no cover - network dependent
                results.append({"name": provider_cfg.name, "ok": False, "message": str(exc)})
        return {"results": results}

    def test_llm_config(self, config: LLMConfig) -> dict:
        factory = LLMProviderFactory(config=config)
        results = []
        for profile in config.profiles:
            try:
                provider = factory.build_profile_provider(profile.name)
                text = provider.generate("Reply with OK only.")
                results.append(
                    {
                        "profile": profile.name,
                        "ok": True,
                        "message": "llm ok",
                        "preview": text[:160],
                        "model": profile.model,
                    }
                )
            except Exception as exc:  # pragma: no cover - network dependent
                results.append({"profile": profile.name, "ok": False, "message": str(exc), "model": profile.model})
        return {"results": results}

    def test_mcp_config(self, config: MCPConfig) -> dict:
        results = []
        for server in config.servers:
            if not server.enabled:
                continue
            client = MCPClient(server)
            try:
                tool_name = "list_docs" if server.name == "internal_tools" else "ping"
                arguments = {"root": "docs", "pattern": "*.md"} if tool_name == "list_docs" else {}
                result = client.call_tool(tool_name, arguments)
                results.append(
                    {
                        "server": server.name,
                        "ok": result.status == "completed",
                        "message": result.status,
                        "tool": tool_name,
                    }
                )
            except Exception as exc:  # pragma: no cover - network dependent
                results.append({"server": server.name, "ok": False, "message": str(exc)})
        return {"results": results}
