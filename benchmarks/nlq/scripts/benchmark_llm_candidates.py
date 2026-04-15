from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mllo_web.app.api.services.settings_model import MLLESettings, load_settings
from mllo_web.core.workflows.nlq import execute_nlq


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_settings(base_settings: MLLESettings, candidate: dict[str, Any]) -> MLLESettings:
    settings_dict = base_settings.model_dump(mode="python")
    provider_name = candidate.get("name") or candidate["provider"]
    settings_dict["active_llm_provider"] = provider_name
    settings_dict["llm_providers"][provider_name] = {
        "provider": candidate["provider"],
        "base_url": candidate.get("base_url"),
        "api_key": candidate.get("api_key", ""),
        "api_version": candidate.get("api_version"),
        "model": candidate["model"],
    }
    return MLLESettings.model_validate(settings_dict)


def _evaluate_case(case: dict[str, Any], response_payload: dict[str, Any] | None, error: Exception | None, latency_s: float) -> dict[str, Any]:
    report: dict[str, Any] = {
        "question": case["question"],
        "category": case.get("category"),
        "latency_s": round(latency_s, 3),
    }
    if error is not None:
        report["passed"] = False
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
        return report

    assert response_payload is not None
    result_keys = sorted({key for row in response_payload["results"] for key in row.keys()})
    checks: dict[str, bool] = {}

    if "expected_tool" in case:
        checks["tool"] = response_payload["intent"]["tool"] == case["expected_tool"]
    if "expected_inference_used" in case:
        checks["inference"] = response_payload["inference_used"] == case["expected_inference_used"]
    checks["min_results"] = len(response_payload["results"]) >= int(case.get("min_results", 0))
    expected_keys = set(case.get("expected_keys", []))
    checks["keys"] = expected_keys.issubset(result_keys)

    report.update(
        {
            "passed": all(checks.values()),
            "checks": checks,
            "intent_tool": response_payload["intent"]["tool"],
            "inference_used": response_payload["inference_used"],
            "result_count": len(response_payload["results"]),
            "result_keys": result_keys,
            "sparql_preview": response_payload["sparql"][:500],
        }
    )
    return report


