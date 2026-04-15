from __future__ import annotations

from fastapi import APIRouter, HTTPException

from mllo_web.app.api.services.nlq_service import (
    NLQRequest,
    NLQResponse,
    execute_nlq,
)

router = APIRouter(prefix="/v1/nlq", tags=["natural-language-query"])


@router.post("/query")
async def nlq_query(body: NLQRequest) -> NLQResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    return await execute_nlq(question, repo=body.repo, answer_mode=body.answer_mode)
