from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NLQStepRecord(BaseModel):
    step_id: str
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)
    sparql: str | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)
    inference_used: bool = False
    reasoning: str | None = None


class NLQQueryState(BaseModel):
    question: str
    repo: str
    steps: list[NLQStepRecord] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)

    def add_step(
        self,
        *,
        tool: str,
        params: dict[str, Any] | None = None,
        sparql: str | None = None,
        results: list[dict[str, Any]] | None = None,
        inference_used: bool = False,
        reasoning: str | None = None,
    ) -> NLQStepRecord:
        record = NLQStepRecord(
            step_id=f"step_{len(self.steps) + 1}",
            tool=tool,
            params=params or {},
            sparql=sparql,
            results=results or [],
            inference_used=inference_used,
            reasoning=reasoning,
        )
        self.steps.append(record)
        return record

    def set_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    def get_artifact(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)
