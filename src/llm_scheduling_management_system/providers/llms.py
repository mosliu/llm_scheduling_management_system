import json

from llm_scheduling_management_system.config_models import LLMProfileConfig, LLMProviderConfig
from llm_scheduling_management_system.providers.http_client import HTTPProviderClient, ProviderRequest
from llm_scheduling_management_system.providers.interfaces import LLMProvider


class BaseConfiguredLLMProvider(LLMProvider):
    """基于配置的基础大语言模型提供商抽象类。

    用途:
        提供共享的LLM请求发送、响应记录、错误记录以及模拟模式的通用实现，是具体LLM提供商的基类。

    用法:
        继承自此类并实现 build_request 和 parse_response_text 方法。

    @Author: mosliu
    """
    def __init__(self, provider: LLMProviderConfig, profile: LLMProfileConfig) -> None:
        """初始化基础配置化大语言模型提供商。

        用途:
            设置大语言模型提供商的配置和模型配置文件，并初始化内部 HTTP 客户端及请求/响应快照。

        用法:
            provider = BaseConfiguredLLMProvider(provider_config, profile_config)

        @Author: mosliu
        """
        self.provider = provider
        self.profile = profile
        self.http_client = HTTPProviderClient(provider.base_url, provider.timeout_seconds)
        self.last_request_snapshot: dict = {}
        self.last_response_snapshot: dict = {}

    def build_request(self, prompt: str) -> ProviderRequest:
        """构建请求对象。

        用途:
            根据提示词和提供商配置生成具体的 ProviderRequest 对象。子类必须实现此方法。

        用法:
            request = provider.build_request("Hello")

        @Author: mosliu
        """
        raise NotImplementedError

    def parse_response_text(self, response_payload) -> str:
        """解析响应文本。

        用途:
            将服务返回的原始响应载荷解析为最终生成的字符串。子类必须实现此方法。

        用法:
            text = provider.parse_response_text(response_payload)

        @Author: mosliu
        """
        raise NotImplementedError

    def generate(self, prompt: str) -> str:
        """生成大语言模型文本。

        用途:
            执行生成逻辑。在模拟模式下直接返回模拟生成文本，在真实请求模式下，构建请求并执行，然后解析并返回结果，并更新请求和响应快照。

        用法:
            result = provider.generate("请介绍一下 Python。")

        @Author: mosliu
        """
        request = self.build_request(prompt)
        if not self.provider.simulate:
            self.last_request_snapshot = {
                "method": request.method,
                "url": request.url,
                "headers": self.http_client._sanitize_headers(request.headers),
                "json_body": request.json_body,
                "params": request.params,
            }
            try:
                response = self.http_client.execute(request)
            except Exception as exc:
                self.last_response_snapshot = {
                    "error": str(exc),
                }
                raise
            self.last_request_snapshot = response.request_snapshot
            self.last_response_snapshot = response.response_snapshot
            return self.parse_response_text(response.payload)
        return (
            f"[{self.provider.name}/{self.profile.model}] simulated generation "
            f"for prompt: {prompt} via {request.method} {request.url}"
        )


