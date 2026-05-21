import json

from llm_scheduling_management_system.config_models import LLMProfileConfig, LLMProviderConfig
from llm_scheduling_management_system.providers.http_client import HTTPProviderClient, ProviderRequest
from llm_scheduling_management_system.providers.interfaces import LLMProvider


class BaseConfiguredLLMProvider(LLMProvider):
    def __init__(self, provider: LLMProviderConfig, profile: LLMProfileConfig) -> None:
        self.provider = provider
        self.profile = profile
        self.http_client = HTTPProviderClient(provider.base_url, provider.timeout_seconds)
        self.last_request_snapshot: dict = {}
        self.last_response_snapshot: dict = {}

    def build_request(self, prompt: str) -> ProviderRequest:
        raise NotImplementedError

    def parse_response_text(self, response_payload) -> str:
        raise NotImplementedError

    def generate(self, prompt: str) -> str:
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
    @staticmethod
    def _extract_choice_text(choice: dict) -> str:
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
    def build_request(self, prompt: str) -> ProviderRequest:
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
        content = response_payload.get("content", []) if isinstance(response_payload, dict) else []
        for item in content:
            text = item.get("text")
            if text:
                return text
        return ""
