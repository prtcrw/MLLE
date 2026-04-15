from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, Query, Request
from pydantic import BaseModel, Field

from mllo_web.app.api.config import get_config
from mllo_web.app.api.services.settings_model import get_app_data_dir

config = get_config()
EXPLICIT_GRAPH = "FROM <http://www.ontotext.com/explicit>"


class PipelineEditorNode(BaseModel):
    id: str
    iri: str
    title: str
    kind: Literal["input", "operation", "output", "model"]
    position: int
    note: str = ""
    x: float | None = None
    y: float | None = None


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


class PipelineEditorNodeMetadata(BaseModel):
    summary: str
    rules: list[str] = Field(default_factory=list)
    observed_structure: list[str] = Field(default_factory=list)
    ontology_classes: list[str] = Field(default_factory=list)
    ontology_relations: list[str] = Field(default_factory=list)
    impact: str


class PipelineEditorState(BaseModel):
    draft: PipelineEditorDraft | None = None
    source_draft: PipelineEditorDraft | None = None
    source_metadata: dict[str, PipelineEditorNodeMetadata] = Field(default_factory=dict)
    history: list[PipelineEditorVersion] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    ok: bool
    validation_status: Literal["passed", "failed"]
    validation_message: str
    violations: list[str] = Field(default_factory=list)


def _build_existing_pipelines_query(search_term: str | None = None) -> str:
    filter_clause = ""
    if search_term:
        safe = search_term.replace('"', '\\"')
        filter_clause = f'FILTER(CONTAINS(LCASE(STRAFTER(STR(?pipeline), "#")), LCASE("{safe}")))'
    query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
SELECT DISTINCT (STRAFTER(STR(?pipeline), "#") AS ?pipeline_name)
WHERE {{
  ?pipeline rdf:type ?pipelineType .
  {{
    ?pipelineType rdfs:subClassOf+ ml:DataProcessingPipeline .
  }} UNION {{
    VALUES ?pipelineType {{ ml:MachineLearningModelDevelopmentPipeline }}
  }}
  {filter_clause}
}}
ORDER BY ?pipeline_name
LIMIT 100
"""
    if config.sparql_backend == "graphdb":
        query = _inject_explicit_graph(query)
    return query


VALIDATION_EXPECTATIONS: dict[str, list[str]] = {
    "DataReshapingOperation": ["FeatureScalingOperation"],
    "FeatureScalingOperation": ["TypeCastingOperation"],
    "TypeCastingOperation": ["PreprocessedDataset"],
    "PreprocessedDataset": ["MLModel"],
}

MLLO_NAMESPACE = "http://www.semanticweb.org/mnd14/ml/"
RELATION_LABEL_FALLBACKS = {
    "http://purl.obolibrary.org/obo/BFO_0000117": "has pipeline component",
    "http://purl.obolibrary.org/obo/BFO_0000063": "has predecessor relation",
    "http://purl.obolibrary.org/obo/BFO_0000057": "has participant",
    "http://www.semanticweb.org/mnd14/ml/hasDataInput": "has data input",
    "http://www.semanticweb.org/mnd14/ml/hasDataOutput": "has data output",
    "http://www.semanticweb.org/mnd14/ml/executes": "executes",
}


def _inject_explicit_graph(query: str) -> str:
    if EXPLICIT_GRAPH in query:
        return query
    return re.sub(
        r"(?is)(SELECT\b.*?)(\bWHERE\s*\{)",
        rf"\1\n{EXPLICIT_GRAPH}\n\2",
        query,
        count=1,
    )


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


def _local_name(value: str) -> str:
    if "#" in value:
        return value.rsplit("#", 1)[-1]
    return value.rstrip("/").rsplit("/", 1)[-1]


def _title_from_local_name(value: str) -> str:
    local_name = _local_name(value)
    tokens = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", local_name).replace("_", " ").strip()
    return tokens or local_name


def _label_or_local_name(value: str | None) -> str:
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return _title_from_local_name(value)
    return value


def _relation_label(relation_iri: str) -> str:
    return RELATION_LABEL_FALLBACKS.get(relation_iri, _label_or_local_name(relation_iri))


def _build_graph_query(pipeline_name: str) -> str:
    query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX ann: <https://spec.industrialontologies.org/ontology/core/meta/AnnotationVocabulary/>
SELECT DISTINCT ?pipeline ?resource ?resourceType ?resourceTypeLabel ?resourceTypeDefinition ?input ?inputType ?inputTypeDefinition ?output ?outputType ?outputTypeDefinition ?model ?modelType ?modelTypeDefinition ?predecessor
WHERE {{
  ?pipeline rdf:type ?pipelineType .
  FILTER(STRAFTER(STR(?pipeline), "#") = "{pipeline_name}")
  OPTIONAL {{
    ?pipeline ml:hasDataInput ?input .
    OPTIONAL {{
      ?input rdf:type ?inputType .
      FILTER(!isBlank(?inputType))
      OPTIONAL {{ ?inputType ann:naturalLanguageDefinition ?inputTypeDefinition }}
    }}
  }}
  OPTIONAL {{
    ?pipeline ml:hasDataOutput ?output .
    OPTIONAL {{
      ?output rdf:type ?outputType .
      FILTER(!isBlank(?outputType))
      OPTIONAL {{ ?outputType ann:naturalLanguageDefinition ?outputTypeDefinition }}
    }}
  }}
  OPTIONAL {{
    {{
      ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model
    }} UNION {{
      ?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?model
    }}
    ?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
    OPTIONAL {{
      ?model rdf:type ?modelType .
      FILTER(!isBlank(?modelType))
      OPTIONAL {{ ?modelType ann:naturalLanguageDefinition ?modelTypeDefinition }}
    }}
  }}
  OPTIONAL {{
    ?pipeline bfo:BFO_0000117 ?resource .
    ?resource rdf:type ?resourceType .
    FILTER(!isBlank(?resourceType))
    FILTER EXISTS {{ ?resourceType rdfs:subClassOf+ iof-core:PlannedProcess }}
    OPTIONAL {{ ?resourceType rdfs:label ?resourceTypeLabel }}
    OPTIONAL {{ ?resourceType ann:naturalLanguageDefinition ?resourceTypeDefinition }}
    OPTIONAL {{
      ?resource bfo:BFO_0000063 ?predecessor .
      ?pipeline bfo:BFO_0000117 ?predecessor .
    }}
  }}
}}
"""
    if config.sparql_backend == "graphdb":
        query = _inject_explicit_graph(query)
    return query


