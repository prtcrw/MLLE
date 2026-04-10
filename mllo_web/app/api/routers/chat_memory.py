from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from mllo_web.app.api.services.chat_memory import chat_memory_store

router = APIRouter(prefix="/v1/chat-memory", tags=["chat-memory"])


class ChatMessagePayload(BaseModel):
    id: str
    role: str
    text: str
    payload: dict[str, Any] | None = None


class ChatSessionPayload(BaseModel):
    session_id: str = Field(min_length=1)
    messages: list[ChatMessagePayload] = Field(default_factory=list)


@router.get("")
async def get_chat_memory(session_id: str = Query(..., alias="session_id")) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "messages": chat_memory_store.get_messages(session_id),
    }


@router.put("")
async def put_chat_memory(payload: ChatSessionPayload) -> dict[str, Any]:
    return {
        "session_id": payload.session_id,
        "messages": chat_memory_store.set_messages(
            payload.session_id,
            [message.model_dump(mode="json") for message in payload.messages],
        ),
    }


@router.delete("")
async def delete_chat_memory(session_id: str = Query(..., alias="session_id")) -> dict[str, Any]:
    chat_memory_store.clear_messages(session_id)
    return {"ok": True, "session_id": session_id}
