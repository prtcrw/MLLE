from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mllo_web.app.api.services.intent_classifier import QueryIntent


class NLQRequest(BaseModel):
    question: str
    repo: str | None = None
    answer_mode: str | None = None


class NLQStepRecord(BaseModel):
    step_id: str
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)
    sparql: str | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)
    inference_used: bool = False
    reasoning: str | None = None


class NLQPlannedStep(BaseModel):
    step_id: str
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)
    reasoning: str | None = None


class NLQQueryState(BaseModel):
    question: str
    repo: str
    plan: list[NLQPlannedStep] = Field(default_factory=list)
    steps: list[NLQStepRecord] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)

    def add_plan_step(
        self,
        *,
        tool: str,
        params: dict[str, Any] | None = None,
        reasoning: str | None = None,
    ) -> NLQPlannedStep:
        record = NLQPlannedStep(
            step_id=f"plan_{len(self.plan) + 1}",
            tool=tool,
            params=params or {},
            reasoning=reasoning,
        )
        self.plan.append(record)
        return record

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


class NLQResponse(BaseModel):
    question: str
    intent: QueryIntent
    sparql: str
    results: list[dict[str, Any]]
    answer: str
    repo_used: str
    inference_used: bool


class NLQExecutionPayload(BaseModel):
    sparql: str
    results: list[dict[str, Any]]
    inference_used: bool
    state: NLQQueryState

