from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

try:
    from platformdirs import user_data_dir
except ImportError:
    def user_data_dir(appname: str, appauthor: str | None = None) -> str:
        base = Path.home() / ".local" / "share"
        author_segment = appauthor or appname
        return str(base / author_segment / appname)


def _env_allowlist() -> list[str] | None:
    raw = os.getenv("GRAPHDB_REPO_ALLOWLIST", "").strip()
    if not raw:
        return None
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or None


class LLMProviderConfig(BaseModel):
    provider: Literal["lm_studio", "openai", "anthropic", "gemini"]
    base_url: str | None = None
    api_key: str | None = None
    model: str

    @model_validator(mode="after")
    def validate_config(self) -> "LLMProviderConfig":
        if self.provider == "lm_studio" and not self.base_url:
            raise ValueError("base_url is required for lm_studio")
        if not self.model.strip():
            raise ValueError("model is required")
        return self


class MLLESettings(BaseModel):
    active_llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "lm_studio"))
    llm_providers: dict[str, LLMProviderConfig] = Field(default_factory=lambda: {
        "lm_studio": LLMProviderConfig(
            provider="lm_studio",
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:1234/v1"),
            api_key=os.getenv("LLM_API_KEY", "lm-studio"),
            model=os.getenv("LLM_MODEL", "local-model"),
        ),
        "openai": LLMProviderConfig(
            provider="openai",
            api_key=os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", "")),
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        ),
        "anthropic": LLMProviderConfig(
            provider="anthropic",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        ),
        "gemini": LLMProviderConfig(
            provider="gemini",
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        ),
    })
    graphdb_url: str = Field(default_factory=lambda: os.getenv("GRAPHDB_URL", "http://localhost:7200"))
    graphdb_default_repo: str = Field(default_factory=lambda: os.getenv("GRAPHDB_DEFAULT_REPO", "mllo3"))
    graphdb_repo_allowlist: list[str] | None = Field(default_factory=_env_allowlist)
    answer_mode: Literal["exact", "conceptual", "auto"] = "auto"

    @model_validator(mode="after")
    def validate_settings(self) -> "MLLESettings":
        if self.active_llm_provider not in self.llm_providers:
            raise ValueError("active_llm_provider must exist in llm_providers")
        return self


def _settings_dir() -> Path:
    return Path(user_data_dir("MLLE", "MLLE"))


def get_app_data_dir() -> Path:
    return _settings_dir()


def get_settings_path() -> Path:
    return _settings_dir() / "mlle_settings.json"


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings() -> MLLESettings:
    defaults = MLLESettings()
    path = get_settings_path()
    if not path.exists():
        return defaults

    raw = json.loads(path.read_text(encoding="utf-8"))
    merged = _deep_merge(defaults.model_dump(), raw)
    return MLLESettings.model_validate(merged)


def save_settings(settings: MLLESettings) -> MLLESettings:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return settings
