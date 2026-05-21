from llm_scheduling_management_system.config_loader import load_mcp_config
from llm_scheduling_management_system.mcp.client import MCPClient


class MCPRegistry:
    """MCP 注册中心类。

    用途:
        用于管理 MCP 服务器配置列表，获取特定服务配置，以及构建与 MCP 服务器通信的客户端实例。

    用法:
        registry = MCPRegistry()
        client = registry.build_client("my_server")

    @Author: mosliu
    """

    def __init__(self) -> None:
        """初始化 MCPRegistry 实例。

        用途:
            从系统配置文件加载最新的 MCP 服务配置。

        用法:
            registry = MCPRegistry()

        @Author: mosliu
        """
        self.config = load_mcp_config()

    def list_servers(self):
        """获取所有已配置的 MCP 服务器列表。

        用途:
            返回当前加载的全部 MCP 服务器配置（包括未启用的）。

        用法:
            servers = registry.list_servers()

        @Author: mosliu
        """
        return list(self.config.servers)

    def get_server(self, name: str):
        """获取指定名称且已启用的 MCP 服务器配置。

        用途:
            查找并返回匹配的已启用的 MCP 服务器配置，不存在或未启用时返回 None。

        用法:
            server_config = registry.get_server("fetch_server")

        @Author: mosliu
        """
        return next((server for server in self.config.servers if server.name == name and server.enabled), None)

    def build_client(self, server_name: str) -> MCPClient | None:
        """构建指定 MCP 服务器的客户端。

        用途:
            根据服务器名称获取其配置并实例化一个 MCPClient，用于连接和调用工具。

        用法:
            client = registry.build_client("fetch_server")

        @Author: mosliu
        """
        server = self.get_server(server_name)
        if server is None:
            return None
        return MCPClient(server)
