from __future__ import annotations

from llm_scheduling_management_system.config_models import ElasticsearchConfig, LLMConfig, MCPConfig, SearchConfig
from llm_scheduling_management_system.mcp.client import MCPClient
from llm_scheduling_management_system.providers.factory import LLMProviderFactory, SearchProviderFactory
from llm_scheduling_management_system.services.elasticsearch_service import ElasticsearchService


class ConfigTestService:
    """配置连接测试服务类。

    用途:
        用于对各种配置（搜索服务商、大语言模型配置、MCP 服务器配置）进行可用性、连通性的校验与健康检查。

    用法:
        service = ConfigTestService()
        result = service.test_search_config(search_config)

    @Author: mosliu
    """

    @staticmethod
    def _simulation_disabled_message(provider_name: str) -> str:
        return (
            f"{provider_name} is configured with simulate=true; console/provider tests require a real search. "
            "Set simulate=false and configure the provider endpoint/key as needed."
        )

    def test_search_config(self, config: SearchConfig) -> dict:
        """测试搜索引擎的配置连通性。

        用途:
            遍历已启用的搜索供应商配置，使用 "sanity check" 关键词进行单条搜索尝试，返回测试结果明细字典。

        用法:
            res = service.test_search_config(config)

        @Author: mosliu
        """
        factory = SearchProviderFactory(config=config)
        results = []
        for provider_cfg in config.providers:
            if not provider_cfg.enabled:
                continue
            if provider_cfg.simulate:
                results.append(
                    {
                        "name": provider_cfg.name,
                        "ok": False,
                        "message": self._simulation_disabled_message(provider_cfg.name),
                        "simulated": True,
                    }
                )
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

    def test_search_provider(self, config: SearchConfig, provider_name: str, query: str, limit: int = 3) -> dict:
        """Test one configured search provider with a caller-supplied query."""

        factory = SearchProviderFactory(config=config)
        provider_cfg = next((item for item in config.providers if item.name == provider_name), None)
        if provider_cfg is None:
            return {"ok": False, "provider": provider_name, "message": "provider not configured"}
        if not provider_cfg.enabled:
            return {"ok": False, "provider": provider_name, "message": "provider disabled"}
        if provider_cfg.simulate:
            return {
                "ok": False,
                "provider": provider_name,
                "vendor": provider_cfg.vendor,
                "message": self._simulation_disabled_message(provider_name),
                "simulated": True,
            }
        provider = factory.build_provider_by_name(provider_name)
        if provider is None:
            return {"ok": False, "provider": provider_name, "message": "provider not buildable"}
        try:
            bundle = provider.search(query, limit=max(1, limit))
            return {
                "ok": True,
                "provider": provider_name,
                "vendor": provider_cfg.vendor,
                "query": query,
                "limit": limit,
                "result_count": len(bundle.hits),
                "request_metadata": bundle.request_metadata,
                "hits": [
                    {
                        "title": hit.title,
                        "url": hit.url,
                        "source_domain": hit.source_domain,
                        "source_type": hit.source_type,
                        "published_at_utc": hit.published_at_utc,
                        "snippet": hit.snippet,
                        "metadata": hit.metadata,
                    }
                    for hit in bundle.hits
                ],
            }
        except Exception as exc:  # pragma: no cover - network dependent
            return {"ok": False, "provider": provider_name, "vendor": provider_cfg.vendor, "message": str(exc)}

    def test_elasticsearch_config(self, config: ElasticsearchConfig) -> dict:
        """测试 Elasticsearch 配置连通性与版本兼容性。"""

        service = ElasticsearchService(config=config)
        return service.test_connection()

    def test_llm_config(self, config: LLMConfig) -> dict:
        """测试大语言模型 Profiles 的配置连通性。

        用途:
            遍历 LLM 配置中的所有 Profiles，利用 "Reply with OK only." 提示词生成单次回复测试连通性，并返回结果详情。

        用法:
            res = service.test_llm_config(config)

        @Author: mosliu
        """
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
        """测试 MCP (Model Context Protocol) 服务的配置连通性。

        用途:
            遍历启用的 MCP 服务器，尝试调用其特有工具（如 list_docs 或 ping），评估其就绪状态并返回测试报告。

        用法:
            res = service.test_mcp_config(config)

        @Author: mosliu
        """
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
