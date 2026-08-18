from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


DEFAULT_GRAPHDB_REPO = "mllo5"
LEGACY_GRAPHDB_REPOS = {"mllo3", "mllo4"}

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
    provider: Literal["lm_studio", "ollama", "openai", "azure_openai", "anthropic", "gemini"]
    base_url: str | None = None
    api_key: str | None = None
    api_version: str | None = None
    model: str

    def is_blank(self) -> bool:
        return not (self.base_url or "").strip() and not (self.api_key or "").strip() and not self.model.strip()

    @model_validator(mode="after")
    def validate_config(self) -> "LLMProviderConfig":
        if self.provider in {"lm_studio", "ollama"} and not self.base_url:
            raise ValueError(f"base_url is required for {self.provider}")
        if self.provider == "azure_openai":
            if self.is_blank():
                return self
            if not self.base_url:
                raise ValueError("base_url is required for azure_openai")
            if not self.api_version:
                raise ValueError("api_version is required for azure_openai")
        if self.provider != "azure_openai" and not self.model.strip():
            raise ValueError("model is required")
        if self.provider == "azure_openai" and not self.is_blank() and not self.model.strip():
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
        "ollama": LLMProviderConfig(
            provider="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("OLLAMA_API_KEY", ""),
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
        ),
        "openai": LLMProviderConfig(
            provider="openai",
            api_key=os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", "")),
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        ),
        "azure_openai": LLMProviderConfig(
            provider="azure_openai",
            base_url=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
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
    graphdb_default_repo: str = Field(default_factory=lambda: os.getenv("GRAPHDB_DEFAULT_REPO", DEFAULT_GRAPHDB_REPO))
    graphdb_repo_allowlist: list[str] | None = Field(default_factory=_env_allowlist)
    answer_mode: Literal["exact", "conceptual", "auto"] = "auto"
    enable_nlq_logging: bool = False

    @model_validator(mode="after")
    def validate_settings(self) -> "MLLESettings":
        if self.active_llm_provider not in self.llm_providers:
            raise ValueError("active_llm_provider must exist in llm_providers")
        active = self.llm_providers[self.active_llm_provider]
        if active.provider == "azure_openai" and active.is_blank():
            raise ValueError("azure_openai must be configured before it can be the active_llm_provider")
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


def _migrate_legacy_graphdb_repo(raw: dict) -> dict:
    if raw.get("graphdb_default_repo") not in LEGACY_GRAPHDB_REPOS:
        return raw

    migrated = dict(raw)
    migrated["graphdb_default_repo"] = DEFAULT_GRAPHDB_REPO
    allowlist = migrated.get("graphdb_repo_allowlist")
    if isinstance(allowlist, list):
        migrated["graphdb_repo_allowlist"] = list(
            dict.fromkeys(DEFAULT_GRAPHDB_REPO if repo in LEGACY_GRAPHDB_REPOS else repo for repo in allowlist)
        )
    return migrated


def load_settings() -> MLLESettings:
    defaults = MLLESettings()
    path = get_settings_path()
    if not path.exists():
        return defaults

    raw = _migrate_legacy_graphdb_repo(json.loads(path.read_text(encoding="utf-8")))
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
