from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from platformdirs import user_data_dir
except ImportError:
    def user_data_dir(appname: str, appauthor: str | None = None) -> str:
        base = Path.home() / ".local" / "share"
        author_segment = appauthor or appname
        return str(base / author_segment / appname)


def _env_allowlist() -> list[str] | None:
    raw = _settings_env().graphdb_repo_allowlist or ""
    raw = raw.strip()
    if not raw:
        return None
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or None


_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class SettingsEnv(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    ollama_base_url: str | None = None
    ollama_api_key: str | None = None
    ollama_model: str | None = None

    openai_api_key: str | None = None
    openai_model: str | None = None

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str | None = None
    azure_openai_deployment: str | None = None

    anthropic_api_key: str | None = None
    anthropic_model: str | None = None

    gemini_api_key: str | None = None
    gemini_model: str | None = None

    graphdb_url: str | None = None
    graphdb_default_repo: str | None = None
    graphdb_endpoint: str | None = None
    graphdb_repo_allowlist: str | None = None


def _settings_env() -> SettingsEnv:
    return SettingsEnv()


def _configured_env_names() -> set[str]:
    names = set(os.environ)
    if not _ENV_FILE.exists():
        return names

    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        names.add(stripped.split("=", 1)[0].strip())
    return names


def _env_value(value: str | None, default: str) -> str:
    if value is None or value == "":
        return default
    return value


def _split_graphdb_endpoint(endpoint: str | None) -> tuple[str | None, str | None]:
    if not endpoint:
        return None, None
    marker = "/repositories/"
    if marker not in endpoint:
        return endpoint.rstrip("/"), None
    base_url, repo = endpoint.split(marker, 1)
    repo = repo.split("/", 1)[0].strip()
    return base_url.rstrip("/"), repo or None


def _env_graphdb_url(env: SettingsEnv) -> str:
    endpoint_url, _ = _split_graphdb_endpoint(env.graphdb_endpoint)
    return _env_value(env.graphdb_url or endpoint_url, "http://localhost:7200")


def _env_graphdb_default_repo(env: SettingsEnv) -> str:
    _, endpoint_repo = _split_graphdb_endpoint(env.graphdb_endpoint)
    return _env_value(env.graphdb_default_repo or endpoint_repo, "mllo4")


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
    active_llm_provider: str = Field(default_factory=lambda: _env_value(_settings_env().llm_provider, "lm_studio"))
    llm_providers: dict[str, LLMProviderConfig] = Field(default_factory=lambda: {
        "lm_studio": LLMProviderConfig(
            provider="lm_studio",
            base_url=_env_value(_settings_env().llm_base_url, "http://localhost:1234/v1"),
            api_key=_env_value(_settings_env().llm_api_key, "lm-studio"),
            model=_env_value(_settings_env().llm_model, "local-model"),
        ),
        "ollama": LLMProviderConfig(
            provider="ollama",
            base_url=_env_value(_settings_env().ollama_base_url, "http://localhost:11434/v1"),
            api_key=_env_value(_settings_env().ollama_api_key, ""),
            model=_env_value(_settings_env().ollama_model, "llama3.1"),
        ),
        "openai": LLMProviderConfig(
            provider="openai",
            api_key=_env_value(_settings_env().openai_api_key or _settings_env().llm_api_key, ""),
            model=_env_value(_settings_env().openai_model, "gpt-4o"),
        ),
        "azure_openai": LLMProviderConfig(
            provider="azure_openai",
            base_url=_env_value(_settings_env().azure_openai_endpoint, ""),
            api_key=_env_value(_settings_env().azure_openai_api_key, ""),
            api_version=_env_value(_settings_env().azure_openai_api_version, "2024-10-21"),
            model=_env_value(_settings_env().azure_openai_deployment, ""),
        ),
        "anthropic": LLMProviderConfig(
            provider="anthropic",
            api_key=_env_value(_settings_env().anthropic_api_key, ""),
            model=_env_value(_settings_env().anthropic_model, "claude-3-5-sonnet-20241022"),
        ),
        "gemini": LLMProviderConfig(
            provider="gemini",
            api_key=_env_value(_settings_env().gemini_api_key, ""),
            model=_env_value(_settings_env().gemini_model, "gemini-1.5-pro"),
        ),
    })
    graphdb_url: str = Field(default_factory=lambda: _env_graphdb_url(_settings_env()))
    graphdb_default_repo: str = Field(default_factory=lambda: _env_graphdb_default_repo(_settings_env()))
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


def load_settings() -> MLLESettings:
    defaults = MLLESettings()
    path = get_settings_path()
    if not path.exists():
        return defaults

    raw = json.loads(path.read_text(encoding="utf-8"))
    merged = _deep_merge(defaults.model_dump(), raw)
    settings = MLLESettings.model_validate(merged)
    return _apply_env_overrides(settings)


def _apply_env_overrides(settings: MLLESettings) -> MLLESettings:
    env = _settings_env()
    configured = _configured_env_names()
    data = settings.model_dump(mode="python")

    if "LLM_PROVIDER" in configured and env.llm_provider:
        data["active_llm_provider"] = env.llm_provider

    provider_env: dict[str, dict[str, tuple[str, str | None]]] = {
        "lm_studio": {
            "base_url": ("LLM_BASE_URL", env.llm_base_url),
            "api_key": ("LLM_API_KEY", env.llm_api_key),
            "model": ("LLM_MODEL", env.llm_model),
        },
        "ollama": {
            "base_url": ("OLLAMA_BASE_URL", env.ollama_base_url),
            "api_key": ("OLLAMA_API_KEY", env.ollama_api_key),
            "model": ("OLLAMA_MODEL", env.ollama_model),
        },
        "openai": {
            "api_key": ("OPENAI_API_KEY", env.openai_api_key),
            "model": ("OPENAI_MODEL", env.openai_model),
        },
        "azure_openai": {
            "base_url": ("AZURE_OPENAI_ENDPOINT", env.azure_openai_endpoint),
            "api_key": ("AZURE_OPENAI_API_KEY", env.azure_openai_api_key),
            "api_version": ("AZURE_OPENAI_API_VERSION", env.azure_openai_api_version),
            "model": ("AZURE_OPENAI_DEPLOYMENT", env.azure_openai_deployment),
        },
        "anthropic": {
            "api_key": ("ANTHROPIC_API_KEY", env.anthropic_api_key),
            "model": ("ANTHROPIC_MODEL", env.anthropic_model),
        },
        "gemini": {
            "api_key": ("GEMINI_API_KEY", env.gemini_api_key),
            "model": ("GEMINI_MODEL", env.gemini_model),
        },
    }

    providers = data["llm_providers"]
    for provider, fields in provider_env.items():
        provider_config = providers.setdefault(provider, {"provider": provider})
        for field, (env_name, value) in fields.items():
            if env_name in configured and value is not None:
                provider_config[field] = value

    if "LLM_API_KEY" in configured and env.llm_api_key is not None and "OPENAI_API_KEY" not in configured:
        providers["openai"]["api_key"] = env.llm_api_key

    if "GRAPHDB_URL" in configured or "GRAPHDB_ENDPOINT" in configured:
        data["graphdb_url"] = _env_graphdb_url(env)
    if "GRAPHDB_DEFAULT_REPO" in configured or "GRAPHDB_ENDPOINT" in configured:
        data["graphdb_default_repo"] = _env_graphdb_default_repo(env)
    if "GRAPHDB_REPO_ALLOWLIST" in configured:
        data["graphdb_repo_allowlist"] = _env_allowlist()

    return MLLESettings.model_validate(data)


def save_settings(settings: MLLESettings) -> MLLESettings:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return settings
