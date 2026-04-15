from __future__ import annotations

from fastapi import APIRouter, Query, Request

from mllo_web.app.api.services.pipeline_editor_service import (
    PipelineEditorDraft,
    PipelineEditorState,
    ValidationResponse,
    delete_draft as delete_pipeline_editor_draft,
    get_draft as get_pipeline_editor_draft,
    get_existing_pipelines as get_pipeline_editor_existing,
    get_history as get_pipeline_editor_history,
    publish_draft as publish_pipeline_editor_draft,
    save_draft as save_pipeline_editor_draft,
    validate_draft as validate_pipeline_editor_draft,
)

router = APIRouter(prefix="/v1/pipeline-editor", tags=["pipeline-editor"])


@router.get("/draft")
async def get_draft(request: Request, pipeline_name: str = Query(..., alias="pipeline_name")) -> PipelineEditorState:
    return await get_pipeline_editor_draft(request, pipeline_name)


@router.get("/existing")
async def get_existing_pipelines(request: Request, search_term: str | None = Query(default=None, alias="search_term")) -> dict:
    return await get_pipeline_editor_existing(request, search_term)


@router.delete("/draft")
async def delete_draft(pipeline_name: str = Query(..., alias="pipeline_name")) -> dict:
    return await delete_pipeline_editor_draft(pipeline_name)


@router.post("/save-draft")
async def save_draft(draft: PipelineEditorDraft) -> PipelineEditorState:
    return await save_pipeline_editor_draft(draft)


@router.post("/validate")
async def validate_draft(draft: PipelineEditorDraft) -> ValidationResponse:
    return await validate_pipeline_editor_draft(draft)


@router.post("/publish")
async def publish_draft(draft: PipelineEditorDraft) -> dict:
    return await publish_pipeline_editor_draft(draft)


@router.get("/history")
async def get_history(pipeline_name: str = Query(..., alias="pipeline_name")) -> dict:
    return await get_pipeline_editor_history(pipeline_name)
