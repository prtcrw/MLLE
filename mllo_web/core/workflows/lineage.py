from __future__ import annotations

import re
from typing import Any


def current_question_text(question: str) -> str:
    marker = "Current user question:"
    if marker not in question:
        return question
    tail = question.rsplit(marker, 1)[-1].strip()
    lines = [line.strip() for line in tail.splitlines() if line.strip()]
    return lines[0] if lines else question


def lineage_query_spec(question: str) -> dict[str, Any] | None:
    focused = current_question_text(question)
    lowered = focused.lower()
    lineage_tokens = (
        "used to make",
        "used to create",
        "create ",
        "made from",
        "derived from",
        "source of",
        "raw dataset",
        "raw data set",
        "upstream",
        "downstream",
        "lineage",
        "provenance",
        "trace",
    )
    if not any(token in lowered for token in lineage_tokens):
        return None

    artifact_iri_match = re.search(r"https?://\S+", focused)
    artifact_name = artifact_iri_match.group(0).rstrip(".,)") if artifact_iri_match else ""
    if not artifact_name:
        anchored_patterns = [
            r"(?:used to make|used to create|made from|source of|upstream of|downstream of|lineage of|provenance of)\s+([A-Za-z][A-Za-z0-9_:-]+)",
            r"(?:for|from)\s+([A-Za-z][A-Za-z0-9_:-]+)$",
        ]
        for pattern in anchored_patterns:
            match = re.search(pattern, focused, re.IGNORECASE)
            if match:
                artifact_name = match.group(1)
                break
    if not artifact_name:
        candidates = re.findall(r"\b[A-Z][A-Za-z0-9_:-]*\d+\b|\b[A-Z][A-Za-z0-9_:-]{3,}\b", focused)
        if candidates:
            artifact_name = candidates[-1]
    if not artifact_name:
        return None

    direction = "downstream" if any(token in lowered for token in ("downstream", "produced from", "generated from")) else "upstream"
    target_kind = "raw_dataset" if "raw dataset" in lowered or "raw data set" in lowered else None
    return {"artifact_name": artifact_name, "direction": direction, "target_kind": target_kind, "max_hops": 10}


def question_requests_model_context(question: str) -> bool:
    lowered = question.lower()
    return "model" in lowered or "models" in lowered


def build_dataset_model_query(dataset_iris: list[str], *, dataset_kind: str = "any") -> str:
    escaped_datasets = " ".join(f"<{dataset}>" for dataset in dataset_iris if dataset)
    if dataset_kind == "test":
        dataset_filter = """
    ?dataset rdf:type ?dataset_type .
    ?dataset_type rdfs:subClassOf* ml:TestDataSet .
    OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
"""
    elif dataset_kind == "machine_learning":
        dataset_filter = """
    ?dataset rdf:type ?dataset_type .
    ?dataset_type rdfs:subClassOf* ml:MachineLearningDataSet .
    OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
"""
    else:
        dataset_filter = """
    OPTIONAL {
        ?dataset rdf:type ?dataset_type .
        OPTIONAL { ?dataset_type rdfs:label ?dataset_role }
    }
"""
    return f"""
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?dataset ?dataset_role ?model_name WHERE {{
    VALUES ?dataset {{ {escaped_datasets} }}
    ?ml_process ml:hasDataInput ?dataset .
    ?ml_process (ml:executed | bfo:BFO_0000057) ?model_name .
    ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    {dataset_filter}
}}
LIMIT 200
"""