class OpenAIProvider(BaseConfiguredLLMProvider):
    """OpenAI 风格大语言模型提供商适配器。

    用途:
        对接兼容 OpenAI 接口规范的 LLM 提供商（包括 OpenAI、DeepSeek 等），提供请求构建及流式/非流式响应解析。

    用法:
        provider = OpenAIProvider(provider_config, profile_config)
        result = provider.generate("你好")

    @Author: mosliu
    """
    @staticmethod
    def _extract_choice_text(choice: dict) -> str:
        """提取 Choice 结构中的文本内容。

        用途:
            从返回的单个 choice 中安全地提取文本，兼容 message.content 和 delta.content 的普通文本及多模态 text_parts 格式。

        用法:
            text = OpenAIProvider._extract_choice_text(choice)

        @Author: mosliu
        """
        message = choice.get("message") if isinstance(choice, dict) else None
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        text_parts.append(item["text"])
                return "".join(text_parts)

        delta = choice.get("delta") if isinstance(choice, dict) else None
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        text_parts.append(item["text"])
                return "".join(text_parts)
        return ""

    def build_request(self, prompt: str) -> ProviderRequest:
        """构建 OpenAI 兼容的 HTTP 请求对象。

        用途:
            支持根据 API 模式（如 chat_completions 或 responses）构造对应的 API 请求载荷和 HTTP 头部。

        用法:
            request = provider.build_request("Hello")

        @Author: mosliu
        """
        api_mode = self.profile.default_options.get("api_mode", "responses")
        if api_mode == "chat_completions":
            json_body = {
                "model": self.profile.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": self.profile.temperature,
                "max_tokens": self.profile.max_tokens,
                **{k: v for k, v in self.profile.default_options.items() if k != "api_mode"},
            }
            return ProviderRequest(
                method="POST",
                url=self.http_client.build_url("/chat/completions"),
                headers={"Authorization": f"Bearer {self.provider.api_key}", **self.provider.extra_headers},
                json_body=json_body,
            )
        json_body = {
            "model": self.profile.model,
            "input": prompt,
            "temperature": self.profile.temperature,
            "max_output_tokens": self.profile.max_tokens,
            **{k: v for k, v in self.profile.default_options.items() if k != "api_mode"},
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/responses"),
            headers={"Authorization": f"Bearer {self.provider.api_key}", **self.provider.extra_headers},
            json_body=json_body,
        )

    def parse_response_text(self, response_payload) -> str:
        """解析 OpenAI 兼容的 HTTP 响应体。

        用途:
            解析 OpenAI 格式的非流式（如 choices[].message.content）或流式（Server-Sent Events 格式）响应负载，并合并为完整的文本。

        用法:
            text = provider.parse_response_text(response_payload)

        @Author: mosliu
        """
        if isinstance(response_payload, str):
            lines = [line.strip() for line in response_payload.splitlines() if line.strip().startswith("data:")]
            streamed_parts: list[str] = []
            for line in lines:
                payload = line[len("data:"):].strip()
                if payload == "[DONE]":
                    continue
                try:
                    parsed = json.loads(payload)
                    choices = parsed.get("choices")
                    if choices:
                        for choice in choices:
                            choice_text = self._extract_choice_text(choice)
                            if choice_text:
                                streamed_parts.append(choice_text)
                except Exception:
                    continue
            if streamed_parts:
                return "".join(streamed_parts)
        choices = response_payload.get("choices") if isinstance(response_payload, dict) else None
        if choices:
            try:
                collected = [self._extract_choice_text(choice) for choice in choices]
                text = "".join(part for part in collected if part)
                if text:
                    return text
            except Exception:
                pass
        output = response_payload.get("output", []) if isinstance(response_payload, dict) else []
        for item in output:
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return text
        return ""


class AnthropicProvider(BaseConfiguredLLMProvider):
    """Anthropic 风格大语言模型提供商适配器。

    用途:
        对接 Anthropic 格式的 LLM 提供商接口，提供请求构建及响应解析。

    用法:
        provider = AnthropicProvider(provider_config, profile_config)
        result = provider.generate("Hello")

    @Author: mosliu
    """
    def build_request(self, prompt: str) -> ProviderRequest:
        """构建 Anthropic 格式 of HTTP 请求对象。

        用途:
            为 Anthropic 模型服务（如 Claude）构造包含用户提示词和模型配置的请求载荷。

        用法:
            request = provider.build_request("Hello")

        @Author: mosliu
        """
        json_body = {
            "model": self.profile.model,
            "max_tokens": self.profile.max_tokens,
            "temperature": self.profile.temperature,
            "messages": [{"role": "user", "content": prompt}],
            **self.profile.default_options,
        }
        return ProviderRequest(
            method="POST",
            url=self.http_client.build_url("/v1/messages"),
            headers={"x-api-key": self.provider.api_key, **self.provider.extra_headers},
            json_body=json_body,
        )

    def parse_response_text(self, response_payload) -> str:
        """解析 Anthropic 格式的 HTTP 响应。

        用途:
            从 Anthropic API 返回的 payload.content 列表中提取文本段落。

        用法:
            text = provider.parse_response_text(response_payload)

        @Author: mosliu
        """
        content = response_payload.get("content", []) if isinstance(response_payload, dict) else []
        for item in content:
            text = item.get("text")
            if text:
                return text
        return ""
