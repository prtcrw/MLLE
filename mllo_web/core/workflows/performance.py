from __future__ import annotations

import re
from typing import Any


def performance_query_spec(question: str) -> dict[str, Any] | None:
    lowered = question.lower()
    if not any(
        token in lowered
        for token in ("performance", "accuracy", "metric", "score", "best", "top", "highest", "lowest", "more than", "less than")
    ):
        return None
    spec: dict[str, Any] = {
        "metric_label": "classification accuracy",
        "limit": 50,
        "order": "DESC",
        "threshold_op": None,
        "threshold_value": None,
    }
    threshold_match = re.search(r"(more than|greater than|above|over|less than|below|under)\s+([0-9]*\.?[0-9]+)", lowered)
    if threshold_match:
        phrase, value = threshold_match.groups()
        spec["threshold_op"] = ">" if phrase in {"more than", "greater than", "above", "over"} else "<"
        spec["threshold_value"] = value
    top_match = re.search(r"top\s+(\d+)", lowered)
    if top_match:
        spec["limit"] = max(1, min(int(top_match.group(1)), 100))
    elif any(token in lowered for token in ("best", "highest")):
        spec["limit"] = 1
    elif any(token in lowered for token in ("lowest", "worst")):
        spec["limit"] = 1
        spec["order"] = "ASC"
    return spec


def build_performance_query_from_spec(spec: dict[str, Any]) -> str:
    threshold_clause = ""
    if spec["threshold_op"] and spec["threshold_value"]:
        threshold_clause = f"FILTER(xsd:decimal(?model_performance_value) {spec['threshold_op']} {spec['threshold_value']})"
    return f"""
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?model_name ?ml_process ?model_performance_metric ?model_performance_value WHERE {{
    ?ml_process bfo:BFO_0000057 ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    ?model_performance_assessment ml:hasDataInput ?model_output .
    ?ml_process ml:hasDataOutput ?model_output .
    ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
    ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment .
    ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
    ?model_performance_metric_type rdfs:subClassOf* ml:PerformanceMetric .
    ?model_performance_metric_type rdfs:label ?model_performance_metric .
    ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
    FILTER(LCASE(STR(?model_performance_metric)) = "{spec['metric_label']}")
    {threshold_clause}
}}
ORDER BY {spec['order']}(xsd:decimal(?model_performance_value))
LIMIT {spec['limit']}
"""


def question_requests_dataset_context(question: str) -> bool:
    lowered = question.lower()
    return any(token in lowered for token in ("test dataset", "dataset", "data set"))


def question_requests_pipeline_context(question: str) -> bool:
    lowered = question.lower()
    return "pipeline" in lowered or "pipelines" in lowered


def build_model_dataset_query(process_iris: list[str], *, dataset_kind: str = "test") -> str:
    escaped_processes = " ".join(f"<{p}>" for p in process_iris if p)
    dataset_class = "ml:TestDataSet" if dataset_kind == "test" else "ml:MachineLearningDataSet"
    return f"""
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?ml_process ?dataset ?dataset_role WHERE {{
    VALUES ?ml_process {{ {escaped_processes} }}
    ?ml_process ml:hasDataInput ?dataset .
    ?dataset rdf:type ?dataset_type .
    ?dataset_type rdfs:subClassOf* {dataset_class} .
    OPTIONAL {{ ?dataset_type rdfs:label ?dataset_role }}
}}
LIMIT 200
"""


def build_model_pipeline_query(model_iris: list[str]) -> str:
    escaped_models = " ".join(f"<{model}>" for model in model_iris if model)
    return f"""
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model_name ?pipeline WHERE {{
    VALUES ?model_name {{ {escaped_models} }}
    ?pipeline bfo:BFO_0000117*/bfo:BFO_0000057 ?model_name .
}}
LIMIT 200
"""


