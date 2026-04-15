"""
trace_nlq.py — Run a single NLQ question and produce a step-by-step Markdown trace.

Usage:
    python scripts/trace_nlq.py "What downstream artifacts use MnistG16?"

Options:
    --repo REPO           GraphDB repo to query (default: from settings)
    --answer-mode MODE    exact | conceptual | auto  (default: auto)
    --output PATH         Where to write the .md report (default: tmp/trace_<timestamp>.md)
    --no-md               Skip the Markdown file; only print to stdout

The script captures every LLM call (purpose, model, full prompts, raw response, latency),
the resolved intent, the generated / repaired SPARQL, GraphDB results, and the final answer,
then formats them as a readable step-by-step Markdown document.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mllo_web.app.api.services import interaction_logging as _ilog
from mllo_web.app.api.services.llm_gateway import LLMGateway
from mllo_web.core.workflows.nlq import execute_nlq
from mllo_web.app.api.services.settings_model import load_settings


# ---------------------------------------------------------------------------
# Monkey-patch: add per-call latency to every LLM call recorded in the trace
# ---------------------------------------------------------------------------

_original_chat_completion = LLMGateway.chat_completion


async def _timed_chat_completion(self: LLMGateway, messages: list[dict], provider_config: dict, purpose: str | None = None) -> str:
    t0 = time.perf_counter()
    result = await _original_chat_completion(self, messages, provider_config, purpose)
    elapsed = round(time.perf_counter() - t0, 3)
    # The last appended llm_call was recorded inside the original; stamp latency on it
    trace = _ilog._current_trace.get()
    if trace and trace.get("llm_calls"):
        trace["llm_calls"][-1]["latency_s"] = elapsed
    return result


LLMGateway.chat_completion = _timed_chat_completion  # type: ignore[method-assign]

# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

_FENCE = "```"


def _md_code(lang: str, text: str) -> str:
    return f"{_FENCE}{lang}\n{text.strip()}\n{_FENCE}"


def _md_json(obj: Any) -> str:
    return _md_code("json", json.dumps(obj, indent=2, ensure_ascii=False))


def _truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + f"\n\n… [{len(text) - limit} chars omitted] …\n\n" + text[-half:]


def _render_llm_call(idx: int, call: dict[str, Any]) -> str:
    lines: list[str] = []
    purpose = call.get("purpose") or "unspecified"
    model = call.get("model") or "?"
    provider = call.get("provider") or "?"
    latency = call.get("latency_s")
    latency_str = f"{latency}s" if latency is not None else "n/a"

    lines.append(f"### LLM Call {idx} — `{purpose}`")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Provider | `{provider}` |")
    lines.append(f"| Model | `{model}` |")
    lines.append(f"| Latency | {latency_str} |")
    lines.append(f"| Prompt chars | {call.get('prompt_chars', '?')} |")
    if call.get("base_url"):
        lines.append(f"| Base URL | `{call['base_url']}` |")
    lines.append("")

    messages: list[dict] = call.get("messages") or []
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = str(msg.get("content") or "")
        lines.append(f"**{role} prompt:**")
        lines.append("")
        lines.append(_md_code("text", _truncate(content, 3000)))
        lines.append("")

    if call.get("error"):
        lines.append(f"**Error:** `{call['error']}`")
        lines.append("")
    elif call.get("response_text"):
        lines.append("**Raw LLM response:**")
        lines.append("")
        lines.append(_md_code("text", _truncate(call["response_text"], 3000)))
        lines.append("")

    return "\n".join(lines)


def build_markdown(trace: dict[str, Any], response_dump: dict[str, Any] | None) -> str:
    sections: list[str] = []

    # ── Header ──────────────────────────────────────────────────────────────
    started_at = trace.get("started_at", "?")
    finished_at = trace.get("finished_at", "?")
    meta = trace.get("metadata", {})
    question = meta.get("question", "?")

    try:
        duration = round(
            (datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)).total_seconds(), 3
        )
        duration_str = f"{duration}s"
    except Exception:
        duration_str = "?"

    sections.append(f"# NLQ Trace — {started_at[:19].replace('T', ' ')} UTC")
    sections.append("")

    # ── Metadata ────────────────────────────────────────────────────────────
    sections.append("## Metadata")
    sections.append("")
    sections.append("| Field | Value |")
    sections.append("|---|---|")
    sections.append(f"| Question | {question} |")
    sections.append(f"| Repo requested | `{meta.get('repo_requested') or 'default'}` |")
    sections.append(f"| Answer mode | `{meta.get('answer_mode_requested') or 'auto'}` |")
    sections.append(f"| Active LLM provider | `{meta.get('active_llm_provider') or '?'}` |")
    sections.append(f"| Started at | `{started_at}` |")
    sections.append(f"| Finished at | `{finished_at}` |")
    sections.append(f"| Total duration | **{duration_str}** |")
    sections.append(f"| Request ID | `{trace.get('request_id', '?')}` |")
    sections.append(f"| Success | {'✅ yes' if trace.get('success') else '❌ no'} |")
    if trace.get("error"):
        sections.append(f"| Error | `{trace['error']}` |")
    sections.append("")

    # ── LLM calls ───────────────────────────────────────────────────────────
    llm_calls: list[dict] = trace.get("llm_calls") or []

    if llm_calls:
        sections.append("---")
        sections.append("")
        sections.append("## LLM Calls (step by step)")
        sections.append("")
        for i, call in enumerate(llm_calls, start=1):
            sections.append(_render_llm_call(i, call))
            sections.append("---")
            sections.append("")
    else:
        sections.append("*No LLM calls were recorded.*")
        sections.append("")

    # ── Execution plan & steps ──────────────────────────────────────────────
    payload = trace.get("payload") or {}
    plan = payload.get("plan") or []
    steps = payload.get("steps") or []

    if plan:
        sections.append("## Execution Plan")
        sections.append("")
        for i, step in enumerate(plan, start=1):
            sections.append(f"**Step {i}** — tool: `{step.get('tool')}`, reasoning: {step.get('reasoning') or '—'}")
            if step.get("params"):
                sections.append("")
                sections.append(_md_json(step["params"]))
        sections.append("")

    if steps:
        sections.append("## Execution Steps")
        sections.append("")
        for i, step in enumerate(steps, start=1):
            sections.append(f"### Execution Step {i} — `{step.get('tool')}`")
            sections.append("")
            sections.append(f"- Inference used: `{step.get('inference_used')}`")
            sections.append(f"- Result count: `{len(step.get('results') or [])}`")
            if step.get("params"):
                sections.append("")
                sections.append("**Params:**")
                sections.append(_md_json(step["params"]))
            if step.get("sparql"):
                sections.append("")
                sections.append("**SPARQL:**")
                sections.append(_md_code("sparql", step["sparql"]))
            if step.get("results"):
                sections.append("")
                sections.append("**Results preview (first 5 rows):**")
                sections.append(_md_json(step["results"][:5]))
            sections.append("")

    # ── Final response ───────────────────────────────────────────────────────
    if response_dump:
        sections.append("---")
        sections.append("")
        sections.append("## Final Response")
        sections.append("")
        resp = payload.get("response") or response_dump

        intent = resp.get("intent") or {}
        sections.append(f"**Intent:** tool=`{intent.get('tool')}`, use_inference=`{intent.get('use_inference')}`, reasoning: {intent.get('reasoning') or '—'}")
        sections.append("")
        sections.append(f"**Repo used:** `{resp.get('repo_used')}`")
        sections.append(f"**Inference used:** `{resp.get('inference_used')}`")
        sections.append(f"**Result count:** `{len(resp.get('results') or [])}`")
        sections.append("")

        if resp.get("sparql"):
            sections.append("**Final SPARQL:**")
            sections.append("")
            sections.append(_md_code("sparql", resp["sparql"]))
            sections.append("")

        if resp.get("results"):
            sections.append("**Results preview (first 5 rows):**")
            sections.append("")
            sections.append(_md_json((resp["results"] or [])[:5]))
            sections.append("")

        if resp.get("answer"):
            sections.append("**Answer:**")
            sections.append("")
            sections.append(f"> {resp['answer']}")
            sections.append("")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(question: str, repo: str | None, answer_mode: str | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Run execute_nlq with logging forced on and return (trace, response_dump)."""
    settings = load_settings()

    # Force logging on for this run regardless of settings file
    original_finalize = _ilog.finalize_nlq_trace
    captured_trace: dict[str, Any] = {}

    def capturing_finalize(*, success: bool, payload: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any] | None:
        result = original_finalize(success=success, payload=payload, error=error)
        if result:
            captured_trace.update(result)
        return result

    _ilog.finalize_nlq_trace = capturing_finalize  # type: ignore[assignment]

    # Patch settings to enable logging so the trace is also persisted to disk
    original_load = None
    try:
        import mllo_web.core.workflows.nlq as _nlq_mod
        import mllo_web.app.api.services.interaction_logging as _ilog_mod

        original_start = _ilog_mod.start_nlq_trace

        def patched_start(*, enabled: bool, metadata: dict[str, Any]) -> Any:
            return original_start(enabled=True, metadata=metadata)  # force enabled

        _ilog_mod.start_nlq_trace = patched_start  # type: ignore[assignment]

        response = await execute_nlq(question, repo=repo, answer_mode=answer_mode)
        response_dump = response.model_dump(mode="json")
    finally:
        _ilog_mod.start_nlq_trace = original_start  # type: ignore[assignment]
        _ilog.finalize_nlq_trace = original_finalize  # type: ignore[assignment]

    return captured_trace, response_dump


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace a single NLQ question and emit a step-by-step Markdown report.")
    parser.add_argument("question", nargs="?", default="What downstream artifacts use MnistG16?", help="The natural language question to trace.")
    parser.add_argument("--repo", default=None, help="GraphDB repo (default: from settings).")
    parser.add_argument("--answer-mode", default="auto", choices=["exact", "conceptual", "auto"], help="Answer mode.")
    parser.add_argument("--output", default="", help="Output .md path. Defaults to tmp/trace_<timestamp>.md")
    parser.add_argument("--no-md", action="store_true", help="Skip writing the .md file; only print to stdout.")
    args = parser.parse_args()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) if args.output else ROOT / "tmp" / f"trace_{timestamp}.md"

    print(f"[trace] question: {args.question}", flush=True)
    print(f"[trace] repo: {args.repo or 'default'}", flush=True)

    try:
        trace, response_dump = asyncio.run(run(args.question, args.repo, args.answer_mode))
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)

    md = build_markdown(trace, response_dump)

    print(md, flush=True)

    if not args.no_md:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")
        print(f"\n[saved] {output_path}", flush=True)


if __name__ == "__main__":
    main()
