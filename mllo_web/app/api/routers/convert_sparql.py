"""Compatibility wrapper for the legacy convert-to-SPARQL endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mllo_web.app.api.routers.natural_language_query import execute_nlq

router = APIRouter()


class ConvertRequest(BaseModel):
    input: str
    repo: str | None = None
    answer_mode: str | None = None


@router.post("/convert-sparql")
async def convert_sparql(body: ConvertRequest):
    text = body.input.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty input")

    response = await execute_nlq(
        text,
        repo=body.repo,
        answer_mode=body.answer_mode,
    )
    return {
        "sparql": response.sparql,
        "results": response.results,
        "error": None,
    }