def dedupe_model_performance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (
            row.get("model_name"),
            row.get("ml_process"),
            row.get("model_performance_metric"),
            row.get("model_performance_value"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def aggregate_best_performance_by_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_model: dict[str, dict[str, Any]] = {}
    for row in rows:
        model_name = row.get("model_name")
        if not model_name:
            continue
        current = best_by_model.get(model_name)
        try:
            score = float(row.get("model_performance_value"))
        except (TypeError, ValueError):
            score = float("-inf")
        if current is None:
            best_by_model[model_name] = row
            continue
        try:
            current_score = float(current.get("model_performance_value"))
        except (TypeError, ValueError):
            current_score = float("-inf")
        if score > current_score:
            best_by_model[model_name] = row
    return list(best_by_model.values())


def merge_model_dataset_rows(performance_rows: list[dict[str, Any]], dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Key by ml_process so each test run gets its own specific dataset(s)
    datasets_by_process: dict[str, list[dict[str, Any]]] = {}
    for row in dataset_rows:
        ml_process = row.get("ml_process")
        if not ml_process:
            continue
        bucket = datasets_by_process.setdefault(ml_process, [])
        candidate = {"test_dataset": row.get("dataset"), "test_dataset_role": row.get("dataset_role")}
        if candidate not in bucket:
            bucket.append(candidate)
    merged = []
    for row in performance_rows:
        datasets = datasets_by_process.get(row.get("ml_process"), [])
        if not datasets:
            merged.append({**row, "test_datasets": []})
            continue
        merged.append(
            {
                **row,
                "test_datasets": [item["test_dataset"] for item in datasets if item.get("test_dataset")],
                "test_dataset_roles": [item["test_dataset_role"] for item in datasets if item.get("test_dataset_role")],
            }
        )
    return merged


def merge_model_pipeline_rows(performance_rows: list[dict[str, Any]], pipeline_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pipelines_by_model: dict[str, list[str]] = {}
    for row in pipeline_rows:
        model_name = row.get("model_name")
        pipeline = row.get("pipeline")
        if not model_name or not pipeline:
            continue
        bucket = pipelines_by_model.setdefault(model_name, [])
        if pipeline not in bucket:
            bucket.append(pipeline)
    return [{**row, "pipelines": pipelines_by_model.get(row.get("model_name"), [])} for row in performance_rows]


def plan_performance_enrichment_steps(question: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if question_requests_dataset_context(question):
        steps.append(
            {
                "tool": "find_test_datasets_for_models",
                "params": {"dataset_kind": "test"},
                "reasoning": "The question asks for related test-dataset context.",
            }
        )
    if question_requests_pipeline_context(question):
        steps.append(
            {
                "tool": "find_pipelines_for_models",
                "params": {},
                "reasoning": "The question asks for related pipeline context.",
            }
        )
    return steps


async def execute_performance_orchestration(
    *,
    question: str,
    resolved_repo: str,
    state,
    graphdb_client,
    payload_type,
):
    performance_spec = performance_query_spec(question)
    if not performance_spec:
        raise ValueError("Performance orchestration requires a performance query spec.")

    performance_sparql = build_performance_query_from_spec(performance_spec)
    performance_rows = await graphdb_client.query(performance_sparql, repo=resolved_repo, use_inference=False)
    performance_rows = dedupe_model_performance_rows(performance_rows)
    state.add_step(
        tool="performance_filter",
        params=performance_spec,
        sparql=performance_sparql,
        results=performance_rows,
        inference_used=False,
        reasoning="Deterministic performance filter query.",
    )

    model_iris = sorted({row.get("model_name") for row in performance_rows if row.get("model_name")})
    process_iris = sorted({row.get("ml_process") for row in performance_rows if row.get("ml_process")})
    state.set_artifact("matching_models", model_iris)
    enrichment_plan = plan_performance_enrichment_steps(question)
    for plan_step in enrichment_plan:
        state.add_plan_step(tool=plan_step["tool"], params=plan_step.get("params"), reasoning=plan_step.get("reasoning"))

    # Keep one row per (model, process, metric, value) — do NOT collapse to one row per model
    combined_results = list(performance_rows)
    sparql_parts = [f"-- Step 1: performance filter\n{performance_sparql}"]

    for index, plan_step in enumerate(enrichment_plan, start=2):
        tool = plan_step["tool"]
        if not process_iris:
            break

        if tool == "find_test_datasets_for_models":
            dataset_kind = plan_step.get("params", {}).get("dataset_kind", "test")
            step_sparql = build_model_dataset_query(process_iris, dataset_kind=dataset_kind)
            step_rows = await graphdb_client.query(step_sparql, repo=resolved_repo, use_inference=False)
            state.add_step(
                tool=tool,
                params={"process_iris": process_iris, "dataset_kind": dataset_kind},
                sparql=step_sparql,
                results=step_rows,
                inference_used=False,
                reasoning=plan_step.get("reasoning"),
            )
            combined_results = merge_model_dataset_rows(combined_results, step_rows)
            sparql_parts.append(f"-- Step {index}: model {dataset_kind} datasets\n{step_sparql}")
            continue

        if tool == "find_pipelines_for_models":
            step_sparql = build_model_pipeline_query(model_iris)
            step_rows = await graphdb_client.query(step_sparql, repo=resolved_repo, use_inference=False)
            state.add_step(
                tool=tool,
                params={"model_iris": model_iris},
                sparql=step_sparql,
                results=step_rows,
                inference_used=False,
                reasoning=plan_step.get("reasoning"),
            )
            combined_results = merge_model_pipeline_rows(combined_results, step_rows)
            sparql_parts.append(f"-- Step {index}: model pipelines\n{step_sparql}")

    state.set_artifact("merged_rows", combined_results)
    return payload_type(
        sparql="\n\n".join(sparql_parts),
        results=combined_results,
        inference_used=False,
        state=state,
    )
