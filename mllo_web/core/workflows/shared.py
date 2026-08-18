from __future__ import annotations

from typing import Any


def active_provider_config(settings) -> dict:
    return {
        "provider": settings.llm_client_type,
        "base_url": settings.llm_base_url,
        "chat_completions_path": settings.llm_chat_completions_path,
        "chat_completions_url": settings.llm_chat_completions_url,
        "model": settings.llm_model,
        "send_model": settings.llm_send_model,
        "api_key": settings.llm_api_key,
        "api_key_header": settings.llm_api_key_header,
        "api_key_prefix": settings.llm_api_key_prefix,
        "api_version": settings.llm_api_version,
        "api_version_param": settings.llm_api_version_param,
        "timeout_seconds": settings.llm_timeout_seconds,
        "max_tokens": settings.llm_max_tokens,
        "max_completion_tokens": settings.llm_max_completion_tokens,
        "temperature": settings.llm_temperature,
        "azure_send_temperature": settings.llm_azure_send_temperature,
        "azure_temperature": settings.llm_azure_temperature,
    }


def dataset_role_params_to_query_args(dataset_roles: Any) -> list[str] | None:
    if not isinstance(dataset_roles, list):
        return None
    mapping = {
        "training": "training_data",
        "test": "test_data",
        "validation": "validation_data",
        "production": "production_data",
        "raw": "raw_data",
    }
    values = [f"{mapping[item]},true" for item in dataset_roles if item in mapping]
    return values or None


def normalize_list(value: Any) -> list[str] | None:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return None


def normalize_identifier(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip("/").rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    return value.strip('"')


def pipeline_names_from_params(params: dict[str, Any]) -> list[str]:
    candidates = (
        normalize_list(params.get("pipeline_ids"))
        or normalize_list(params.get("pipeline_names"))
        or normalize_list(params.get("pipelines"))
    )
    return [normalize_identifier(item) for item in candidates if normalize_identifier(item)]
