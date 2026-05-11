from __future__ import annotations

import json
import subprocess

import httpx

from llm_scheduling_management_system.config_models import MCPServerConfig
from llm_scheduling_management_system.mcp.types import MCPToolCallResult


class MCPClient:
    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config

    def call_tool(self, tool_name: str, arguments: dict) -> MCPToolCallResult:
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
