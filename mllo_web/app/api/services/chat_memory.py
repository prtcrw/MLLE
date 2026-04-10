from __future__ import annotations

from typing import Any


class ChatMemoryStore:
    def __init__(self) -> None:
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        return [dict(message) for message in self._sessions.get(session_id, [])]

    def set_messages(self, session_id: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._sessions[session_id] = [dict(message) for message in messages]
        return self.get_messages(session_id)

    def clear_messages(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


chat_memory_store = ChatMemoryStore()
