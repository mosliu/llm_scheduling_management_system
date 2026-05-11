from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class ProviderRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    params: dict[str, Any] | None = None


@dataclass(slots=True)
class ProviderResponse:
    status_code: int
    payload: Any
    headers: dict[str, Any] = field(default_factory=dict)


class HTTPProviderClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def create_client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_seconds)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        with self.create_client() as client:
            response = client.request(
                method=request.method,
                url=request.url,
                headers=request.headers,
                json=request.json_body,
                params=request.params,
            )
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            return ProviderResponse(
                status_code=response.status_code,
                payload=payload,
                headers=dict(response.headers),
            )