def build_artifact_resolution_query(artifact_name: str) -> str:
    safe = artifact_name.replace('"', '\\"')
    return f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?node ?label ?type ?type_label WHERE {{
  {{
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    FILTER(LCASE(STR(?label)) = LCASE("{safe}"))
  }} UNION {{
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("{safe}"))
    BIND(STRAFTER(STR(?node), "#") AS ?label)
  }}
  OPTIONAL {{
    ?node rdf:type ?type .
    FILTER(!isBlank(?type))
    OPTIONAL {{ ?type rdfs:label ?type_label }}
  }}
  FILTER(!isBlank(?node))
}}
LIMIT 50
"""


def choose_resolved_artifact(rows: list[dict[str, Any]], artifact_name: str) -> dict[str, Any] | None:
    if not rows:
        return None
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        node = row.get("node")
        if not node:
            continue
        entry = grouped.setdefault(node, {"node": node, "label": row.get("label") or artifact_name, "types": set(), "type_labels": set()})
        if row.get("type"):
            entry["types"].add(row["type"])
        if row.get("type_label"):
            entry["type_labels"].add(row["type_label"])
    if not grouped:
        return None
    ranked = sorted(
        grouped.values(),
        key=lambda item: (
            0 if any("dataset" in label.lower() or "data set" in label.lower() for label in item["type_labels"]) else 1,
            0 if any("https://spec.industrialontologies.org/ontology/construct/" in type_iri for type_iri in item["types"]) else 1,
            item["label"],
        ),
    )
    winner = ranked[0]
    return {"node": winner["node"], "label": winner["label"], "types": sorted(winner["types"]), "type_labels": sorted(winner["type_labels"])}


def build_lineage_step_query(dataset_iris: list[str], *, direction: str) -> str:
    escaped = " ".join(f"<{iri}>" for iri in dataset_iris if iri)
    if direction == "downstream":
        return f"""
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {{
  VALUES ?current_dataset {{ {escaped} }}
  ?process ml:hasDataInput ?current_dataset .
  ?process ml:hasDataOutput ?neighbor_dataset .
  OPTIONAL {{
    ?process rdf:type ?process_type .
    OPTIONAL {{ ?process_type rdfs:label ?process_type_label }}
  }}
  OPTIONAL {{
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL {{ ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }}
  }}
}}
LIMIT 500
"""
    return f"""
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?current_dataset ?process ?process_type_label ?neighbor_dataset ?neighbor_dataset_type_label WHERE {{
  VALUES ?current_dataset {{ {escaped} }}
  ?process ml:hasDataOutput ?current_dataset .
  ?process ml:hasDataInput ?neighbor_dataset .
  OPTIONAL {{
    ?process rdf:type ?process_type .
    OPTIONAL {{ ?process_type rdfs:label ?process_type_label }}
  }}
  OPTIONAL {{
    ?neighbor_dataset rdf:type ?neighbor_dataset_type .
    OPTIONAL {{ ?neighbor_dataset_type rdfs:label ?neighbor_dataset_type_label }}
  }}
}}
LIMIT 500
"""


def dedupe_lineage_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (
            row.get("current_dataset"),
            row.get("process"),
            row.get("neighbor_dataset"),
            row.get("neighbor_dataset_type_label"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def merge_lineage_results(*, current_rows: list[dict[str, Any]], step_rows: list[dict[str, Any]], direction: str) -> list[dict[str, Any]]:
    neighbors_by_current: dict[str, list[dict[str, Any]]] = {}
    for row in step_rows:
        current_dataset = row.get("current_dataset")
        if not current_dataset:
            continue
        bucket = neighbors_by_current.setdefault(current_dataset, [])
        candidate = {
            "process": row.get("process"),
            "process_type": row.get("process_type_label"),
            "neighbor_dataset": row.get("neighbor_dataset"),
            "neighbor_dataset_type": row.get("neighbor_dataset_type_label"),
        }
        if candidate not in bucket:
            bucket.append(candidate)
    merged: list[dict[str, Any]] = []
    for row in current_rows:
        current_dataset = row.get("dataset") or row.get("neighbor_dataset") or row.get("artifact")
        candidates = neighbors_by_current.get(current_dataset, [])
        if not candidates:
            merged.append(row)
            continue
        for candidate in candidates:
            merged.append(
                {
                    **row,
                    ("upstream_process" if direction == "upstream" else "downstream_process"): candidate["process"],
                    ("upstream_process_type" if direction == "upstream" else "downstream_process_type"): candidate["process_type"],
                    ("upstream_dataset" if direction == "upstream" else "downstream_dataset"): candidate["neighbor_dataset"],
                    ("upstream_dataset_type" if direction == "upstream" else "downstream_dataset_type"): candidate["neighbor_dataset_type"],
                }
            )
    return merged


def merge_lineage_model_rows(lineage_rows: list[dict[str, Any]], model_rows: list[dict[str, Any]], *, direction: str) -> list[dict[str, Any]]:
    dataset_key = "upstream_dataset" if direction == "upstream" else "downstream_dataset"
    models_by_dataset: dict[str, list[dict[str, Any]]] = {}
    for row in model_rows:
        dataset = row.get("dataset")
        model_name = row.get("model_name")
        if not dataset or not model_name:
            continue
        bucket = models_by_dataset.setdefault(dataset, [])
        candidate = {"model_name": model_name, "dataset_role": row.get("dataset_role")}
        if candidate not in bucket:
            bucket.append(candidate)
    merged: list[dict[str, Any]] = []
    for row in lineage_rows:
        dataset = row.get(dataset_key)
        candidates = models_by_dataset.get(dataset or "", [])
        if not candidates:
            merged.append(row)
            continue
        for candidate in candidates:
            merged.append({**row, "model_name": candidate["model_name"], "model_dataset_role": candidate["dataset_role"]})
    return merged


def plan_lineage_enrichment_steps(question: str, *, direction: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if direction == "downstream" and question_requests_model_context(question):
        steps.append(
            {
                "tool": "find_models_for_lineage_datasets",
                "params": {"dataset_kind": "any"},
                "reasoning": "The question asks which models use the traced downstream datasets.",
            }
        )
    return steps


async def execute_lineage_orchestration(
    *,
    question: str,
    resolved_repo: str,
    state,
    graphdb_client,
    payload_type,
):
    spec = lineage_query_spec(question)
    if not spec:
        raise ValueError("Lineage orchestration requires a lineage query spec.")

    resolution_sparql = build_artifact_resolution_query(spec["artifact_name"])
    resolution_rows = await graphdb_client.query(resolution_sparql, repo=resolved_repo, use_inference=False)
    state.add_plan_step(tool="resolve_artifact", params={"artifact_name": spec["artifact_name"]}, reasoning="Resolve the named artifact to a graph node before tracing lineage.")
    state.add_step(tool="resolve_artifact", params={"artifact_name": spec["artifact_name"]}, sparql=resolution_sparql, results=resolution_rows, inference_used=False, reasoning="Resolve the named artifact to a graph node before tracing lineage.")
    resolved_artifact = choose_resolved_artifact(resolution_rows, spec["artifact_name"])
    if not resolved_artifact:
        return payload_type(sparql=resolution_sparql, results=[], inference_used=False, state=state)

    state.set_artifact("resolved_artifact", resolved_artifact)
    direction = spec["direction"]
    max_hops = int(spec.get("max_hops", 10))
    target_kind = spec.get("target_kind")

    current_frontier = [resolved_artifact["node"]]
    lineage_rows: list[dict[str, Any]] = [{"artifact": resolved_artifact["node"], "artifact_label": resolved_artifact["label"], "artifact_types": resolved_artifact.get("type_labels", [])}]
    sparql_parts = [f"-- Step 1: resolve artifact\n{resolution_sparql}"]

    for hop in range(1, max_hops + 1):
        if not current_frontier:
            break
        step_reasoning = f"Trace {direction} one hop through MLLO data-input/data-output process links."
        state.add_plan_step(tool="trace_lineage_step", params={"direction": direction, "hop": hop, "frontier": current_frontier}, reasoning=step_reasoning)
        step_sparql = build_lineage_step_query(current_frontier, direction=direction)
        step_rows = dedupe_lineage_rows(await graphdb_client.query(step_sparql, repo=resolved_repo, use_inference=False))
        state.add_step(tool="trace_lineage_step", params={"direction": direction, "hop": hop, "frontier": current_frontier}, sparql=step_sparql, results=step_rows, inference_used=False, reasoning=step_reasoning)
        sparql_parts.append(f"-- Step {hop + 1}: lineage hop {hop}\n{step_sparql}")
        lineage_rows = merge_lineage_results(current_rows=lineage_rows, step_rows=step_rows, direction=direction)

        next_frontier = [row.get("neighbor_dataset") for row in step_rows if row.get("neighbor_dataset")]
        if target_kind == "raw_dataset":
            matching = [
                row for row in lineage_rows
                if "raw data set" in str(row.get("upstream_dataset_type", "")).lower()
                or "raw data set" in str(row.get("downstream_dataset_type", "")).lower()
            ]
            if matching:
                lineage_rows = matching
                break
        current_frontier = sorted(set(next_frontier))

    enrichment_plan = plan_lineage_enrichment_steps(question, direction=direction)
    for plan_step in enrichment_plan:
        state.add_plan_step(tool=plan_step["tool"], params=plan_step.get("params"), reasoning=plan_step.get("reasoning"))

    for index, plan_step in enumerate(enrichment_plan, start=len(state.steps) + 1):
        if plan_step["tool"] != "find_models_for_lineage_datasets":
            continue
        dataset_key = "upstream_dataset" if direction == "upstream" else "downstream_dataset"
        lineage_datasets = sorted({row.get(dataset_key) for row in lineage_rows if row.get(dataset_key)})
        if not lineage_datasets:
            continue
        dataset_kind = plan_step.get("params", {}).get("dataset_kind", "any")
        step_sparql = build_dataset_model_query(lineage_datasets, dataset_kind=dataset_kind)
        step_rows = await graphdb_client.query(step_sparql, repo=resolved_repo, use_inference=False)
        state.add_step(tool=plan_step["tool"], params={"datasets": lineage_datasets, "dataset_kind": dataset_kind}, sparql=step_sparql, results=step_rows, inference_used=False, reasoning=plan_step.get("reasoning"))
        sparql_parts.append(f"-- Step {index}: models for traced datasets\n{step_sparql}")
        lineage_rows = merge_lineage_model_rows(lineage_rows, step_rows, direction=direction)

    state.set_artifact("merged_rows", lineage_rows)
    return payload_type(sparql="\n\n".join(sparql_parts), results=lineage_rows, inference_used=False, state=state)
