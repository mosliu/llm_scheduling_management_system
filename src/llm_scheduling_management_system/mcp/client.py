from __future__ import annotations

import json
import subprocess

import httpx

from llm_scheduling_management_system.config_models import MCPServerConfig
from llm_scheduling_management_system.mcp.types import MCPToolCallResult


class MCPClient:
    """MCP 客户端类。

    用途:
        建立与特定 MCP 服务器的通信，并执行特定的工具。支持 http 和 stdio 传输机制，并支持模拟（Simulation）运行。

    用法:
        config = MCPServerConfig(...)
        client = MCPClient(config)
        result = client.call_tool("fetch_url", {"url": "http://example.com"})

    @Author: mosliu
    """

    def __init__(self, config: MCPServerConfig) -> None:
        """初始化 MCPClient 实例。

        用途:
            利用传入的服务器配置（MCPServerConfig）进行初始化。

        用法:
            client = MCPClient(config)

        @Author: mosliu
        """
        self.config = config

    def call_tool(self, tool_name: str, arguments: dict) -> MCPToolCallResult:
        """调用服务器上的指定工具。

        用途:
            根据配置的传输协议（HTTP/STDIO/SIMULATE），将参数序列化并发送至 MCP 服务器端以执行指定工具，并解析返回结果。

        用法:
            result = client.call_tool("calculate", {"expression": "1 + 1"})

        @Author: mosliu
        """
        if self.config.simulate:
            return MCPToolCallResult(
                server_name=self.config.name,
                tool_name=tool_name,
                arguments=arguments,
                response={
                    "simulated": True,
                    "server": self.config.name,
                    "tool": tool_name,
                    "arguments": arguments,
                },
            )

        if self.config.transport == "http":
            if not self.config.url:
                raise RuntimeError(f"MCP server {self.config.name} is missing url")
            payload = {"tool": tool_name, "arguments": arguments}
            response = httpx.post(self.config.url, json=payload, timeout=self.config.timeout_seconds)
            data = response.json() if "application/json" in response.headers.get("content-type", "") else {"text": response.text}
            return MCPToolCallResult(
                server_name=self.config.name,
                tool_name=tool_name,
                arguments=arguments,
                response=data,
                status="completed" if response.is_success else "failed",
            )

        if self.config.transport == "stdio":
            if not self.config.command:
                raise RuntimeError(f"MCP server {self.config.name} is missing command")
            payload = json.dumps({"tool": tool_name, "arguments": arguments})
            completed = subprocess.run(
                [self.config.command, *self.config.args],
                input=payload,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                check=False,
            )
            response = {"stdout": completed.stdout, "stderr": completed.stderr, "returncode": completed.returncode}
            return MCPToolCallResult(
                server_name=self.config.name,
                tool_name=tool_name,
                arguments=arguments,
                response=response,
                status="completed" if completed.returncode == 0 else "failed",
            )

        raise RuntimeError(f"Unsupported MCP transport: {self.config.transport}")
