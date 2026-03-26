from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mllo_web.app.api.routers.natural_language_query import execute_nlq


PROMPTS = [
    "Show me models trained on MNIST",
    "What kinds of models exist in MLLO?",
    "What is the best performing model?",
    "Find models with performance more than 0.9",
    "Show me models with performance more than 0.9 and their test dataset",
    "Compare pipelines PreprocessingPipeline1 and PreprocessingPipeline10",
    "Show me the best performing model and its test dataset",
    "Show me the best performing model and its pipeline",
    "Show me models with performance more than 0.9 and their pipeline",
    "Show me models with performance more than 0.9, their test dataset, and their pipeline",
    "Which models stay above 0.9 accuracy and what test datasets were they evaluated on?",
    "Which pipeline is associated with the best performing model?",
    "How do different hyperparameter configurations impact model performance?"
]


def _write_report(output_path: Path, reports: list[dict]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")


async def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT / "tmp"
    output_path = output_dir / f"nlq_eval_mllo4_{timestamp}.json"
    latest_path = output_dir / "nlq_eval_mllo4_latest.json"
    reports = []
    for question in PROMPTS:
        print(f"[question] {question}", flush=True)
        try:
            response = await execute_nlq(question, repo="mllo4", answer_mode="auto")
            payload = response.model_dump()
            reports.append(
                {
                    "question": payload["question"],
                    "intent": payload["intent"],
                    "repo_used": payload["repo_used"],
                    "inference_used": payload["inference_used"],
                    "result_count": len(payload["results"]),
                    "answer": payload["answer"],
                    "sparql_preview": payload["sparql"][:1200],
                    "results_preview": payload["results"][:5],
                }
            )
        except Exception as exc:  # pragma: no cover - live eval helper
            reports.append(
                {
                    "question": question,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        _write_report(output_path, reports)
        _write_report(latest_path, reports)
        print(f"[saved] {output_path}", flush=True)
        print(f"[done] {question}", flush=True)
    print(json.dumps(reports, indent=2))
    print(f"[final] {output_path}", flush=True)
    print(f"[latest] {latest_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
