from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MCPToolCallResult:
    """MCP 工具调用结果的数据类。

    用途:
        保存执行 MCP 服务器工具时的请求参数、响应结果和状态信息。

    用法:
        result = MCPToolCallResult(
            server_name="fetch_server",
            tool_name="fetch_url",
            arguments={"url": "http://example.com"},
            response={"content": "html..."},
            status="completed"
        )

    @Author: mosliu
    """
    server_name: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    status: str = "completed"
