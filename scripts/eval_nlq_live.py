from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mllo_web.app.api.routers.natural_language_query import execute_nlq
from mllo_web.app.api.services.settings_model import load_settings


CASES = [
    {
        "question": "Show me models trained on MNIST",
        "category": "structured_lookup",
        "expected": "supported",
    },
    {
        "question": "What kinds of models exist in MLLO?",
        "category": "conceptual_exploration",
        "expected": "supported",
    },
    {
        "question": "What is the best performing model?",
        "category": "ranking",
        "expected": "supported",
    },
    {
        "question": "Find models with performance more than 0.9",
        "category": "threshold_filter",
        "expected": "supported",
    },
    {
        "question": "Show me models with performance more than 0.9 and their test dataset",
        "category": "threshold_filter",
        "expected": "supported",
    },
    {
        "question": "Show me the best performing model and its pipeline",
        "category": "ranking_with_context",
        "expected": "supported",
    },
    {
        "question": "Which pipeline is associated with the best performing model?",
        "category": "ranking_with_context",
        "expected": "supported",
    },
    {
        "question": "Compare pipelines PreprocessingPipeline1 and PreprocessingPipeline10",
        "category": "pipeline_comparison",
        "expected": "supported",
    },
    {
        "question": "Show me deployed models and the systems they run on",
        "category": "deployed_models",
        "expected": "supported",
    },
    {
        "question": "Which datasets are used as test data sets?",
        "category": "dataset_lookup",
        "expected": "supported",
    },
    {
        "question": "Trace the lineage of PreprocessedDataset1 upstream",
        "category": "lineage",
        "expected": "stretch",
    },
    {
        "question": "What namespaces are present in the graph?",
        "category": "graph_metadata",
        "expected": "stretch",
    },
    {
        "question": "How do different hyperparameter configurations impact model performance?",
        "category": "analysis",
        "expected": "stretch",
    },
]


def _write_report(output_path: Path, reports: list[dict]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")


def _case_status(report: dict) -> str:
    if report.get("error_type"):
        return "error"
    if report.get("result_count", 0) > 0:
        return "answered"
    return "empty"


def _build_summary(reports: list[dict]) -> dict[str, int]:
    summary = {
        "supported_answered": 0,
        "supported_empty": 0,
        "supported_errored": 0,
        "stretch_answered": 0,
        "stretch_empty": 0,
        "stretch_errored": 0,
    }
    for report in reports:
        expected = report.get("expected", "supported")
        status = _case_status(report)
        key = f"{expected}_{'errored' if status == 'error' else status}"
        if key in summary:
            summary[key] += 1
    return summary


async def main() -> None:
    settings = load_settings()
    repo = os.environ.get("REPO", settings.graphdb_default_repo)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT / "tmp"
    output_path = output_dir / f"nlq_eval_{repo}_{timestamp}.json"
    latest_path = output_dir / f"nlq_eval_{repo}_latest.json"
    reports = []
    for case in CASES:
        question = case["question"]
        print(f"[question] {question}", flush=True)
        try:
            response = await execute_nlq(question, repo=repo, answer_mode="auto")
            payload = response.model_dump()
            reports.append(
                {
                    "category": case["category"],
                    "expected": case["expected"],
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
                    "category": case["category"],
                    "expected": case["expected"],
                    "question": question,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        _write_report(output_path, reports)
        _write_report(latest_path, reports)
        print(f"[saved] {output_path}", flush=True)
        print(f"[done] {question}", flush=True)
    summary = _build_summary(reports)
    print("[summary]", json.dumps(summary, indent=2), flush=True)
    print(json.dumps({"summary": summary, "cases": reports}, indent=2))
    print(f"[final] {output_path}", flush=True)
    print(f"[latest] {latest_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
