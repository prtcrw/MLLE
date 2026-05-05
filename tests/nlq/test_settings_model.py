from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mllo_web.app.api.services import settings_model


class SettingsModelTests(unittest.TestCase):
    def _env(self, **values: str | None) -> settings_model.SettingsEnv:
        defaults = {
            "llm_provider": None,
            "llm_base_url": None,
            "llm_api_key": None,
            "llm_model": None,
            "ollama_base_url": None,
            "ollama_api_key": None,
            "ollama_model": None,
            "openai_api_key": None,
            "openai_model": None,
            "azure_openai_endpoint": None,
            "azure_openai_api_key": None,
            "azure_openai_api_version": None,
            "azure_openai_deployment": None,
            "anthropic_api_key": None,
            "anthropic_model": None,
            "gemini_api_key": None,
            "gemini_model": None,
            "graphdb_url": None,
            "graphdb_default_repo": None,
            "graphdb_endpoint": None,
            "graphdb_repo_allowlist": None,
        }
        defaults.update(values)
        return settings_model.SettingsEnv.model_construct(**defaults)

    def test_defaults_follow_env_values(self) -> None:
        env = self._env(
            llm_provider="ollama",
            llm_model="qwen3",
            graphdb_endpoint="http://localhost:7200/repositories/mllo4",
        )

        with patch.object(settings_model, "_settings_env", return_value=env):
            settings = settings_model.MLLESettings()

        self.assertEqual(settings.active_llm_provider, "ollama")
        self.assertEqual(settings.llm_providers["lm_studio"].model, "qwen3")
        self.assertEqual(settings.graphdb_url, "http://localhost:7200")
        self.assertEqual(settings.graphdb_default_repo, "mllo4")

    def test_explicit_env_overrides_saved_settings(self) -> None:
        env = self._env(
            llm_provider="ollama",
            ollama_model="llama3.2",
            graphdb_default_repo="mllo4",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "mlle_settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "active_llm_provider": "lm_studio",
                        "llm_providers": {
                            "ollama": {
                                "provider": "ollama",
                                "base_url": "http://localhost:11434/v1",
                                "api_key": "",
                                "model": "saved-model",
                            }
                        },
                        "graphdb_default_repo": "saved-repo",
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch.object(settings_model, "_settings_env", return_value=env),
                patch.object(settings_model, "_configured_env_names", return_value={"LLM_PROVIDER", "OLLAMA_MODEL", "GRAPHDB_DEFAULT_REPO"}),
                patch.object(settings_model, "get_settings_path", return_value=settings_path),
            ):
                settings = settings_model.load_settings()

        self.assertEqual(settings.active_llm_provider, "ollama")
        self.assertEqual(settings.llm_providers["ollama"].model, "llama3.2")
        self.assertEqual(settings.graphdb_default_repo, "mllo4")


if __name__ == "__main__":
    unittest.main()
