from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from mllo_web.app.api.services.intent_classifier import QueryIntent
from mllo_web.app.api.services.llm_gateway import LLMGateway
from mllo_web.core.workflows.nlq import _execute_with_state, execute_nlq


class FakeGraphDBClient:
    def __init__(self, *args, **kwargs):
        pass

    async def validate_repo(self, repo: str) -> str:
        return repo

    async def query(self, sparql: str, **kwargs) -> list[dict]:
        return []


def custom_intent(question: str) -> QueryIntent:
    return QueryIntent(
        tool="custom_sparql",
        params={"question": question},
        use_inference=False,
        reasoning="Classifier selected custom SPARQL.",
    )


class ExecutionReportingTests(unittest.IsolatedAsyncioTestCase):
    async def execute(self, question: str, intent: QueryIntent):
        return await _execute_with_state(
            question=question,
            intent=intent,
            resolved_repo="mllo5",
            use_inference=False,
            graphdb_client=FakeGraphDBClient(),
            gateway=LLMGateway(),
        )

    async def test_custom_intent_reports_deterministic_lineage_execution(self) -> None:
        execution = await self.execute(
            "What datasets are downstream of MnistG16?",
            custom_intent("What datasets are downstream of MnistG16?"),
        )

        self.assertEqual(
            execution.state.get_artifact("execution"),
            {"mode": "deterministic", "route": "lineage_orchestration"},
        )
        self.assertEqual([step.tool for step in execution.state.steps], ["resolve_artifact"])

    async def test_custom_intent_reports_deterministic_performance_execution(self) -> None:
        execution = await self.execute(
            "Show models with performance more than 0.95",
            custom_intent("Show models with performance more than 0.95"),
        )

        self.assertEqual(
            execution.state.get_artifact("execution"),
            {"mode": "deterministic", "route": "performance_orchestration"},
        )
        self.assertEqual([step.tool for step in execution.state.steps], ["performance_filter"])

    async def test_actual_generated_sparql_is_reported_as_llm_generated(self) -> None:
        question = "Which entities have an unusual combination of relationships?"
        with patch(
            "mllo_web.core.workflows.nlq.generate_sparql",
            new=AsyncMock(return_value=("SELECT * WHERE {}", {"prefixes": []})),
        ):
            execution = await self.execute(question, custom_intent(question))

        self.assertEqual(
            execution.state.get_artifact("execution"),
            {"mode": "llm_generated", "route": "custom_sparql"},
        )
        self.assertEqual([step.tool for step in execution.state.steps], ["custom_sparql"])

    async def test_prior_performance_context_does_not_hijack_current_custom_question(self) -> None:
        current_question = (
            "For each process, list every input artifact together with every output artifact "
            "and the model it executes."
        )
        contextual_question = (
            "Conversation context:\n"
            "User: Show models with performance more than 0.95.\n"
            "Assistant: Here are the performance results.\n\n"
            f"Current user question: {current_question}\n"
            "Resolve references to earlier turns when needed."
        )
        with patch(
            "mllo_web.core.workflows.nlq.generate_sparql",
            new=AsyncMock(return_value=("SELECT * WHERE {}", {"prefixes": []})),
        ) as generate_sparql:
            execution = await self.execute(contextual_question, custom_intent(contextual_question))

        self.assertEqual(
            execution.state.get_artifact("execution"),
            {"mode": "llm_generated", "route": "custom_sparql"},
        )
        self.assertEqual(generate_sparql.await_args.args[0], current_question)

    async def test_prior_dataset_and_pipeline_context_does_not_add_performance_enrichment(self) -> None:
        current_question = "Show models with performance more than 0.95."
        contextual_question = (
            "Conversation context:\n"
            "User: Include test datasets and pipelines.\n\n"
            f"Current user question: {current_question}\n"
            "Resolve references to earlier turns when needed."
        )
        execution = await self.execute(contextual_question, custom_intent(current_question))

        self.assertEqual(
            execution.state.get_artifact("execution"),
            {"mode": "deterministic", "route": "performance_orchestration"},
        )
        self.assertEqual([step.tool for step in execution.state.steps], ["performance_filter"])

    async def test_response_keeps_classified_intent_separate_from_actual_execution(self) -> None:
        question = "What datasets are downstream of MnistG16?"
        intent = custom_intent(question)
        with (
            patch("mllo_web.core.workflows.nlq.GraphDBClient", FakeGraphDBClient),
            patch("mllo_web.core.workflows.nlq.classify_intent", new=AsyncMock(return_value=intent)),
            patch("mllo_web.core.workflows.nlq.generate_answer", new=AsyncMock(return_value="No matches.")),
        ):
            response = await execute_nlq(question, repo="mllo5", answer_mode="auto")

        self.assertEqual(response.intent.tool, "custom_sparql")
        self.assertEqual(response.execution_mode, "deterministic")
        self.assertEqual(response.execution_route, "lineage_orchestration")
        self.assertEqual(response.executed_tools, ["resolve_artifact"])


if __name__ == "__main__":
    unittest.main()
