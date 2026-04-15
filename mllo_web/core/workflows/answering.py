from __future__ import annotations

import json

from mllo_web.core.llm import LLMServiceError
from mllo_web.core.workflows.shared import active_provider_config


async def generate_answer(question: str, results: list[dict], settings, gateway, state=None) -> str:
    if not results:
        return "No matching results were found in the selected repository."
    preview = json.dumps(results[:20], indent=2)
    steps_text = ""
    if state and (state.plan or state.steps):
        plan_summaries = [{"tool": step.tool, "params": step.params, "reasoning": step.reasoning} for step in state.plan]
        step_summaries = [{"tool": step.tool, "params": step.params, "result_count": len(step.results)} for step in state.steps]
        steps_text = (
            f"\n\nPlanned steps:\n{json.dumps(plan_summaries, indent=2)}"
            f"\n\nExecution steps:\n{json.dumps(step_summaries, indent=2)}"
        )
    try:
        return await gateway.chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Summarize ML ontology query results for a non-technical practitioner. "
                        "Be concise and factual. If the results already include joined fields such as "
                        "test_datasets, pipelines, upstream_dataset, upstream_process, downstream_dataset, "
                        "downstream_process, or model_name, use them directly and do not replace them "
                        "with generic guesses."
                    ),
                },
                {"role": "user", "content": f"Question: {question}\n\nFiltered results:\n{preview}{steps_text}"},
            ],
            active_provider_config(settings),
            purpose="answer_generation",
        )
    except LLMServiceError:
        return f"Found {len(results)} result(s) for the question."
