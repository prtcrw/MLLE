from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mllo_web.app.api.config import AppConfig, get_config
from mllo_web.app.api.routers.settings import router as settings_router
from mllo_web.app.api.services.graphdb_client import GraphDBClient
from mllo_web.app.api.services.settings_model import RuntimeSettingsView, load_settings
from mllo_web.core.workflows.shared import active_provider_config


class EnvConfigurationTests(unittest.TestCase):
    def test_env_file_populates_the_shared_runtime_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    (
                        "HOST=0.0.0.0",
                        "PORT=6262",
                        "GRAPHDB_URL=http://graphdb.example:7200",
                        "GRAPHDB_DEFAULT_REPO=mllo5",
                        "GRAPHDB_REPO_ALLOWLIST=mllo5,shared",
                        "LLM_CLIENT_TYPE=openai_compatible",
                        "LLM_BASE_URL=http://llm.example/v1",
                        "LLM_MODEL=test-model",
                        "LLM_API_KEY=test-secret",
                        "ANSWER_MODE=exact",
                        "ENABLE_NLQ_LOGGING=true",
                    )
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                config = AppConfig(_env_file=env_path)

        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 6262)
        self.assertEqual(config.graphdb_default_repo, "mllo5")
        self.assertEqual(config.graphdb_repo_allowlist, ["mllo5", "shared"])
        self.assertEqual(config.graphdb_endpoint, "http://graphdb.example:7200/repositories/mllo5")
        self.assertEqual(config.llm_model, "test-model")
        self.assertEqual(config.answer_mode, "exact")
        self.assertTrue(config.enable_nlq_logging)

    def test_runtime_settings_view_never_exposes_secrets(self) -> None:
        config = AppConfig(_env_file=None, llm_api_key="test-secret", graphdb_auth_password="graph-secret")
        payload = RuntimeSettingsView.from_config(config).model_dump()

        self.assertNotIn("llm_api_key", payload)
        self.assertNotIn("graphdb_auth_password", payload)
        self.assertNotIn("test-secret", str(payload))
        self.assertNotIn("graph-secret", str(payload))

    def test_settings_api_is_read_only(self) -> None:
        settings_route = next(route for route in settings_router.routes if route.path == "/v1/settings")
        self.assertEqual(settings_route.methods, {"GET"})

    def test_all_compatibility_loaders_return_the_same_cached_config(self) -> None:
        self.assertIs(load_settings(), get_config())
        self.assertEqual(GraphDBClient().default_repo, get_config().graphdb_default_repo)

    def test_llm_gateway_config_is_derived_from_app_config(self) -> None:
        config = AppConfig(
            _env_file=None,
            llm_client_type="azure_foundry",
            llm_chat_completions_url="https://llm.example/chat/completions",
            llm_model="deployment",
            llm_api_key="test-secret",
            llm_api_key_header="api-key",
            llm_api_key_prefix="",
        )

        provider = active_provider_config(config)

        self.assertEqual(provider["provider"], "azure_foundry")
        self.assertEqual(provider["chat_completions_url"], "https://llm.example/chat/completions")
        self.assertEqual(provider["api_key_header"], "api-key")
        self.assertEqual(provider["api_key"], "test-secret")


if __name__ == "__main__":
    unittest.main()
