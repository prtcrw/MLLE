from __future__ import annotations

import contextvars
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from mllo_web.app.api.services.settings_model import get_app_data_dir

logger = logging.getLogger(__name__)

_current_trace: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "mllo_nlq_trace",
    default=None,
)


def _logs_dir() -> Path:
    return get_app_data_dir() / "nlq_logs"


def _log_file_path(timestamp: datetime | None = None) -> Path:
    current = timestamp or datetime.now(UTC)
    return _logs_dir() / f"nlq_{current.strftime('%Y%m%d')}.jsonl"


def start_nlq_trace(*, enabled: bool, metadata: dict[str, Any]) -> contextvars.Token:
    trace = {
        "enabled": enabled,
        "request_id": uuid4().hex,
        "started_at": datetime.now(UTC).isoformat(),
        "metadata": metadata,
        "llm_calls": [],
    }
    return _current_trace.set(trace)


def update_nlq_trace(**fields: Any) -> None:
    trace = _current_trace.get()
    if trace is None:
        return
    trace.update(fields)


def record_llm_call(
    *,
    purpose: str | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    messages: list[dict[str, Any]],
    prompt_chars: int,
    response_text: str | None = None,
    error: str | None = None,
) -> None:
    trace = _current_trace.get()
    if trace is None:
        return
    trace["llm_calls"].append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "purpose": purpose or "unspecified",
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "prompt_chars": prompt_chars,
            "messages": messages,
            "response_text": response_text,
            "error": error,
        }
    )


def finalize_nlq_trace(*, success: bool, payload: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any] | None:
    trace = _current_trace.get()
    if trace is None:
        return None

    trace["finished_at"] = datetime.now(UTC).isoformat()
    trace["success"] = success
    trace["payload"] = payload or {}
    trace["error"] = error

    if trace.get("enabled"):
        path = _log_file_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(trace, ensure_ascii=True) + "\n")
        except OSError as exc:
            logger.warning("Failed to write NLQ trace log to %s: %s", path, exc)

    return trace


def reset_nlq_trace(token: contextvars.Token) -> None:
    _current_trace.reset(token)


def get_recent_nlq_logs(limit: int = 20) -> list[dict[str, Any]]:
    logs_dir = _logs_dir()
    if not logs_dir.exists():
        return []

    entries: list[dict[str, Any]] = []
    for path in sorted(logs_dir.glob("nlq_*.jsonl"), reverse=True):
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(entries) >= limit:
                return entries
    return entries
