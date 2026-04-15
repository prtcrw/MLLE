from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from mllo_web.app.api.services.settings_model import MLLESettings, load_settings
from mllo_web.core.workflows.nlq import execute_nlq


TEST_REPO = os.getenv("MLLO_NLQ_TEST_REPO", "mllo4")
TEST_PROVIDER = os.getenv("MLLO_NLQ_TEST_PROVIDER", "").strip()
TEST_BASE_URL = os.getenv("MLLO_NLQ_TEST_BASE_URL", "").strip()
TEST_MODEL = os.getenv("MLLO_NLQ_TEST_MODEL", "").strip()
TEST_API_KEY = os.getenv("MLLO_NLQ_TEST_API_KEY", "").strip()

CUSTOM_SPARQL_CASES = (
    {
        "question": "Which datasets are consumed by processes that execute a machine learning model?",
        "min_results": 1,
        "expected_keys": {"dataset"},
    },
    {
        "question": "Which datasets are produced by processes that also use a model output?",
        "min_results": 1,
        "expected_keys": {"dataset"},
    },
    {
        "question": "Which models and pipelines share the same dataset?",
        "min_results": 1,
        "expected_keys": {"model", "pipeline", "dataset"},
    },
    {
        "question": "Which model outputs are later used as inputs to another process?",
        "min_results": 1,
        "expected_keys": {"output_dataset"},
    },
    {
        "question": "Which pipelines share a dataset with a model?",
        "min_results": 0,
        "expected_keys": set(),
    },
)

STRUCTURED_AND_THRESHOLD_CASES = (
    {
        "question": "What pipeline uses MnistG16?",
        "expected_tool": "find_pipelines",
        "expected_keys": {"pipeline_name", "pipeline_data_input"},
    },
    {
        "question": "What models use MnistG16 as test dataset?",
        "expected_tool": "find_models",
        "expected_keys": {"model", "linked_dataset"},
    },
    {
        "question": "What models use MnistG16 as training dataset?",
        "expected_tool": "find_models",
        "expected_keys": {"model", "linked_dataset"},
    },
    {
        "question": "What datasets are downstream of MnistG16?",
        "expected_tool": "custom_sparql",
        "expected_keys": {"downstream_dataset", "downstream_process"},
    },
    {
        "question": "Show me models with performance more than 0.95",
        "expected_tool": "custom_sparql",
        "expected_keys": {"model_name", "model_performance_value"},
    },
)


class NLQRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def _execute(self, question: str):
        if not (TEST_PROVIDER and TEST_MODEL):
            return await execute_nlq(question, repo=TEST_REPO, answer_mode="auto")

        settings_dict = load_settings().model_dump(mode="python")
        provider_name = "test_provider"
        settings_dict["active_llm_provider"] = provider_name
        settings_dict["llm_providers"][provider_name] = {
            "provider": TEST_PROVIDER,
            "base_url": TEST_BASE_URL or None,
            "api_key": TEST_API_KEY,
            "api_version": None,
            "model": TEST_MODEL,
        }
        overridden_settings = MLLESettings.model_validate(settings_dict)
        with patch("mllo_web.core.workflows.nlq.load_settings", return_value=overridden_settings):
            return await execute_nlq(question, repo=TEST_REPO, answer_mode="auto")

    async def test_downstream_artifacts_query_returns_lineage_shape(self) -> None:
        response = await self._execute("What downstream artifacts use MnistG16?")

        self.assertGreater(len(response.results), 0)
        result_keys = {key for row in response.results for key in row.keys()}
        self.assertIn("downstream_process", result_keys)
        self.assertIn("downstream_dataset", result_keys)

    async def test_downstream_models_query_returns_model_name(self) -> None:
        response = await self._execute("What models use downstream artifacts of MnistG16?")

        self.assertGreater(len(response.results), 0)
        result_keys = {key for row in response.results for key in row.keys()}
        self.assertIn("model_name", result_keys)
        self.assertIn("downstream_dataset", result_keys)

    async def test_downstream_models_query_with_which_wording_returns_model_name(self) -> None:
        response = await self._execute("Which models use downstream artifacts of MnistG16?")

        self.assertGreater(len(response.results), 0)
        result_keys = {key for row in response.results for key in row.keys()}
        self.assertIn("model_name", result_keys)
        self.assertIn("downstream_dataset", result_keys)

    async def test_performance_query_returns_enriched_context(self) -> None:
        response = await self._execute("Show me models their test dataset, and their pipeline that has performance more than 0.9")

        self.assertGreater(len(response.results), 0)
        result_keys = {key for row in response.results for key in row.keys()}
        self.assertIn("model_name", result_keys)
        self.assertIn("test_datasets", result_keys)
        self.assertIn("pipelines", result_keys)

    async def test_conceptual_dataset_prompt_uses_inference(self) -> None:
        response = await self._execute("Which kinds of datasets exist in MLLO?")

        self.assertEqual(response.intent.tool, "explore_category")
        self.assertTrue(response.inference_used)
        self.assertGreater(len(response.results), 0)
        result_keys = {key for row in response.results for key in row.keys()}
        self.assertIn("entity", result_keys)
        self.assertIn("entity_type", result_keys)
        self.assertIn("label", result_keys)

    async def test_custom_sparql_prompt_set_routes_to_custom_sparql(self) -> None:
        for case in CUSTOM_SPARQL_CASES:
            with self.subTest(question=case["question"]):
                response = await self._execute(case["question"])

                self.assertEqual(response.intent.tool, "custom_sparql")
                self.assertGreaterEqual(len(response.results), case["min_results"])

                result_keys = {key for row in response.results for key in row.keys()}
                for key in case["expected_keys"]:
                    self.assertIn(key, result_keys)

    async def test_structured_and_threshold_prompt_set(self) -> None:
        for case in STRUCTURED_AND_THRESHOLD_CASES:
            with self.subTest(question=case["question"]):
                response = await self._execute(case["question"])

                self.assertEqual(response.intent.tool, case["expected_tool"])
                self.assertGreater(len(response.results), 0)

                result_keys = {key for row in response.results for key in row.keys()}
                for key in case["expected_keys"]:
                    self.assertIn(key, result_keys)


if __name__ == "__main__":
    unittest.main()
