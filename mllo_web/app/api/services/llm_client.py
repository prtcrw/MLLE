from abc import ABC, abstractmethod
from typing import Any

import httpx

from mllo_web.app.api.config import AppConfig


class LlmClient(ABC):
    """Abstract LLM chat-completions client."""

    def __init__(self, config: AppConfig):
        self.config = config

    def _build_params(self) -> dict[str, str]:
        if not self.config.llm_api_version:
            return {}

        return {
            self.config.llm_api_version_param: self.config.llm_api_version,
        }

    def _build_headers(self) -> dict[str, str]:
        if not self.config.llm_api_key:
            return {}

        prefix = self.config.llm_api_key_prefix or ""
        if prefix and not prefix.endswith(" "):
            prefix = f"{prefix} "

        return {
            self.config.llm_api_key_header: f"{prefix}{self.config.llm_api_key}",
        }

    @abstractmethod
    def _build_url(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def _build_payload(self, messages: list[dict]) -> dict[str, Any]:
        raise NotImplementedError

    def _extract_error_message(self, resp: httpx.Response) -> str:
        try:
            body = resp.json()
        except ValueError:
            text = (resp.text or "").strip()
            return text[:500] if text else f"HTTP {resp.status_code}"

        if isinstance(body, dict):
            # Common OpenAI/Azure style: {"error": {"message": "..."}}
            err = body.get("error")
            if isinstance(err, dict):
                msg = err.get("message")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
                code = err.get("code")
                if isinstance(code, str) and code.strip():
                    return code.strip()
            # Generic fallback fields
            for key in ("message", "detail", "error_description"):
                val = body.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()

        return str(body)[:500]

    async def chat_completion(self, messages: list[dict]) -> str:
        url = self._build_url()
        headers = self._build_headers()
        params = self._build_params()
        payload = self._build_payload(messages)

        async with httpx.AsyncClient(timeout=self.config.llm_timeout_seconds) as client:
            resp = await client.post(
                url,
                params=params or None,
                headers=headers or None,
                json=payload,
            )

            if not resp.is_success:
                message = self._extract_error_message(resp)
                raise ValueError(f"LLM API error {resp.status_code}: {message}")

            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("LLM response missing choices.")

        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("LLM response missing message content.")

        return content.strip()


class OpenAICompatibleClient(LlmClient):
    """Client for OpenAI-compatible /chat/completions style APIs."""

    def _build_url(self) -> str:
        base = self.config.llm_base_url.rstrip("/")
        path = self.config.llm_chat_completions_path
        if not path.startswith("/"):
            path = "/" + path
        return f"{base}{path}"

    def _build_payload(self, messages: list[dict]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": self.config.llm_max_tokens,
            "temperature": self.config.llm_temperature,
        }
        if self.config.llm_send_model:
            payload["model"] = self.config.llm_model
        return payload


class AzureFoundryClient(LlmClient):
    """Client for Azure Foundry/Azure OpenAI endpoint URLs."""

    def _build_url(self) -> str:
        if self.config.llm_chat_completions_url:
            return self.config.llm_chat_completions_url
        raise ValueError("llm_chat_completions_url is required when llm_client_type=azure_foundry")

    def _build_payload(self, messages: list[dict]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": messages,
            "max_completion_tokens": self.config.llm_max_completion_tokens,
        }
        if self.config.llm_azure_send_temperature:
            payload["temperature"] = self.config.llm_azure_temperature
        if self.config.llm_send_model:
            payload["model"] = self.config.llm_model
        return payload


def create_llm_client(config: AppConfig) -> LlmClient:
    if config.llm_client_type == "openai_compatible":
        return OpenAICompatibleClient(config)
    if config.llm_client_type == "azure_foundry":
        return AzureFoundryClient(config)
    raise ValueError(f"Unsupported llm_client_type: {config.llm_client_type}")
