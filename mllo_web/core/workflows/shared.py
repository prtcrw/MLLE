from __future__ import annotations

from typing import Any


def active_provider_config(settings) -> dict:
    return settings.llm_providers[settings.active_llm_provider].model_dump()


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
