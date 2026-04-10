from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mllo_web.app.api.routers.natural_language_query import execute_nlq
from mllo_web.app.api.services.llm_gateway import LLMGateway


DEFAULT_QUESTIONS = [
    "Show me models trained on MNIST",
    "Show me the best performing model and its test dataset",
    "How do different hyperparameter configurations impact model performance?",
]


async def _run() -> list[dict[str, Any]]:
    original = LLMGateway.chat_completion
    reports: list[dict[str, Any]] = []
    captured_calls: list[dict[str, Any]] = []

    async def wrapped(self: LLMGateway, messages: list[dict], provider_config: dict) -> str:
        response = await original(self, messages, provider_config)
        captured_calls.append(
            {
                "provider": provider_config.get("provider"),
                "model": provider_config.get("model"),
                "messages": messages,
                "response": response,
            }
        )
        return response

    LLMGateway.chat_completion = wrapped
    try:
        questions = json.loads(os.environ["QUESTIONS_JSON"]) if os.environ.get("QUESTIONS_JSON") else DEFAULT_QUESTIONS
        for question in questions:
            start_idx = len(captured_calls)
            item: dict[str, Any] = {"question": question}
            try:
                result = await execute_nlq(question, repo="mllo4", answer_mode="auto")
                payload = result.model_dump()
                item["ok"] = True
                item["intent"] = payload["intent"]
                item["sparql"] = payload["sparql"]
                item["results"] = payload["results"][:10]
                item["result_count"] = len(payload["results"])
                item["answer"] = payload["answer"]
                item["repo_used"] = payload["repo_used"]
                item["inference_used"] = payload["inference_used"]
            except Exception as exc:  # pragma: no cover - runtime capture helper
                item["ok"] = False
                item["error_type"] = type(exc).__name__
                item["error"] = str(exc)
            item["llm_calls"] = captured_calls[start_idx:]
            reports.append(item)
    finally:
        LLMGateway.chat_completion = original
    return reports


def main() -> None:
    reports = asyncio.run(_run())
    output_path = os.environ.get("OUTPUT_PATH", str(ROOT / "tmp" / "captured_nlq_examples.json"))
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