def _summarize(candidate_name: str, case_reports: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [item["latency_s"] for item in case_reports]
    passed = sum(1 for item in case_reports if item["passed"])
    errored = sum(1 for item in case_reports if item.get("error_type"))
    return {
        "candidate": candidate_name,
        "cases": len(case_reports),
        "passed": passed,
        "failed": len(case_reports) - passed,
        "errored": errored,
        "pass_rate": round(passed / len(case_reports), 3) if case_reports else 0.0,
        "avg_latency_s": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "median_latency_s": round(statistics.median(latencies), 3) if latencies else None,
    }


async def _run_candidate(
    *,
    candidate: dict[str, Any],
    cases: list[dict[str, Any]],
    repo: str,
    answer_mode: str,
    base_settings: MLLESettings,
) -> dict[str, Any]:
    candidate_settings = _candidate_settings(base_settings, candidate)
    case_reports: list[dict[str, Any]] = []

    for case in cases:
        question = case["question"]
        start = time.perf_counter()
        error: Exception | None = None
        payload: dict[str, Any] | None = None
        try:
            with patch("mllo_web.core.workflows.nlq.load_settings", return_value=candidate_settings):
                response = await execute_nlq(question, repo=repo, answer_mode=answer_mode)
            payload = response.model_dump(mode="json")
        except Exception as exc:  # pragma: no cover - live benchmark helper
            error = exc
        latency_s = time.perf_counter() - start
        case_reports.append(_evaluate_case(case, payload, error, latency_s))

    return {
        "candidate": deepcopy(candidate),
        "summary": _summarize(candidate.get("name", candidate["model"]), case_reports),
        "cases": case_reports,
    }


def _build_markdown_report(
    *,
    timestamp: str,
    repo: str,
    answer_mode: str,
    prompt_manifest: str,
    candidate_config: str,
    scoreboard: list[dict[str, Any]],
    reports: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    lines.append(f"# NLQ Benchmark Report — {timestamp}")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Timestamp | `{timestamp}` |")
    lines.append(f"| Repo | `{repo}` |")
    lines.append(f"| Answer mode | `{answer_mode}` |")
    lines.append(f"| Prompt manifest | `{prompt_manifest}` |")
    lines.append(f"| Candidate config | `{candidate_config}` |")
    lines.append("")

    lines.append("## Scoreboard")
    lines.append("")
    lines.append("| Rank | Candidate | Pass rate | Passed | Failed | Errored | Avg latency | Median latency |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for rank, entry in enumerate(scoreboard, start=1):
        lines.append(
            f"| {rank} | `{entry['candidate']}` | **{entry['pass_rate']:.1%}** "
            f"| {entry['passed']} | {entry['failed']} | {entry['errored']} "
            f"| {entry.get('avg_latency_s', '?')}s | {entry.get('median_latency_s', '?')}s |"
        )
    lines.append("")

    for report in reports:
        cand = report["candidate"]
        cand_name = cand.get("name", cand.get("model", "?"))
        summary = report["summary"]
        lines.append(f"---")
        lines.append("")
        lines.append(f"## Candidate: `{cand_name}`")
        lines.append("")
        lines.append("### Config")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        lines.append(f"| Provider | `{cand.get('provider', '?')}` |")
        lines.append(f"| Model | `{cand.get('model', '?')}` |")
        if cand.get("base_url"):
            lines.append(f"| Base URL | `{cand['base_url']}` |")
        lines.append("")
        lines.append("### Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Pass rate | **{summary['pass_rate']:.1%}** ({summary['passed']}/{summary['cases']}) |")
        lines.append(f"| Errored | {summary['errored']} |")
        lines.append(f"| Avg latency | {summary.get('avg_latency_s', '?')}s |")
        lines.append(f"| Median latency | {summary.get('median_latency_s', '?')}s |")
        lines.append("")
        lines.append("### Case Results")
        lines.append("")
        lines.append("| # | Question | Category | Passed | Tool | Inference | Results | Latency |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for i, case in enumerate(report["cases"], start=1):
            passed_icon = "✅" if case.get("passed") else ("💥" if case.get("error_type") else "❌")
            tool = case.get("intent_tool") or case.get("error_type") or "—"
            inference = "yes" if case.get("inference_used") else "no"
            result_count = case.get("result_count", "—")
            latency = f"{case.get('latency_s', '?')}s"
            category = case.get("category") or "—"
            question_short = case["question"][:60] + ("…" if len(case["question"]) > 60 else "")
            lines.append(f"| {i} | {question_short} | `{category}` | {passed_icon} | `{tool}` | {inference} | {result_count} | {latency} |")
        lines.append("")

        # Failures detail
        failures = [c for c in report["cases"] if not c.get("passed")]
        if failures:
            lines.append("### Failed Cases Detail")
            lines.append("")
            for case in failures:
                lines.append(f"#### ❌ {case['question']}")
                lines.append("")
                if case.get("error_type"):
                    lines.append(f"- **Error type:** `{case['error_type']}`")
                    lines.append(f"- **Error:** {case.get('error', '?')}")
                else:
                    checks = case.get("checks") or {}
                    for check_name, check_val in checks.items():
                        icon = "✅" if check_val else "❌"
                        lines.append(f"- {icon} `{check_name}`")
                    if case.get("sparql_preview"):
                        lines.append("")
                        lines.append("**SPARQL generated:**")
                        lines.append("")
                        lines.append(f"```sparql\n{case['sparql_preview']}\n```")
                lines.append("")

    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark NLQ quality and latency across LLM candidates.")
    parser.add_argument(
        "--prompts",
        default=str(ROOT / "benchmarks" / "nlq" / "prompts" / "model_selection_cases.json"),
        help="Path to benchmark prompt manifest JSON.",
    )
    parser.add_argument(
        "--config",
        default=str(ROOT / "benchmarks" / "nlq" / "configs" / "llm_candidates.example.json"),
        help="Path to candidate config JSON.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output path for the benchmark report JSON.",
    )
    args = parser.parse_args()

    cases = _load_json(Path(args.prompts))
    config = _load_json(Path(args.config))
    base_settings = load_settings()
    repo = config.get("repo") or os.environ.get("REPO") or base_settings.graphdb_default_repo
    answer_mode = config.get("answer_mode") or "auto"
    candidates = config.get("candidates", [])
    if not candidates:
        raise SystemExit("No candidates found in config.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) if args.output else ROOT / "benchmarks" / "nlq" / "results" / f"llm_benchmark_{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reports = []
    for candidate in candidates:
        print(f"[candidate] {candidate.get('name', candidate['model'])}", flush=True)
        report = await _run_candidate(
            candidate=candidate,
            cases=cases,
            repo=repo,
            answer_mode=answer_mode,
            base_settings=base_settings,
        )
        reports.append(report)
        output_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")
        print(json.dumps(report["summary"], indent=2), flush=True)

    scoreboard = sorted((report["summary"] for report in reports), key=lambda item: (-item["pass_rate"], item["median_latency_s"] or 10**9))
    final_payload = {
        "repo": repo,
        "answer_mode": answer_mode,
        "prompt_manifest": str(Path(args.prompts)),
        "candidate_config": str(Path(args.config)),
        "scoreboard": scoreboard,
        "reports": reports,
    }
    output_path.write_text(json.dumps(final_payload, indent=2), encoding="utf-8")
    print(f"[saved] {output_path}", flush=True)
    print(json.dumps(scoreboard, indent=2))

    md_path = output_path.with_suffix(".md")
    md = _build_markdown_report(
        timestamp=timestamp,
        repo=repo,
        answer_mode=answer_mode,
        prompt_manifest=str(Path(args.prompts)),
        candidate_config=str(Path(args.config)),
        scoreboard=scoreboard,
        reports=reports,
    )
    md_path.write_text(md, encoding="utf-8")
    print(f"[saved] {md_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
