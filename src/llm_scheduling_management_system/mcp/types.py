from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MCPToolCallResult:
    server_name: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    status: str = "completed"
