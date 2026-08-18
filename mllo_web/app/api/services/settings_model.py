from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from mllo_web.app.api.config import AppConfig, get_config

try:
    from platformdirs import user_data_dir
except ImportError:
    def user_data_dir(appname: str, appauthor: str | None = None) -> str:
        base = Path.home() / ".local" / "share"
        author_segment = appauthor or appname
        return str(base / author_segment / appname)


class RuntimeSettingsView(BaseModel):
    """Secret-free settings returned to the read-only Settings UI."""

    config_source: str = ".env"
    llm_client_type: str
    llm_base_url: str
    llm_chat_completions_url: str | None
    llm_model: str
    graphdb_url: str
    graphdb_default_repo: str
    graphdb_repo_allowlist: list[str] | None
    answer_mode: str
    enable_nlq_logging: bool

    @classmethod
    def from_config(cls, config: AppConfig) -> "RuntimeSettingsView":
        return cls.model_validate(config.model_dump())


def _settings_dir() -> Path:
    return Path(user_data_dir("MLLE", "MLLE"))


def get_app_data_dir() -> Path:
    return _settings_dir()


def load_settings() -> AppConfig:
    """Compatibility entry point; all runtime settings come from the repo .env."""
    return get_config()
