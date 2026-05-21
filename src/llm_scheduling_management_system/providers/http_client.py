from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class ProviderRequest:
    """提供商服务请求模型。

    用途:
        保存向外部 API 提供商发送 HTTP 请求时所需要的方法、网址、头信息、请求体与参数。

    用法:
        req = ProviderRequest(method="POST", url="http://example.com/api", json_body={"q": "test"})

    @Author: mosliu
    """
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    params: dict[str, Any] | None = None


@dataclass(slots=True)
class ProviderResponse:
    """提供商服务响应模型。

    用途:
        包含外部 API 响应的状态码、解析后的负载、响应头、原始文本以及请求和响应的脱敏快照。

    用法:
        resp = ProviderResponse(status_code=200, payload={"result": "ok"})

    @Author: mosliu
    """
    status_code: int
    payload: Any
    headers: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    request_snapshot: dict[str, Any] = field(default_factory=dict)
    response_snapshot: dict[str, Any] = field(default_factory=dict)


class HTTPProviderClient:
    """HTTP 服务提供商客户端。

    用途:
        提供调用外部 API (如 tavily, exa, llm) 的通用 HTTP 客户端封装，支持头信息脱敏、自动抓取快照并序列化响应。

    用法:
        client = HTTPProviderClient(base_url="https://api.tavily.com", timeout_seconds=10)
        resp = client.execute(req)

    @Author: mosliu
    """

    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        """初始化 HTTPProviderClient 实例。

        用途:
            配置请求基准 URL 和超时时间。

        用法:
            client = HTTPProviderClient("http://api.com", 30)

        @Author: mosliu
        """
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def build_url(self, path: str) -> str:
        """构造完整的请求 URL。

        用途:
            如果 path 不是以 http 开头的完整 URL，则将其与 base_url 拼接。

        用法:
            url = client.build_url("/search")

        @Author: mosliu
        """
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def create_client(self) -> httpx.Client:
        """创建 httpx.Client 实例。

        用途:
            返回一个带有超时设置的 httpx.Client，以便进行请求执行。

        用法:
            with client.create_client() as c:
                ...

        @Author: mosliu
        """
        return httpx.Client(timeout=self.timeout_seconds)

    @staticmethod
    def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
        """对请求头信息中的敏感字段进行掩码处理。

        用途:
            移除或替换头信息中的 Authorization 和 X-API-KEY 等密钥，以便记录安全的日志审计。

        用法:
            safe_headers = HTTPProviderClient._sanitize_headers(headers)

        @Author: mosliu
        """
        masked: dict[str, str] = {}
        for key, value in headers.items():
            lowered = key.lower()
            if lowered in {"authorization", "x-api-key"}:
                masked[key] = "***redacted***"
            else:
                masked[key] = value
        return masked

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        """执行 HTTP 请求并捕获快照。

        用途:
            向外部服务商发送请求，拦截并解析返回的数据，记录经过脱敏的请求和响应日志快照。

        用法:
            response = client.execute(request)

        @Author: mosliu
        """
        request_snapshot = {
            "method": request.method,
            "url": request.url,
            "headers": self._sanitize_headers(request.headers),
            "json_body": request.json_body,
            "params": request.params,
        }
        with self.create_client() as client:
            response = client.request(
                method=request.method,
                url=request.url,
                headers=request.headers,
                json=request.json_body,
                params=request.params,
            )
            raw_text = response.text
            try:
                payload = response.json()
            except ValueError:
                payload = raw_text
            response_snapshot = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body_text": raw_text,
                "parsed_payload": payload,
            }
            return ProviderResponse(
                status_code=response.status_code,
                payload=payload,
                headers=dict(response.headers),
                raw_text=raw_text,
                request_snapshot=request_snapshot,
                response_snapshot=response_snapshot,
            )
