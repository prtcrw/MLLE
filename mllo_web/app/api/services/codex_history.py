from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

SESSION_ID_PATTERN = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
CONTROL_PREFIXES = (
    "<environment_context>",
    "<collaboration_mode>",
    "<apps_instructions>",
    "<skills_instructions>",
    "<plugins_instructions>",
)


def _codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def _session_id_from_path(path: Path) -> str:
    match = SESSION_ID_PATTERN.search(path.name)
    return match.group(1) if match else path.stem


def _session_files(codex_home: Path) -> list[Path]:
    roots = [codex_home / "sessions", codex_home / "archived_sessions"]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*.jsonl") if path.is_file())
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def _load_thread_names(codex_home: Path) -> dict[str, dict[str, str]]:
    index_path = codex_home / "session_index.jsonl"
    if not index_path.exists():
        return {}

    index: dict[str, dict[str, str]] = {}
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = str(entry.get("id") or "")
        if session_id:
            index[session_id] = {
                "thread_name": str(entry.get("thread_name") or "Untitled Codex thread"),
                "updated_at": str(entry.get("updated_at") or ""),
            }
    return index


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts).strip()


def _is_visible_chat_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return not any(stripped.startswith(prefix) for prefix in CONTROL_PREFIXES)


def _compact_preview(text: str, length: int = 420) -> str:
    compact = " ".join(text.split())
    if len(compact) <= length:
        return compact
    return f"{compact[: length - 1].rstrip()}..."


def _parse_session(path: Path, thread_index: dict[str, dict[str, str]]) -> dict[str, Any] | None:
    session_id = _session_id_from_path(path)
    meta: dict[str, Any] = {}
    messages: list[dict[str, str]] = []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type")
        payload = event.get("payload")
        if event_type == "session_meta" and isinstance(payload, dict):
            meta.update(payload)
            continue

        if event_type != "response_item" or not isinstance(payload, dict):
            continue
        if payload.get("type") != "message":
            continue

        role = payload.get("role")
        if role not in {"user", "assistant"}:
            continue

        text = _extract_text(payload.get("content"))
        if not _is_visible_chat_text(text):
            continue
        messages.append({"role": str(role), "text": text})

    if not messages and not meta:
        return None

    indexed = thread_index.get(session_id, {})
    updated_at = str(indexed.get("updated_at") or meta.get("timestamp") or "")
    started_at = str(meta.get("timestamp") or updated_at)
    cwd = str(meta.get("cwd") or "")
    title = str(indexed.get("thread_name") or "Untitled Codex thread")
    user_messages = [message["text"] for message in messages if message["role"] == "user"]
    assistant_messages = [message["text"] for message in messages if message["role"] == "assistant"]

    return {
        "id": session_id,
        "thread_name": title,
        "started_at": started_at,
        "updated_at": updated_at,
        "cwd": cwd,
        "source_path": str(path),
        "message_count": len(messages),
        "user_message_count": len(user_messages),
        "assistant_message_count": len(assistant_messages),
        "first_user_message": _compact_preview(user_messages[0]) if user_messages else "",
        "last_user_message": _compact_preview(user_messages[-1]) if user_messages else "",
        "last_assistant_message": _compact_preview(assistant_messages[-1]) if assistant_messages else "",
        "recent_messages": [
            {"role": message["role"], "text": _compact_preview(message["text"], 900)}
            for message in messages[-8:]
        ],
    }


def get_codex_chat_history(
    *,
    limit: int = 50,
    query: str | None = None,
    workspace: str | None = None,
    codex_home: Path | None = None,
) -> list[dict[str, Any]]:
    home = codex_home or _codex_home()
    if not home.exists():
        return []

    normalized_query = (query or "").strip().lower()
    workspace_filter = (workspace or str(Path.cwd())).strip()
    thread_index = _load_thread_names(home)
    entries: list[dict[str, Any]] = []

    for path in _session_files(home):
        entry = _parse_session(path, thread_index)
        if entry is None:
            continue

        if workspace_filter:
            cwd = str(entry.get("cwd") or "")
            source_path = str(entry.get("source_path") or "")
            searchable_path = f"{cwd} {source_path}"
            if workspace_filter not in searchable_path and Path(workspace_filter).name not in searchable_path:
                continue

        if normalized_query:
            searchable = " ".join(
                [
                    str(entry.get("thread_name") or ""),
                    str(entry.get("cwd") or ""),
                    str(entry.get("first_user_message") or ""),
                    str(entry.get("last_user_message") or ""),
                    str(entry.get("last_assistant_message") or ""),
                ]
            ).lower()
            if normalized_query not in searchable:
                continue

        entries.append(entry)
        if len(entries) >= limit:
            break

    return entries
