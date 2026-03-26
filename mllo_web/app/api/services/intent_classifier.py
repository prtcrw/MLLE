from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel

from mllo_web.app.api.services.llm_gateway import LLMGateway


class QueryIntent(BaseModel):
    tool: Literal[
        "find_datasets",
        "find_models",
        "find_pipelines",
        "analyze_deployed_models",
        "compare_pipelines",
        "get_artifact_details",
        "explore_category",
        "custom_sparql",
    ]
    params: dict
    use_inference: bool
    reasoning: str


INTENT_SYSTEM_PROMPT = """
You classify ML lifecycle questions for the MLLE ontology explorer.

Available tools:
- find_datasets: dataset lookup by name, role, timeframe, or related model
- find_models: model lookup by dataset, model type, or search term
- find_pipelines: pipeline lookup by name, pipeline type, associated model, or dataset
- analyze_deployed_models: deployed model inventory and runtime analysis
- compare_pipelines: explicit comparison between multiple named pipelines
- get_artifact_details: direct IRI lookup or questions about a specific full IRI
- explore_category: conceptual or hierarchical exploration of a class/category/type
- custom_sparql: fallback for anything too custom for the structured tools

Set use_inference=true for conceptual or hierarchical questions, especially when the question includes:
"type of", "kind of", "category", "all supervised", "is it a", "related to", "what are", "classify"

Set use_inference=false for exact lookup questions, especially when the question includes:
specific names, dates, owners, counts, "show me X", "find X named Y"

Use custom_sparql with use_inference=false for ranking, aggregation, or metric-based questions, especially when the question includes:
"best", "top", "highest", "lowest", "maximum", "minimum", "max", "min", "most accurate", "least accurate", "performance", "accuracy", "score", "metric"

Do not use explore_category for ranking, performance, or superlative questions.

Return JSON only with:
{
  "tool": "...",
  "params": {},
  "use_inference": true|false,
  "reasoning": "brief explanation"
}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def _fallback_intent(question: str) -> QueryIntent:
    lowered = question.lower()
    use_inference = any(
        phrase in lowered
        for phrase in ["type of", "kind of", "category", "all supervised", "is it a", "related to", "what are", "classify"]
    )
    is_ranking_or_metric = any(
        phrase in lowered
        for phrase in [
            "best",
            "top",
            "highest",
            "lowest",
            "maximum",
            "minimum",
            "max ",
            " min ",
            "most accurate",
            "least accurate",
            "performance",
            "accuracy",
            "score",
            "metric",
        ]
    )
    if "http://" in question or "https://" in question:
        iri = re.search(r"https?://\S+", question)
        return QueryIntent(
            tool="get_artifact_details",
            params={"iri": iri.group(0).rstrip(".,)") if iri else ""},
            use_inference=False,
            reasoning="Fallback selected IRI lookup because the question contains a full IRI.",
        )
    if "compare" in lowered and "pipeline" in lowered:
        return QueryIntent(
            tool="compare_pipelines",
            params={"pipeline_ids": re.findall(r"[A-Za-z][A-Za-z0-9_:-]+", question)},
            use_inference=False,
            reasoning="Fallback selected pipeline comparison because the question asks to compare pipelines.",
        )
    if "deployed" in lowered:
        return QueryIntent(
            tool="analyze_deployed_models",
            params={},
            use_inference=False,
            reasoning="Fallback selected deployed model analysis.",
        )
    if is_ranking_or_metric:
        return QueryIntent(
            tool="custom_sparql",
            params={"question": question},
            use_inference=False,
            reasoning="Fallback selected custom SPARQL for ranking or metric-based analysis.",
        )
    if "pipeline" in lowered:
        return QueryIntent(
            tool="find_pipelines",
            params={"search_term": question},
            use_inference=use_inference,
            reasoning="Fallback selected pipeline lookup.",
        )
    if "dataset" in lowered or "data set" in lowered:
        return QueryIntent(
            tool="find_datasets",
            params={"search_term": question},
            use_inference=use_inference,
            reasoning="Fallback selected dataset lookup.",
        )
    if "model" in lowered:
        return QueryIntent(
            tool="find_models",
            params={"search_term": question},
            use_inference=use_inference,
            reasoning="Fallback selected model lookup.",
        )
    if use_inference:
        return QueryIntent(
            tool="explore_category",
            params={"category_name": question},
            use_inference=True,
            reasoning="Fallback selected conceptual category exploration.",
        )
    return QueryIntent(
        tool="custom_sparql",
        params={"question": question},
        use_inference=False,
        reasoning="Fallback selected custom SPARQL.",
    )


async def classify_intent(
    question: str,
    gateway: LLMGateway,
    provider_config: dict,
) -> QueryIntent:
    try:
        raw = await gateway.chat_completion(
            [
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            provider_config,
        )
        return QueryIntent.model_validate(_extract_json(raw))
    except Exception:
        return _fallback_intent(question)
