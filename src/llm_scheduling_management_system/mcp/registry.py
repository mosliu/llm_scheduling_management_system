from llm_scheduling_management_system.config_loader import load_mcp_config
from llm_scheduling_management_system.mcp.client import MCPClient


class MCPRegistry:
    def __init__(self) -> None:
        self.config = load_mcp_config()

    def list_servers(self):
        return list(self.config.servers)

    def get_server(self, name: str):
        return next((server for server in self.config.servers if server.name == name and server.enabled), None)

    def build_client(self, server_name: str) -> MCPClient | None:
        server = self.get_server(server_name)
        if server is None:
            return None
        return MCPClient(server)
