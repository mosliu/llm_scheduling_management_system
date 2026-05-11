from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from llm_scheduling_management_system.config_loader import resolve_config_path


class ConfigEditor:
    def _read(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("rb") as file:
            return tomllib.load(file)

    def _write(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as file:
            file.write(tomli_w.dumps(data).encode("utf-8"))

    def get_search_config(self) -> tuple[str, dict[str, Any]]:
        path = resolve_config_path("config/search.toml", "config/search.example.toml")
        return str(path), self._read(path)

    def save_search_config(self, data: dict[str, Any]) -> str:
        path = Path("config/search.toml")
        self._write(path, data)
        return str(path)

    def get_llm_config(self) -> tuple[str, dict[str, Any]]:
        path = resolve_config_path("config/llm.toml", "config/llm.example.toml")
        return str(path), self._read(path)

    def save_llm_config(self, data: dict[str, Any]) -> str:
        path = Path("config/llm.toml")
        self._write(path, data)
        return str(path)

    def get_source_registry(self) -> tuple[str, dict[str, Any]]:
        path = resolve_config_path("config/source_registry.toml", "config/source_registry.example.toml")
        return str(path), self._read(path)

    def save_source_registry(self, data: dict[str, Any]) -> str:
        path = Path("config/source_registry.toml")
        self._write(path, data)
        return str(path)

    def get_mcp_config(self) -> tuple[str, dict[str, Any]]:
        path = resolve_config_path("config/mcp.toml", "config/mcp.example.toml")
        return str(path), self._read(path)

    def save_mcp_config(self, data: dict[str, Any]) -> str:
        path = Path("config/mcp.toml")
        self._write(path, data)
        return str(path)
