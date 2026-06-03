from __future__ import annotations

from fastapi import APIRouter, HTTPException

from mllo_web.app.api.services.codex_history import get_codex_chat_history
from mllo_web.app.api.services.graphdb_client import GraphDBClient
from mllo_web.app.api.services.interaction_logging import get_recent_nlq_logs
from mllo_web.app.api.services.llm_gateway import LLMGateway, LLMServiceError
from mllo_web.app.api.services.settings_model import MLLESettings, load_settings, save_settings

router = APIRouter(prefix="/v1/settings", tags=["settings"])


@router.get("")
async def get_settings() -> MLLESettings:
    return load_settings()


@router.put("")
async def put_settings(settings: MLLESettings) -> MLLESettings:
    try:
        return save_settings(settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/repos")
async def get_repos() -> dict:
    settings = load_settings()
    client = GraphDBClient(
        base_url=settings.graphdb_url,
        default_repo=settings.graphdb_default_repo,
        repo_allowlist=settings.graphdb_repo_allowlist,
    )
    try:
        repos = await client.list_repos()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if settings.graphdb_repo_allowlist is not None:
        repos = [repo for repo in repos if repo in settings.graphdb_repo_allowlist]
    return {"repos": repos}


@router.post("/test-llm")
async def test_llm(settings: MLLESettings | None = None) -> dict:
    resolved_settings = settings or load_settings()
    provider = resolved_settings.llm_providers[resolved_settings.active_llm_provider]
    gateway = LLMGateway()
    try:
        text = await gateway.chat_completion(
            [
                {"role": "system", "content": "Reply with TEST_OK only."},
                {"role": "user", "content": "Ping"},
            ],
            provider.model_dump(),
            purpose="settings_test_connection",
        )
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True, "response": text}


@router.get("/nlq-logs")
async def get_nlq_logs(limit: int = 20) -> dict:
    capped_limit = max(1, min(limit, 100))
    return {"logs": get_recent_nlq_logs(capped_limit)}


@router.get("/codex-history")
async def get_codex_history(limit: int = 50, query: str | None = None) -> dict:
    capped_limit = max(1, min(limit, 100))
    return {"history": get_codex_chat_history(limit=capped_limit, query=query)}
