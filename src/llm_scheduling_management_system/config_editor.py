from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from llm_scheduling_management_system.config_loader import resolve_config_path


class ConfigEditor:
    """配置文件编辑器。

    用途:
        用于读取和保存系统的各类 TOML 配置文件（搜索配置、LLM 配置、源注册配置、MCP 配置）。

    用法:
        实例化 ConfigEditor 后，调用相应的 get_* 或 save_* 方法来读取/修改配置。

    @Author: mosliu
    """

    def _read(self, path: Path) -> dict[str, Any]:
        """读取指定路径的 TOML 配置文件。

        用途:
            内部辅助方法，读取 TOML 文件并将其解析为字典格式。

        用法:
            self._read(Path("config.toml"))

        @Author: mosliu
        """
        if not path.exists():
            return {}
        with path.open("rb") as file:
            return tomllib.load(file)

    def _write(self, path: Path, data: dict[str, Any]) -> None:
        """向指定路径写入 TOML 配置文件。

        用途:
            内部辅助方法，将字典数据序列化为 TOML 格式并写入文件，若父目录不存在会自动创建。

        用法:
            self._write(Path("config.toml"), {"key": "value"})

        @Author: mosliu
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as file:
            file.write(tomli_w.dumps(data).encode("utf-8"))

    def get_search_config(self) -> tuple[str, dict[str, Any]]:
        """获取搜索配置文件的路径和数据内容。

        用途:
            读取搜索配置文件。优先读取真实配置文件，若不存在则回退读取样例配置文件。

        用法:
            path, data = editor.get_search_config()

        @Author: mosliu
        """
        path = resolve_config_path("config/search.toml", "config/search.example.toml")
        return str(path), self._read(path)

    def get_elasticsearch_config(self) -> tuple[str, dict[str, Any]]:
        """获取 Elasticsearch 配置文件的路径和数据内容。"""

        path = resolve_config_path("config/es.toml", "config/es.example.toml")
        return str(path), self._read(path)

    def save_search_config(self, data: dict[str, Any]) -> str:
        """保存搜索配置文件数据。

        用途:
            将传入的配置数据以 TOML 格式保存至真实搜索配置文件。

        用法:
            path = editor.save_search_config(data)

        @Author: mosliu
        """
        path = Path("config/search.toml")
        self._write(path, data)
        return str(path)

    def save_elasticsearch_config(self, data: dict[str, Any]) -> str:
        """保存 Elasticsearch 配置文件数据。"""

        path = Path("config/es.toml")
        self._write(path, data)
        return str(path)

    def get_llm_config(self) -> tuple[str, dict[str, Any]]:
        """获取 LLM 配置文件的路径和数据内容。

        用途:
            读取 LLM 配置文件。优先读取真实配置文件，若不存在则回退读取样例配置文件。

        用法:
            path, data = editor.get_llm_config()

        @Author: mosliu
        """
        path = resolve_config_path("config/llm.toml", "config/llm.example.toml")
        return str(path), self._read(path)

    def save_llm_config(self, data: dict[str, Any]) -> str:
        """保存 LLM 配置文件数据。

        用途:
            将传入的配置数据以 TOML 格式保存至真实 LLM 配置文件。

        用法:
            path = editor.save_llm_config(data)

        @Author: mosliu
        """
        path = Path("config/llm.toml")
        self._write(path, data)
        return str(path)

    def get_source_registry(self) -> tuple[str, dict[str, Any]]:
        """获取数据源注册配置文件的路径和数据内容。

        用途:
            读取源注册配置文件。优先读取真实配置文件，若不存在则回退读取样例配置文件。

        用法:
            path, data = editor.get_source_registry()

        @Author: mosliu
        """
        path = resolve_config_path("config/source_registry.toml", "config/source_registry.example.toml")
        return str(path), self._read(path)

    def save_source_registry(self, data: dict[str, Any]) -> str:
        """保存数据源注册配置文件数据。

        用途:
            将传入的配置数据以 TOML 格式保存至真实数据源注册配置文件。

        用法:
            path = editor.save_source_registry(data)

        @Author: mosliu
        """
        path = Path("config/source_registry.toml")
        self._write(path, data)
        return str(path)

    def get_mcp_config(self) -> tuple[str, dict[str, Any]]:
        """获取 MCP 配置文件的路径和数据内容。

        用途:
            读取 MCP 配置文件。优先读取真实配置文件，若不存在则回退读取样例配置文件。

        用法:
            path, data = editor.get_mcp_config()

        @Author: mosliu
        """
        path = resolve_config_path("config/mcp.toml", "config/mcp.example.toml")
        return str(path), self._read(path)

    def save_mcp_config(self, data: dict[str, Any]) -> str:
        """保存 MCP 配置文件数据。

        用途:
            将传入的配置数据以 TOML 格式保存至真实 MCP 配置文件。

        用法:
            path = editor.save_mcp_config(data)

        @Author: mosliu
        """
        path = Path("config/mcp.toml")
        self._write(path, data)
        return str(path)
