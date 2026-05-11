from __future__ import annotations

import json
from pathlib import Path
import sys


def list_docs(arguments: dict) -> dict:
    root = Path(arguments.get("root", "docs"))
    pattern = arguments.get("pattern", "*.md")
    files = [
        {
            "path": str(path).replace("\\", "/"),
            "name": path.name,
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(root.rglob(pattern))
        if path.is_file()
    ]
    return {
        "root": str(root).replace("\\", "/"),
        "pattern": pattern,
        "count": len(files),
        "files": files,
    }


TOOLS = {
    "list_docs": list_docs,
}


def main() -> None:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    tool_name = payload.get("tool")
    arguments = payload.get("arguments", {})
    if tool_name not in TOOLS:
        response = {
            "status": "failed",
            "error": f"Unknown tool: {tool_name}",
        }
    else:
        response = {
            "status": "completed",
            "tool": tool_name,
            "result": TOOLS[tool_name](arguments),
        }
    sys.stdout.write(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
