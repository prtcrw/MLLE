from __future__ import annotations

import logging
from typing import Any

import httpx
from mllo_web.app.api.services.interaction_logging import record_llm_call

logger = logging.getLogger(__name__)


class LLMServiceError(RuntimeError):
    pass


class LLMGateway:
    async def chat_completion(self, messages: list[dict], provider_config: dict, purpose: str | None = None) -> str:
        provider = provider_config.get("provider")
        model = provider_config.get("model")
        base_url = provider_config.get("base_url")
        prompt_size = sum(len(str(message.get("content", ""))) for message in messages)
        logger.info("LLM call provider=%s prompt_chars~=%d", provider, prompt_size)

        try:
            if provider in {"openai_compatible", "azure_foundry"}:
                text = await self._chat_completions_request(messages, provider_config)
            else:
                raise LLMServiceError(f"Unsupported LLM provider: {provider}")

            record_llm_call(
                purpose=purpose,
                provider=provider,
                model=model,
                base_url=base_url,
                messages=messages,
                prompt_chars=prompt_size,
                response_text=text,
            )
            return text
        except LLMServiceError:
            record_llm_call(
                purpose=purpose,
                provider=provider,
                model=model,
                base_url=base_url,
                messages=messages,
                prompt_chars=prompt_size,
                error="LLMServiceError",
            )
            raise
        except Exception as exc:
            record_llm_call(
                purpose=purpose,
                provider=provider,
                model=model,
                base_url=base_url,
                messages=messages,
                prompt_chars=prompt_size,
                error=str(exc),
            )
            raise LLMServiceError(str(exc)) from exc

    async def _chat_completions_request(self, messages: list[dict], provider_config: dict) -> str:
        provider = provider_config.get("provider")
        base_url = (provider_config.get("base_url") or "").rstrip("/")
        path = "/" + (provider_config.get("chat_completions_path") or "chat/completions").lstrip("/")
        request_url = provider_config.get("chat_completions_url")
        if not request_url and not base_url:
            raise LLMServiceError("LLM chat completions URL is required")
        request_url = request_url or f"{base_url}{path}"

        headers: dict[str, str] = {"Content-Type": "application/json"}
        api_key = provider_config.get("api_key")
        if api_key:
            header_name = provider_config.get("api_key_header") or "Authorization"
            prefix = (provider_config.get("api_key_prefix") or "").strip()
            headers[header_name] = f"{prefix} {api_key}".strip()

        payload: dict[str, Any] = {"messages": messages}
        if provider_config.get("send_model", True):
            payload["model"] = provider_config.get("model")
        if provider == "azure_foundry":
            payload["max_completion_tokens"] = provider_config.get("max_completion_tokens", 1024)
            if provider_config.get("azure_send_temperature", False):
                payload["temperature"] = provider_config.get("azure_temperature", 1.0)
        else:
            payload["max_tokens"] = provider_config.get("max_tokens", 1024)
            payload["temperature"] = provider_config.get("temperature", 0.0)

        params = None
        api_version = provider_config.get("api_version")
        if api_version:
            params = {provider_config.get("api_version_param") or "api-version": api_version}

        async with httpx.AsyncClient(timeout=provider_config.get("timeout_seconds", 120.0)) as client:
            response = await client.post(
                request_url,
                headers=headers,
                params=params,
                json=payload,
            )

        if not response.is_success:
            detail = response.text[:500]
            try:
                body = response.json()
                error = body.get("error", {}) if isinstance(body, dict) else {}
                if isinstance(error, dict) and isinstance(error.get("message"), str):
                    detail = error["message"]
            except ValueError:
                pass
            raise LLMServiceError(f"LLM API error {response.status_code}: {detail}")

        data = response.json()
        content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMServiceError("LLM response missing message content")
        return content.strip()