def _pick_preferred_definition(definitions: set[str]) -> str | None:
    if not definitions:
        return None
    ordered = sorted(definitions, key=lambda value: (len(value), value))
    return ordered[0]


def _pick_preferred_type(type_iris: set[str]) -> str | None:
    if not type_iris:
        return None
    mllo_types = sorted([value for value in type_iris if value.startswith(MLLO_NAMESPACE)])
    if mllo_types:
        return mllo_types[0]
    return sorted(type_iris)[0]


def _node_matches(node: PipelineEditorNode, token: str) -> bool:
    haystack = f"{node.id} {node.title} {node.iri}".lower()
    return token.lower() in haystack


def _build_axiom_query(class_iris: list[str]) -> str:
    values = " ".join(f"<{iri}>" for iri in class_iris)
    query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?class ?restrictionProperty ?restrictionPropertyLabel ?restrictionTarget ?restrictionTargetLabel ?disjointClass ?disjointLabel
WHERE {{
  VALUES ?class {{ {values} }}
  OPTIONAL {{
    ?class rdfs:subClassOf ?restriction .
    ?restriction a owl:Restriction ;
      owl:onProperty ?restrictionProperty ;
      (owl:someValuesFrom|owl:allValuesFrom|owl:onClass) ?restrictionTarget .
    OPTIONAL {{ ?restrictionProperty rdfs:label ?restrictionPropertyLabel }}
    OPTIONAL {{ ?restrictionTarget rdfs:label ?restrictionTargetLabel }}
    FILTER(!isBlank(?restrictionTarget))
  }}
  OPTIONAL {{
    {{ ?class owl:disjointWith ?disjointClass }} UNION {{ ?disjointClass owl:disjointWith ?class }}
    OPTIONAL {{ ?disjointClass rdfs:label ?disjointLabel }}
    FILTER(!isBlank(?disjointClass))
  }}
}}
"""
    if config.sparql_backend == "graphdb":
        query = _inject_explicit_graph(query)
    return query


def _load_axiom_rules(request: Request, class_iris: list[str]) -> dict[str, list[str]]:
    if not class_iris:
        return {}

    rows = request.app.sparql_client.query(_build_axiom_query(class_iris))
    rules_by_class: dict[str, set[str]] = {class_iri: set() for class_iri in class_iris}

    for row in rows:
        class_iri = row.get("class")
        if not class_iri:
            continue
        restriction_property = row.get("restrictionProperty")
        restriction_target = row.get("restrictionTarget")
        disjoint_class = row.get("disjointClass")

        if restriction_property and restriction_target:
            property_label = _label_or_local_name(row.get("restrictionPropertyLabel") or restriction_property)
            target_label = _label_or_local_name(row.get("restrictionTargetLabel") or restriction_target)
            rules_by_class.setdefault(class_iri, set()).add(
                f"Ontology restriction: {property_label} some {target_label}."
            )

        if disjoint_class:
            disjoint_label = _label_or_local_name(row.get("disjointLabel") or disjoint_class)
            rules_by_class.setdefault(class_iri, set()).add(
                f"Must not be classified together with {disjoint_label}."
            )

    return {class_iri: sorted(values) for class_iri, values in rules_by_class.items()}


def _validate_draft(draft: PipelineEditorDraft) -> list[str]:
    ordered_nodes = sorted(draft.nodes, key=lambda item: item.position)
    violations: list[str] = []
    kinds_present = {node.kind for node in ordered_nodes}

    if "input" not in kinds_present:
        violations.append("Pipeline draft must include an input dataset node.")
    if "output" not in kinds_present:
        violations.append("Pipeline draft must include an output dataset node.")
    if "model" not in kinds_present:
        violations.append("Pipeline draft must include an associated model node.")

    for source_token, target_tokens in VALIDATION_EXPECTATIONS.items():
        source_node = next((node for node in ordered_nodes if _node_matches(node, source_token)), None)
        if not source_node:
            continue
        for target_token in target_tokens:
            target_node = next((node for node in ordered_nodes if _node_matches(node, target_token)), None)
            if not target_node:
                continue
            if source_node.position >= target_node.position:
                violations.append(f"{source_node.title} must appear before {target_node.title}.")

    return violations


def _build_source_draft(request: Request, pipeline_name: str) -> tuple[PipelineEditorDraft | None, dict[str, str]]:
    rows = request.app.sparql_client.query(_build_graph_query(pipeline_name))
    if not rows:
        return None, {}

    input_iri = next((row["input"] for row in rows if row.get("input")), None)
    output_iri = next((row["output"] for row in rows if row.get("output")), None)
    model_iri = next((row["model"] for row in rows if row.get("model")), None)

    resources: dict[str, dict[str, set[str]]] = {}
    predecessors: dict[str, set[str]] = {}
    input_definitions: set[str] = set()
    output_definitions: set[str] = set()
    model_definitions: set[str] = set()
    input_types: set[str] = set()
    output_types: set[str] = set()
    model_types: set[str] = set()
    for row in rows:
        resource = row.get("resource")
        resource_type = row.get("resourceType")
        resource_type_label = row.get("resourceTypeLabel")
        resource_type_definition = row.get("resourceTypeDefinition")
        predecessor = row.get("predecessor")
        if row.get("inputTypeDefinition"):
            input_definitions.add(row["inputTypeDefinition"])
        if row.get("inputType"):
            input_types.add(row["inputType"])
        if row.get("outputTypeDefinition"):
            output_definitions.add(row["outputTypeDefinition"])
        if row.get("outputType"):
            output_types.add(row["outputType"])
        if row.get("modelTypeDefinition"):
            model_definitions.add(row["modelTypeDefinition"])
        if row.get("modelType"):
            model_types.add(row["modelType"])
        if not resource:
            continue
        resources.setdefault(resource, {"types": set(), "labels": set(), "definitions": set()})
        predecessors.setdefault(resource, set())
        if resource_type:
            resources[resource]["types"].add(resource_type)
        if resource_type_label:
            resources[resource]["labels"].add(resource_type_label)
        if resource_type_definition:
            resources[resource]["definitions"].add(resource_type_definition)
        if predecessor:
            predecessors[resource].add(predecessor)

    ordered_resources: list[str] = []
    remaining = set(resources.keys())
    while remaining:
        ready = sorted(
            [resource for resource in remaining if predecessors.get(resource, set()).isdisjoint(remaining)],
            key=_local_name,
        )
        if not ready:
            ready = sorted(remaining, key=_local_name)
        ordered_resources.extend(ready)
        for resource in ready:
            remaining.remove(resource)

    nodes: list[PipelineEditorNode] = []
    node_class_map: dict[str, str] = {}
    position = 0

    def _default_coordinates(index: int) -> tuple[int, int]:
        return 40 + (index * 240), 80

    if input_iri:
        input_id = _local_name(input_iri)
        x, y = _default_coordinates(position)
        nodes.append(
            PipelineEditorNode(
                id=input_id,
                iri=input_iri,
                title=_title_from_local_name(input_iri),
                kind="input",
                position=position,
                note=_pick_preferred_definition(input_definitions) or "Loaded from GraphDB pipeline input.",
                x=x,
                y=y,
            )
        )
        preferred_input_type = _pick_preferred_type(input_types)
        if preferred_input_type:
            node_class_map[input_id] = preferred_input_type
        position += 1

    for resource in ordered_resources:
        resource_definition = _pick_preferred_definition(resources[resource]["definitions"])
        resource_id = _local_name(resource)
        x, y = _default_coordinates(position)
        nodes.append(
            PipelineEditorNode(
                id=resource_id,
                iri=resource,
                title=_title_from_local_name(resource),
                kind="operation",
                position=position,
                note=resource_definition or f"Loaded from {pipeline_name} component membership in GraphDB.",
                x=x,
                y=y,
            )
        )
        preferred_resource_type = _pick_preferred_type(resources[resource]["types"])
        if preferred_resource_type:
            node_class_map[resource_id] = preferred_resource_type
        position += 1

    if output_iri:
        output_id = _local_name(output_iri)
        x, y = _default_coordinates(position)
        nodes.append(
            PipelineEditorNode(
                id=output_id,
                iri=output_iri,
                title=_title_from_local_name(output_iri),
                kind="output",
                position=position,
                note=_pick_preferred_definition(output_definitions) or "Loaded from GraphDB pipeline output.",
                x=x,
                y=y,
            )
        )
        preferred_output_type = _pick_preferred_type(output_types)
        if preferred_output_type:
            node_class_map[output_id] = preferred_output_type
        position += 1

    if model_iri:
        model_id = _local_name(model_iri)
        x, y = _default_coordinates(position)
        nodes.append(
            PipelineEditorNode(
                id=model_id,
                iri=model_iri,
                title=_title_from_local_name(model_iri),
                kind="model",
                position=position,
                note=_pick_preferred_definition(model_definitions) or "Loaded from GraphDB associated model path.",
                x=x,
                y=y,
            )
        )
        preferred_model_type = _pick_preferred_type(model_types)
        if preferred_model_type:
            node_class_map[model_id] = preferred_model_type

    edges = [
        PipelineEditorEdge(
            source=node.id,
            target=nodes[index + 1].id,
            relation="isStructurallyFollowedBy",
        )
        for index, node in enumerate(nodes[:-1])
    ]

    return PipelineEditorDraft(
        pipelineName=pipeline_name,
        savedAt=datetime.now(UTC).isoformat(),
        validationStatus="unknown",
        validationMessage="Loaded from GraphDB. Run consistency checks before publishing.",
        nodes=nodes,
        edges=edges,
    ), node_class_map


def _build_source_metadata(
    request: Request,
    source_draft: PipelineEditorDraft | None,
    node_class_map: dict[str, str],
) -> dict[str, PipelineEditorNodeMetadata]:
    if source_draft is None:
        return {}

    ordered_nodes = sorted(source_draft.nodes, key=lambda item: item.position)
    axiom_rules = _load_axiom_rules(request, sorted(set(node_class_map.values())))
    metadata: dict[str, PipelineEditorNodeMetadata] = {}

    for index, node in enumerate(ordered_nodes):
        previous_node = ordered_nodes[index - 1] if index > 0 else None
        next_node = ordered_nodes[index + 1] if index < len(ordered_nodes) - 1 else None

        observed_structure: list[str] = []
        if previous_node is None:
            observed_structure.append("Observed as the first node in the current pipeline graph.")
        else:
            observed_structure.append(f"Observed after {previous_node.title} in the current workflow order.")
        if next_node is not None:
            observed_structure.append(f"Observed before {next_node.title} through the pipeline chain.")

        ontology_relations: list[str] = []
        if node.kind == "input":
            ontology_relations.append(f"Mapped through {_relation_label('http://www.semanticweb.org/mnd14/ml/hasDataInput')} from the pipeline instance.")
        elif node.kind == "output":
            ontology_relations.append(f"Mapped through {_relation_label('http://www.semanticweb.org/mnd14/ml/hasDataOutput')} from the pipeline instance.")
        elif node.kind == "operation":
            ontology_relations.append(f"Mapped as a pipeline component through {_relation_label('http://purl.obolibrary.org/obo/BFO_0000117')}.")
            if previous_node is not None:
                ontology_relations.append(f"Mapped to predecessor/successor ordering through {_relation_label('http://purl.obolibrary.org/obo/BFO_0000063')}.")
        elif node.kind == "model":
            ontology_relations.append(
                f"Mapped through the model execution path using {_relation_label('http://www.semanticweb.org/mnd14/ml/executes')} and {_relation_label('http://purl.obolibrary.org/obo/BFO_0000057')}."
            )

        class_iri = node_class_map.get(node.id)
        ontology_classes: list[str] = []
        rules: list[str] = []
        if class_iri:
            ontology_classes.append(_title_from_local_name(class_iri))
            rules.extend(axiom_rules.get(class_iri, []))
        deduped_rules = list(dict.fromkeys(rules))
        deduped_structure = list(dict.fromkeys(observed_structure))
        deduped_relations = list(dict.fromkeys(ontology_relations))

        impact_parts = []
        if next_node is not None:
            impact_parts.append(f"Changes here affect downstream node {next_node.title}.")
        else:
            impact_parts.append("Changes here affect the terminal stage of the pipeline.")
        if previous_node is not None:
            impact_parts.append(f"It also depends on upstream context from {previous_node.title}.")
        if node.kind == "model":
            impact_parts.append("Model updates influence evaluation, deployment, and comparison outcomes.")
        elif node.kind == "output":
            impact_parts.append("Output updates influence lineage, reproducibility, and model handoff.")
        elif node.kind == "input":
            impact_parts.append("Input updates propagate through the full downstream workflow.")
        else:
            impact_parts.append("Operation updates can change validation and export behavior for later steps.")

        metadata[node.id] = PipelineEditorNodeMetadata(
            summary=node.note or f"Loaded from {source_draft.pipelineName}.",
            rules=deduped_rules,
            observed_structure=deduped_structure,
            ontology_classes=ontology_classes,
            ontology_relations=deduped_relations,
            impact=" ".join(impact_parts),
        )

    return metadata


async def get_draft(request: Request, pipeline_name: str = Query(..., alias="pipeline_name")) -> PipelineEditorState:
    draft_path = _draft_path(pipeline_name)
    draft = None
    if draft_path.exists():
        raw = json.loads(draft_path.read_text(encoding="utf-8"))
        draft = PipelineEditorDraft.model_validate(raw)
    history = _load_history(pipeline_name)
    source_draft, node_class_map = _build_source_draft(request, pipeline_name)
    return PipelineEditorState(
        draft=draft,
        source_draft=source_draft,
        source_metadata=_build_source_metadata(request, source_draft, node_class_map),
        history=history,
    )


async def get_existing_pipelines(request: Request, search_term: str | None = Query(default=None, alias="search_term")) -> dict:
    rows = request.app.sparql_client.query(_build_existing_pipelines_query(search_term))
    return {"pipelines": [row["pipeline_name"] for row in rows if row.get("pipeline_name")]}


async def delete_draft(pipeline_name: str = Query(..., alias="pipeline_name")) -> dict:
    draft_path = _draft_path(pipeline_name)
    if draft_path.exists():
        draft_path.unlink()
    return {"ok": True}


async def save_draft(draft: PipelineEditorDraft) -> PipelineEditorState:
    draft_path = _draft_path(draft.pipelineName)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(
        json.dumps(draft.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    history = _load_history(draft.pipelineName)
    return PipelineEditorState(draft=draft, source_draft=None, source_metadata={}, history=history)


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

    published_draft = {
        **draft.model_dump(mode="json"),
        "validationStatus": "passed",
        "validationMessage": "Published after backend validation.",
    }
    version_payload = {
        "publishedAt": published_at,
        "draft": published_draft,
        "version": version_record.model_dump(mode="json"),
    }
    version_file = versions_dir / f"{version_name.replace('.', '_')}_{published_at.replace(':', '-')}.json"
    version_file.write_text(json.dumps(version_payload, indent=2), encoding="utf-8")

    _draft_path(draft.pipelineName).write_text(json.dumps(published_draft, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "published_at": published_at,
        "version": version_record,
        "draft": published_draft,
        "history": history,
    }


async def get_history(pipeline_name: str = Query(..., alias="pipeline_name")) -> dict:
    return {"history": _load_history(pipeline_name)}
