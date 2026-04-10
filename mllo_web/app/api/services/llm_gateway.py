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
            if provider in {"lm_studio", "openai"}:
                text = await self._openai_compatible_completion(messages, provider_config)
            elif provider == "anthropic":
                text = await self._anthropic_completion(messages, provider_config)
            elif provider == "gemini":
                text = await self._gemini_completion(messages, provider_config)
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

    async def _openai_compatible_completion(self, messages: list[dict], provider_config: dict) -> str:
        base_url = (provider_config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        api_key = provider_config.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload: dict[str, Any] = {
            "model": provider_config.get("model"),
            "messages": messages,
            "temperature": 0,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        if not response.is_success:
            raise LLMServiceError(f"LLM API error {response.status_code}: {response.text[:500]}")

        data = response.json()
        content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMServiceError("LLM response missing message content")
        return content.strip()

    async def _anthropic_completion(self, messages: list[dict], provider_config: dict) -> str:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise LLMServiceError("anthropic SDK is not installed") from exc

        system_messages = [message["content"] for message in messages if message.get("role") == "system"]
        chat_messages = [
            {"role": message["role"], "content": message["content"]}
            for message in messages
            if message.get("role") in {"user", "assistant"}
        ]
        client = AsyncAnthropic(api_key=provider_config.get("api_key"))
        response = await client.messages.create(
            model=provider_config.get("model"),
            max_tokens=1024,
            system="\n".join(system_messages),
            messages=chat_messages,
        )
        texts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        if not texts:
            raise LLMServiceError("Anthropic response missing text content")
        return "\n".join(texts).strip()

    async def _gemini_completion(self, messages: list[dict], provider_config: dict) -> str:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise LLMServiceError("google-generativeai SDK is not installed") from exc

        genai.configure(api_key=provider_config.get("api_key"))
        system_text = "\n".join(
            str(message.get("content", "")) for message in messages if message.get("role") == "system"
        )
        prompt_text = "\n\n".join(
            f"{message.get('role', 'user').upper()}:\n{message.get('content', '')}"
            for message in messages
            if message.get("role") != "system"
        )
        model = genai.GenerativeModel(
            model_name=provider_config.get("model"),
            system_instruction=system_text or None,
        )
        response = await model.generate_content_async(prompt_text)
        text = getattr(response, "text", "")
        if not text:
            raise LLMServiceError("Gemini response missing text content")
        return text.strip()
