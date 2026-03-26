from __future__ import annotations

import json
import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mllo_web.app.api.services.settings_model import get_app_data_dir

router = APIRouter(prefix="/v1/pipeline-editor", tags=["pipeline-editor"])


class PipelineEditorNode(BaseModel):
    id: str
    iri: str
    title: str
    kind: Literal["input", "operation", "output", "model"]
    status: Literal["stable", "draft", "warning"]
    position: int
    note: str = ""


class PipelineEditorEdge(BaseModel):
    source: str
    target: str
    relation: str


class PipelineEditorDraft(BaseModel):
    pipelineName: str = Field(min_length=1)
    savedAt: str
    validationStatus: Literal["unknown", "passed", "failed"] = "unknown"
    validationMessage: str = ""
    nodes: list[PipelineEditorNode]
    edges: list[PipelineEditorEdge]


class PipelineEditorVersion(BaseModel):
    version: str
    label: str
    note: str
    status: Literal["ready", "review", "archived"]
    savedAt: str


class PipelineEditorState(BaseModel):
    draft: PipelineEditorDraft | None = None
    history: list[PipelineEditorVersion] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    ok: bool
    validation_status: Literal["passed", "failed"]
    validation_message: str
    violations: list[str] = Field(default_factory=list)


VALIDATION_EXPECTATIONS: dict[str, list[str]] = {
    "reshape": ["scale"],
    "scale": ["cast"],
    "cast": ["processed"],
    "processed": ["model"],
}


def _slugify_pipeline_name(pipeline_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", pipeline_name.strip()).strip("-").lower()
    return slug or "pipeline"


def _pipeline_dir(pipeline_name: str) -> Path:
    return get_app_data_dir() / "pipeline_editor" / _slugify_pipeline_name(pipeline_name)


def _draft_path(pipeline_name: str) -> Path:
    return _pipeline_dir(pipeline_name) / "draft.json"


def _history_path(pipeline_name: str) -> Path:
    return _pipeline_dir(pipeline_name) / "history.json"


def _versions_dir(pipeline_name: str) -> Path:
    return _pipeline_dir(pipeline_name) / "versions"


def _load_history(pipeline_name: str) -> list[PipelineEditorVersion]:
    path = _history_path(pipeline_name)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [PipelineEditorVersion.model_validate(item) for item in raw]


def _save_history(pipeline_name: str, history: list[PipelineEditorVersion]) -> None:
    path = _history_path(pipeline_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([item.model_dump(mode="json") for item in history], indent=2),
        encoding="utf-8",
    )


def _validate_draft(draft: PipelineEditorDraft) -> list[str]:
    node_order = [node.id for node in sorted(draft.nodes, key=lambda item: item.position)]
    node_lookup = {node.id: node for node in draft.nodes}
    violations: list[str] = []

    for source_id, target_ids in VALIDATION_EXPECTATIONS.items():
        for target_id in target_ids:
            source_index = node_order.index(source_id) if source_id in node_order else -1
            target_index = node_order.index(target_id) if target_id in node_order else -1
            if source_index == -1 or target_index == -1:
                violations.append(f"Missing required node relationship: {source_id} -> {target_id}.")
                continue
            if source_index >= target_index:
                source_title = node_lookup.get(source_id).title if source_id in node_lookup else source_id
                target_title = node_lookup.get(target_id).title if target_id in node_lookup else target_id
                violations.append(f"{source_title} must appear before {target_title}.")

    return violations


@router.get("/draft")
async def get_draft(pipeline_name: str = Query(..., alias="pipeline_name")) -> PipelineEditorState:
    draft_path = _draft_path(pipeline_name)
    draft = None
    if draft_path.exists():
        raw = json.loads(draft_path.read_text(encoding="utf-8"))
        draft = PipelineEditorDraft.model_validate(raw)
    history = _load_history(pipeline_name)
    return PipelineEditorState(draft=draft, history=history)


@router.delete("/draft")
async def delete_draft(pipeline_name: str = Query(..., alias="pipeline_name")) -> dict:
    draft_path = _draft_path(pipeline_name)
    if draft_path.exists():
        draft_path.unlink()
    return {"ok": True}


@router.post("/save-draft")
async def save_draft(draft: PipelineEditorDraft) -> PipelineEditorState:
    draft_path = _draft_path(draft.pipelineName)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(
        json.dumps(draft.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    history = _load_history(draft.pipelineName)
    return PipelineEditorState(draft=draft, history=history)


@router.post("/validate")
async def validate_draft(draft: PipelineEditorDraft) -> ValidationResponse:
    violations = _validate_draft(draft)
    if violations:
        return ValidationResponse(
            ok=False,
            validation_status="failed",
            validation_message=violations[0],
            violations=violations,
        )
    return ValidationResponse(
        ok=True,
        validation_status="passed",
        validation_message="Draft is structurally consistent and ready for publish.",
    )


@router.post("/publish")
async def publish_draft(draft: PipelineEditorDraft) -> dict:
    violations = _validate_draft(draft)
    if violations:
        raise HTTPException(status_code=422, detail=violations[0])

    pipeline_dir = _pipeline_dir(draft.pipelineName)
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    versions_dir = _versions_dir(draft.pipelineName)
    versions_dir.mkdir(parents=True, exist_ok=True)

    history = _load_history(draft.pipelineName)
    version_number = len(history) + 1
    published_at = datetime.now(UTC).isoformat()
    version_name = f"v{version_number}.0"
    version_note = f"Published from editor draft with {len(draft.nodes)} nodes and {len(draft.edges)} edges."
    version_record = PipelineEditorVersion(
        version=version_name,
        label="Published draft",
        note=version_note,
        status="ready",
        savedAt=published_at,
    )
    history.insert(0, version_record)
    _save_history(draft.pipelineName, history)

    version_payload = {
        "publishedAt": published_at,
        "draft": {
            **draft.model_dump(mode="json"),
            "validationStatus": "passed",
            "validationMessage": "Published after backend validation.",
        },
        "version": version_record.model_dump(mode="json"),
    }
    version_file = versions_dir / f"{version_name.replace('.', '_')}_{published_at.replace(':', '-')}.json"
    version_file.write_text(json.dumps(version_payload, indent=2), encoding="utf-8")

    draft_path = _draft_path(draft.pipelineName)
    draft_path.write_text(
        json.dumps(version_payload["draft"], indent=2),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "published_at": published_at,
        "version": version_record,
        "draft": version_payload["draft"],
        "history": history,
    }


@router.get("/history")
async def get_history(pipeline_name: str = Query(..., alias="pipeline_name")) -> dict:
    return {"history": _load_history(pipeline_name)}
