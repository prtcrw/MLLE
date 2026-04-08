from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mllo_web.app.api.routers.find_datasets import FindDatasetsQueryBuilder
from mllo_web.app.api.routers.find_models import DeployedModelsQueryBuilder, FindModelsQueryBuilder
from mllo_web.app.api.routers.find_pipelines import FindPipelinesQueryBuilder
from mllo_web.app.api.routers.query_iri import IriQueryBuilder
from mllo_web.app.api.services.graphdb_client import GraphDBClient
from mllo_web.app.api.services.intent_classifier import QueryIntent, classify_intent
from mllo_web.app.api.services.llm_gateway import LLMGateway, LLMServiceError
from mllo_web.app.api.services.query_state import NLQQueryState
from mllo_web.app.api.services.settings_model import MLLESettings, load_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/nlq", tags=["natural-language-query"])

LLM_UNAVAILABLE_USER_MESSAGE = "Can't access AI model."
ONTOLOGY_UNAVAILABLE_USER_MESSAGE = "Can't access ontology data source."

ONTOLOGY_GRAPH = "http://www.semanticweb.org/mnd14/ml/"

ONTOLOGY_SCHEMA_QUERY = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT
    ?type
    ?entity
    ?label
    ?domain
    ?range
WHERE {
    GRAPH ?g {
    {
        ?entity rdf:type owl:Class .
        BIND("Class" AS ?type)
        OPTIONAL { ?entity rdfs:label ?label }
        OPTIONAL { ?entity rdfs:subClassOf ?domain }
    }
    UNION
    {
        ?entity rdf:type owl:ObjectProperty .
        BIND("ObjectProperty" AS ?type)
        OPTIONAL { ?entity rdfs:label ?label }
        OPTIONAL { ?entity rdfs:domain ?domain }
        OPTIONAL { ?entity rdfs:range ?range }
    }
    UNION
    {
        ?entity rdf:type owl:DatatypeProperty .
        BIND("DatatypeProperty" AS ?type)
        OPTIONAL { ?entity rdfs:label ?label }
        OPTIONAL { ?entity rdfs:domain ?domain }
        OPTIONAL { ?entity rdfs:range ?range }
    }
    UNION
    {
        ?entity rdf:type owl:AnnotationProperty .
        BIND("AnnotationProperty" AS ?type)
        OPTIONAL { ?entity rdfs:label ?label }
    }
}
}

ORDER BY ?type ?entity
"""

SAMPLE_TRIPLES_QUERY = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>

SELECT ?s ?p ?o
WHERE {
    ?s ?p ?o .
    FILTER(!isBlank(?s) && !isBlank(?o))
    FILTER(?p != rdf:type && ?p != rdfs:subClassOf && ?p != owl:imports)
}
LIMIT 30
"""

NAMED_INDIVIDUALS_QUERY = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?individual ?label ?type
WHERE {
    ?individual rdf:type ?type .
    FILTER(isIRI(?individual) && isIRI(?type))
    FILTER(
        ?type != owl:Class &&
        ?type != owl:ObjectProperty &&
        ?type != owl:DatatypeProperty &&
        ?type != owl:AnnotationProperty &&
        ?type != owl:Ontology &&
        ?type != owl:NamedIndividual
    )
    OPTIONAL { ?individual rdfs:label ?label }
}
LIMIT 2000
"""

PREFIX_QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
SELECT DISTINCT ?prefix ?namespace
WHERE {
    {
        ?ont a owl:Ontology .
        ?ont sh:declare ?decl .
        ?decl sh:prefix ?prefix .
        ?decl sh:namespace ?namespace .
    }
    UNION
    {
        ?entity rdf:type ?t .
        FILTER(?t IN (owl:Class, owl:ObjectProperty, owl:DatatypeProperty))
        BIND(REPLACE(STR(?entity), "[^/#]*$", "") AS ?namespace)
        BIND("" AS ?prefix)
    }
}
"""

EXAMPLE_QUERIES = """"""
"""
=== EXAMPLE QUERIES ===

-- Example 1: Find all ML models with their type, objective, dataset, and performance --
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT ?model ?model_type ?model_objective ?dataset ?ml_input_timestamp
       ?model_output ?model_output_utilization
       ?model_performance_metric ?model_performance_value
WHERE {
    ?ml_process ml:executes | bfo:BFO_0000057 ?model .
    ?model rdf:type/rdfs:label ?model_type .
    ?model bfo:BFO_0000178 ?model_objective .
    ?model_objective rdf:type/rdfs:label ?objective_type .
    ?ml_process ml:hasDataInput ?dataset .
    ?dataset rdf:type ?dataset_type .
    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
    }
    OPTIONAL {
        ?ml_process ml:hasDataOutput ?model_output .
        OPTIONAL {
            ?utilization_process ml:hasDataInput ?model_output .
            ?utilization_process rdf:type/rdfs:label ?model_output_utilization
        }
    }
    OPTIONAL {
        ?ml_process (ml:hasDataOutput/^ml:hasDataInput)+ ?model_performance_assessment .
        ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
        ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment .
        ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
        ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric .
        ?model_performance_metric_type rdfs:label ?model_performance_metric .
        ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value
    }
}
ORDER BY ?model
LIMIT 100

-- Example 2: Find all pipelines with components and associated models --
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    (STRAFTER(STR(?pipeline), "#") AS ?pipeline_name)
    ?pipeline_type
    ?pipeline_components
    (STRAFTER(STR(?pipeline_data_input_iri), "#") AS ?pipeline_data_input)
    (STRAFTER(STR(?pipeline_data_output_iri), "#") AS ?pipeline_data_output)
    (STRAFTER(STR(?pipeline_associated_model_iri), "#") AS ?pipeline_associated_model)
WHERE {
    {
        SELECT ?pipeline ?pipeline_type
            (GROUP_CONCAT(DISTINCT ?pipeline_component_label; separator=";") AS ?pipeline_components)
        WHERE {
            ?pipeline rdf:type ?pipeline_type_iri .
            ?pipeline_type_iri rdfs:label ?pipeline_type .
            {
                ?pipeline_type_iri rdfs:subClassOf+ ml:DataProcessingPipeline .
            } UNION {
                VALUES ?pipeline_type_iri { ml:MachineLearningModelDevelopmentPipeline }
                ?pipeline rdf:type ?pipeline_type_iri .
            }
            ?pipeline bfo:BFO_0000117 ?pipeline_component .
            ?pipeline_component rdf:type ?pipeline_component_type .
            ?pipeline_component_type rdfs:subClassOf+ iof-core:PlannedProcess .
            ?pipeline_component_type rdfs:label ?pipeline_component_label
        }
        GROUP BY ?pipeline ?pipeline_type
    }
    OPTIONAL { ?pipeline ml:hasDataInput ?pipeline_data_input_iri }
    OPTIONAL { ?pipeline ml:hasDataOutput ?pipeline_data_output_iri }
    OPTIONAL {
        {
            ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        } UNION {
            ?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }
        ?pipeline_associated_model_iri rdf:type/rdfs:subClassOf* ml:MachineLearningModel
    }
}

-- Example 3: Find deployed models with execution details --
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT ?model_name ?model_deployed_on_system
    (MAX(?model_training_timestamp) AS ?last_model_update)
    ?model_execution_timestamp ?model_input ?model_output
WHERE {
    ?deployed_state bfo:BFO_0000167 ?model_name .
    ?deployed_state bfo:BFO_0000167 ?model_deployed_on_system .
    ?model_deployed_on_system rdf:type/rdfs:subClassOf* iof-core:EngineeredSystem .
    ?model_name rdf:type/rdfs:subClassOf+ ml:MachineLearningModel .
    ?deployed_state bfo:BFO_0000117 ?model_execution .
    ?model_execution rdf:type/rdfs:subClassOf* ml:ModelExecution .
    ?model_execution ml:hasDataInput ?model_input .
    ?model_execution ml:hasDataOutput ?model_output .
    ?ml_training ^bfo:BFO_0000117*/bfo:BFO_0000063 ?model_execution .
    ?ml_training rdf:type/rdfs:subClassOf* ml:MachineLearningTraining .
    ?model_execution bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?model_execution_timestamp .
    ?ml_training bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?model_training_timestamp .
}
GROUP BY ?model_name ?model_deployed_on_system ?model_execution_timestamp ?model_input ?model_output

-- Example 4: Find all datasets used in ML processes with their role and model --
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    (STRAFTER(STR(?dataset), "#") AS ?dataset_name)
    ?dataset_used_as
    ?dataset_used_for
    (STRAFTER(STR(?model), "#") AS ?model_name)
    ?ml_input_timestamp
WHERE {
    ?ml_process ml:executes | bfo:BFO_0000057 ?model .
    ?ml_process ml:hasDataInput ?dataset .
    ?dataset rdf:type ?dataset_type .
    ?dataset_type rdfs:label ?dataset_used_as .
    {
        ?ml_process ml:hasDataOutput ?model_output .
        ?utilization_process ml:hasDataInput ?model_output .
        ?utilization_process rdf:type/rdfs:label ?dataset_used_for .
    } UNION {
        ?ml_process rdf:type/rdfs:subClassOf* ml:MachineLearningTraining .
        ?ml_process rdfs:label ?dataset_used_for .
    }
    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
    }
}
ORDER BY ?dataset_name
LIMIT 100
"""

SYSTEM_MESSAGE = (
    "You are an expert Semantic Web engineer specialising in the MLLO (Machine Learning Lifecycle Ontology).\n"
    "Generate ONLY valid SPARQL that strictly follows the provided ontology schema and example queries.\n\n"
    "ENTITY DEFINITIONS in MLLO:\n"
    "- DATASET: an entity used as input to an ML process via ml:hasDataInput.\n"
    "- MODEL: a MachineLearningModel linked from an ML process via ml:executes | bfo:BFO_0000057.\n"
    "- PIPELINE: a DataProcessingPipeline or MachineLearningModelDevelopmentPipeline with components via bfo:BFO_0000117.\n"
    "- ML PROCESS: the central node linking models, datasets, inputs, and outputs.\n\n"
    "KEY PATTERNS:\n"
    "- ML processes link to models via: ml:executes | bfo:BFO_0000057\n"
    "- ML processes link to datasets via: ml:hasDataInput / ml:hasDataOutput\n"
    "- Individuals are linked to classes via: ?individual rdf:type ?class\n"
    "- Include subclass hierarchy with rdf:type/rdfs:subClassOf* or rdfs:subClassOf*\n"
    "- Use property paths as shown in the examples\n\n"
    "IMPORTANT RULES:\n"
    "- Do not invent classes, properties, or IRIs.\n"
    "- Use only the listed prefixes and vocabulary.\n"
    "- Always include LIMIT 100 unless the user explicitly asks for all results.\n"
    "- Prefer OPTIONAL blocks for fields that may not exist.\n"
    "- If the question cannot be answered with the ontology, return exactly: CANNOT_ANSWER_WITH_ONTOLOGY\n"
    "- Return ONLY the SPARQL query, with no markdown fences."
)

REPAIR_MESSAGE = (
    "The previous SPARQL was invalid for this ontology or could not be parsed. "
    "Fix it strictly using the provided ontology vocabulary and return ONLY corrected SPARQL."
)


class NLQRequest(BaseModel):
    question: str
    repo: str | None = None
    answer_mode: str | None = None


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


def _active_provider_config(settings: MLLESettings) -> dict:
    return settings.llm_providers[settings.active_llm_provider].model_dump()


def _build_ontology_context(
    schema_rows: list,
    prefix_rows: list,
    sample_rows: list,
    individual_rows: list | None = None,
) -> dict:
    def _is_valid_iri(iri: str) -> bool:
        return bool(iri) and (iri.startswith("http://") or iri.startswith("https://"))

    classes = []
    object_properties = []
    datatype_properties = []
    annotation_properties = []
    individuals = []

    for row in schema_rows:
        iri = row.get("entity") or ""
        if not _is_valid_iri(iri):
            continue
        entry = {"iri": iri, "label": row.get("label") or ""}
        rtype = row.get("type", "")
        if rtype == "Class":
            entry["superclass"] = row.get("domain", "")
            classes.append(entry)
        elif rtype == "ObjectProperty":
            entry["domain"] = row.get("domain", "")
            entry["range"] = row.get("range", "")
            object_properties.append(entry)
        elif rtype == "DatatypeProperty":
            entry["domain"] = row.get("domain", "")
            entry["range"] = row.get("range", "")
            datatype_properties.append(entry)
        elif rtype == "AnnotationProperty":
            annotation_properties.append(entry)

    for row in individual_rows or []:
        ind = row.get("individual") or ""
        if not _is_valid_iri(ind):
            continue
        individuals.append(
            {"iri": ind, "label": row.get("label") or "", "type": row.get("type") or ""}
        )

    ns_set: dict[str, str] = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "ml": "http://www.semanticweb.org/mnd14/ml/",
        "bfo": "http://purl.obolibrary.org/obo/",
        "iof-core": "https://spec.industrialontologies.org/ontology/core/Core/",
    }
    for row in prefix_rows:
        prefix = (row.get("prefix") or "").strip()
        namespace = (row.get("namespace") or "").strip()
        if prefix and namespace:
            ns_set[prefix] = namespace

    sample_triples = [
        f'{row.get("s", "")}  {row.get("p", "")}  {row.get("o", "")}' for row in sample_rows
    ]

    return {
        "prefixes": ns_set,
        "classes": classes,
        "object_properties": object_properties,
        "datatype_properties": datatype_properties,
        "annotation_properties": annotation_properties,
        "individuals": individuals,
        "sample_triples": sample_triples,
    }


def _compact_iri(iri: str, prefix_map: dict[str, str]) -> str:
    for prefix, namespace in prefix_map.items():
        if iri.startswith(namespace):
            return f"{prefix}:{iri[len(namespace):]}"
    return f"<{iri}>"


def _tokenize_query(text: str) -> set[str]:
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "get",
        "how", "in", "is", "it", "list", "me", "of", "on", "or", "show", "that",
        "the", "their", "to", "use", "used", "using", "what", "which", "with",
        "all", "find", "give", "return",
    }
    raw = re.findall(r"[A-Za-z0-9_]+", text.lower())
    return {token for token in raw if len(token) > 2 and token not in stopwords}


def _extract_terms(label: str, iri: str) -> set[str]:
    terms: set[str] = set()
    if label:
        terms.update(re.findall(r"[A-Za-z0-9_]+", label.lower()))
    local = iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1]
    local = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", local).lower()
    terms.update(re.findall(r"[A-Za-z0-9_]+", local))
    return {term for term in terms if len(term) > 2}


def _build_relevant_subgraph(
    ctx: dict,
    user_question: str,
    max_classes: int = 80,
    max_object_properties: int = 120,
    max_datatype_properties: int = 80,
) -> dict:
    query_tokens = _tokenize_query(user_question)
    if not query_tokens:
        return ctx

    classes = ctx["classes"]
    object_properties = ctx["object_properties"]
    datatype_properties = ctx["datatype_properties"]
    individuals = ctx.get("individuals", [])
    class_by_iri = {item["iri"]: item for item in classes}

    scored_classes = []
    for item in classes:
        score = len(query_tokens & _extract_terms(item.get("label", ""), item["iri"]))
        if score > 0:
            scored_classes.append((score, item))
    scored_classes.sort(key=lambda value: value[0], reverse=True)
    selected_class_iris = {item["iri"] for _, item in scored_classes[:max_classes]}

    scored_object_properties = []
    for item in object_properties:
        score = len(query_tokens & _extract_terms(item.get("label", ""), item["iri"]))
        if item.get("domain") in selected_class_iris or item.get("range") in selected_class_iris:
            score += 1
        if score > 0:
            scored_object_properties.append((score, item))
    scored_object_properties.sort(key=lambda value: value[0], reverse=True)
    selected_object_properties = [item for _, item in scored_object_properties[:max_object_properties]]

    scored_datatype_properties = []
    for item in datatype_properties:
        score = len(query_tokens & _extract_terms(item.get("label", ""), item["iri"]))
        if item.get("domain") in selected_class_iris:
            score += 1
        if score > 0:
            scored_datatype_properties.append((score, item))
    scored_datatype_properties.sort(key=lambda value: value[0], reverse=True)
    selected_datatype_properties = [item for _, item in scored_datatype_properties[:max_datatype_properties]]

    scored_individuals = []
    for item in individuals:
        score = len(query_tokens & _extract_terms(item.get("label", ""), item["iri"]))
        if item.get("type") in selected_class_iris:
            score += 1
        if score > 0:
            scored_individuals.append((score, item))
    scored_individuals.sort(key=lambda value: value[0], reverse=True)
    selected_individuals = [item for _, item in scored_individuals[:120]]

    for item in selected_object_properties + selected_datatype_properties:
        if item.get("domain") in class_by_iri:
            selected_class_iris.add(item["domain"])
        if item.get("range") in class_by_iri:
            selected_class_iris.add(item["range"])

    for iri in list(selected_class_iris):
        superclass = class_by_iri.get(iri, {}).get("superclass")
        if superclass in class_by_iri:
            selected_class_iris.add(superclass)

    selected_classes = [item for item in classes if item["iri"] in selected_class_iris][:max_classes]
    if not selected_classes and not selected_object_properties and not selected_datatype_properties and not selected_individuals:
        return ctx

    return {
        "prefixes": ctx["prefixes"],
        "classes": selected_classes,
        "object_properties": selected_object_properties,
        "datatype_properties": selected_datatype_properties,
        "annotation_properties": ctx["annotation_properties"],
        "individuals": selected_individuals,
        "sample_triples": ctx["sample_triples"],
    }


def _ontology_context_to_text(ctx: dict, max_chars: int = 8000) -> str:
    prefixes = ctx["prefixes"]
    lines = ["=== PREFIXES ==="]
    for prefix, namespace in prefixes.items():
        lines.append(f"PREFIX {prefix}: <{namespace}>")

    lines.append("\n=== CLASSES ===")
    for item in ctx["classes"]:
        label_suffix = f'  # {item["label"]}' if item.get("label") else ""
        lines.append(f'  {_compact_iri(item["iri"], prefixes)}{label_suffix}')

    lines.append("\n=== OBJECT PROPERTIES ===")
    for item in ctx["object_properties"]:
        parts = [_compact_iri(item["iri"], prefixes)]
        if item.get("domain"):
            parts.append(f'domain={_compact_iri(item["domain"], prefixes)}')
        if item.get("range"):
            parts.append(f'range={_compact_iri(item["range"], prefixes)}')
        lines.append(f'  {" ".join(parts)}')

    lines.append("\n=== DATATYPE PROPERTIES ===")
    for item in ctx["datatype_properties"]:
        parts = [_compact_iri(item["iri"], prefixes)]
        if item.get("domain"):
            parts.append(f'domain={_compact_iri(item["domain"], prefixes)}')
        if item.get("range"):
            parts.append(f'range={_compact_iri(item["range"], prefixes)}')
        lines.append(f'  {" ".join(parts)}')

    lines.append("\n=== NAMED INDIVIDUALS ===")
    for item in ctx.get("individuals", []):
        parts = [_compact_iri(item["iri"], prefixes)]
        if item.get("type"):
            parts.append(f'type={_compact_iri(item["type"], prefixes)}')
        if item.get("label"):
            parts.append(f'label="{item["label"]}"')
        lines.append(f'  {" ".join(parts)}')

    text = "\n".join(lines)
    if len(text) > max_chars:
        idx = text.find("\n=== NAMED INDIVIDUALS")
        if idx != -1:
            text = text[:idx]
    if len(text) > max_chars:
        idx = text.find("\n=== DATATYPE PROPERTIES")
        if idx != -1:
            text = text[:idx]
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (truncated to fit context window)"
    return text


def _extract_sparql(raw: str) -> str:
    match = re.search(r"```(?:sparql)?\s*(.+?)```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    for keyword in ("SELECT", "ASK", "CONSTRUCT", "DESCRIBE", "PREFIX"):
        idx = raw.upper().find(keyword)
        if idx != -1:
            return raw[idx:].strip()
    return raw.strip()


def _contains_cannot_answer(text: str) -> bool:
    return "CANNOT_ANSWER_WITH_ONTOLOGY" in (text or "").upper()


def _inject_prefixes(sparql: str, ctx: dict) -> str:
    prefix_map = dict(ctx["prefixes"])
    declared = {
        match.group(1)
        for match in re.finditer(r"PREFIX\s+(\w[\w-]*):\s*<[^>]+>", sparql, re.IGNORECASE)
    }
    body = "\n".join(
        line for line in sparql.split("\n") if not line.strip().upper().startswith("PREFIX")
    )
    used = set(re.findall(r"(\b\w[\w-]*):", body))
    used -= {"http", "https", "urn", "mailto", "tel", "ftp"}
    missing = [f"PREFIX {prefix}: <{prefix_map[prefix]}>" for prefix in sorted(used) if prefix not in declared and prefix in prefix_map]
    return ("\n".join(missing) + "\n" + sparql) if missing else sparql


def _validate_sparql(sparql: str, ctx: dict) -> list[str]:
    errors = []
    known_class_iris = {item["iri"] for item in ctx["classes"]}
    known_individual_iris = {item["iri"] for item in ctx.get("individuals", [])}
    known_prop_iris = {
        item["iri"]
        for collection in (ctx["object_properties"], ctx["datatype_properties"], ctx["annotation_properties"])
        for item in collection
    }
    prefix_map = dict(ctx["prefixes"])
    declared_prefixes = {
        match.group(1): match.group(2)
        for match in re.finditer(r"PREFIX\s+(\w[\w-]*):\s*<([^>]+)>", sparql, re.IGNORECASE)
    }
    body = "\n".join(
        line for line in sparql.split("\n") if not line.strip().upper().startswith("PREFIX")
    )
    used_prefixes = set(re.findall(r"(\b\w[\w-]*):", body))
    used_prefixes -= {"http", "https", "urn", "mailto", "tel", "ftp"}
    for prefix in used_prefixes:
        if prefix not in declared_prefixes and prefix not in prefix_map:
            errors.append(f"Undefined prefix used: {prefix}:")

    prefixed_names = re.findall(r"(\b\w[\w-]*):(\w+)", body)
    all_known = known_class_iris | known_prop_iris | known_individual_iris
    known_local_names = {
        iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1]
        for iri in all_known
    }
    skip_prefixes = {"rdf", "rdfs", "owl", "xsd", "skos", "dcterms", "dc", "foaf", "sh"}
    for prefix, local in prefixed_names:
        if prefix in skip_prefixes:
            continue
        namespace = declared_prefixes.get(prefix) or prefix_map.get(prefix)
        if namespace and (namespace + local) not in all_known and local not in known_local_names:
            if not re.match(r"[A-Z]+_\d+", local):
                errors.append(f"Term not in ontology: {prefix}:{local}")
    return errors


async def _load_ontology_context(client: GraphDBClient, repo: str) -> dict:
    try:
        schema_rows = await client.get_ontology_schema(repo)
        prefix_rows = await client.get_prefixes(repo)
        sample_rows = await client.get_sample_triples(repo)
        individual_rows = await client.get_named_individuals(repo)
    except Exception as exc:
        logger.error("Failed to fetch ontology schema: %s", exc)
        raise HTTPException(status_code=500, detail=ONTOLOGY_UNAVAILABLE_USER_MESSAGE) from exc
    return _build_ontology_context(schema_rows, prefix_rows, sample_rows, individual_rows)


async def _generate_sparql(
    question: str,
    repo: str,
    settings: MLLESettings,
    graphdb_client: GraphDBClient,
    gateway: LLMGateway,
) -> tuple[str, dict]:
    ctx = await _load_ontology_context(graphdb_client, repo)
    prompt_ctx = _build_relevant_subgraph(ctx, question)
    ontology_text = _ontology_context_to_text(prompt_ctx)
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {
            "role": "user",
            "content": (
                f"User question: {question}\n\n"
                f"Ontology schema:\n{ontology_text}\n\n"
                f"{EXAMPLE_QUERIES}\n\n"
                "Generate a SPARQL SELECT query to answer the question. "
                "Use ONLY the listed classes, properties, individuals, and prefixes."
            ),
        },
    ]
    provider_config = _active_provider_config(settings)
    try:
        raw_sparql = await gateway.chat_completion(messages, provider_config)
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if _contains_cannot_answer(raw_sparql):
        raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")

    sparql = _extract_sparql(raw_sparql)
    if _contains_cannot_answer(sparql):
        raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
    errors = _validate_sparql(sparql, ctx)
    if errors:
        repair_messages = messages + [
            {"role": "assistant", "content": sparql},
            {"role": "user", "content": f"{REPAIR_MESSAGE}\n\nValidation errors:\n- " + "\n- ".join(errors)},
        ]
        try:
            repaired = await gateway.chat_completion(repair_messages, provider_config)
            if _contains_cannot_answer(repaired):
                raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
            sparql = _extract_sparql(repaired)
            if _contains_cannot_answer(sparql):
                raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
        except LLMServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        errors = _validate_sparql(sparql, ctx)
        if errors:
            raise HTTPException(status_code=422, detail="Generated SPARQL could not be validated.")

    return _inject_prefixes(sparql, ctx), ctx


def _dataset_role_params_to_query_args(dataset_roles: Any) -> list[str] | None:
    if not isinstance(dataset_roles, list):
        return None
    mapping = {
        "training": "training_data",
        "test": "test_data",
        "validation": "validation_data",
        "production": "production_data",
        "raw": "raw_data",
    }
    values = [f"{mapping[item]},true" for item in dataset_roles if item in mapping]
    return values or None


def _normalize_list(value: Any) -> list[str] | None:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return None


def _build_compare_pipelines_query(pipeline_ids: list[str]) -> str:
    escaped = " ".join(f'"{item}"' for item in pipeline_ids if item)
    return f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT
    (STRAFTER(STR(?pipeline), "#") AS ?pipeline_name)
    ?pipeline_type
    ?pipeline_components
    (STRAFTER(STR(?pipeline_data_input_iri), "#") AS ?pipeline_data_input)
    (STRAFTER(STR(?pipeline_data_output_iri), "#") AS ?pipeline_data_output)
    (STRAFTER(STR(?pipeline_associated_model_iri), "#") AS ?pipeline_associated_model)
WHERE {{
    {{
        SELECT ?pipeline ?pipeline_type
            (GROUP_CONCAT(DISTINCT ?pipeline_component_label; separator=";") AS ?pipeline_components)
        WHERE {{
            VALUES ?pipeline_name_filter {{ {escaped} }}
            ?pipeline rdf:type ?pipeline_type_iri .
            FILTER(?pipeline_type_iri != owl:NamedIndividual)
            ?pipeline_type_iri rdfs:label ?pipeline_type .
            FILTER(STRAFTER(STR(?pipeline), "#") = ?pipeline_name_filter)
            ?pipeline bfo:BFO_0000117 ?pipeline_component .
            ?pipeline_component rdf:type ?pipeline_component_type .
            FILTER(?pipeline_component_type != owl:NamedIndividual)
            ?pipeline_component_type rdfs:label ?pipeline_component_label
        }}
        GROUP BY ?pipeline ?pipeline_type
    }}
    OPTIONAL {{ ?pipeline ml:hasDataInput ?pipeline_data_input_iri }}
    OPTIONAL {{ ?pipeline ml:hasDataOutput ?pipeline_data_output_iri }}
    OPTIONAL {{
        {{
            ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }} UNION {{
            ?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }}
    }}
}}
ORDER BY ?pipeline_name
"""


def _normalize_identifier(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip("/").rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    return value.strip('"')


def _pipeline_names_from_params(params: dict[str, Any]) -> list[str]:
    candidates = (
        _normalize_list(params.get("pipeline_ids"))
        or _normalize_list(params.get("pipeline_names"))
        or _normalize_list(params.get("pipelines"))
    )
    return [_normalize_identifier(item) for item in candidates if _normalize_identifier(item)]


def _resolve_explore_category_target(category_name: str) -> str:
    category_value = (category_name or "").strip()
    if not category_value:
        return "ml:MachineLearningModel"
    if category_value.startswith("http://") or category_value.startswith("https://"):
        return f"<{category_value}>"
    lowered = category_value.lower()
    keyword_map = {
        "model": "ml:MachineLearningModel",
        "models": "ml:MachineLearningModel",
        "dataset": "ml:MachineLearningDataSet",
        "datasets": "ml:MachineLearningDataSet",
        "pipeline": "ml:DataProcessingPipeline",
        "pipelines": "ml:DataProcessingPipeline",
        "metric": "ml:PerformanceMetric",
        "metrics": "ml:PerformanceMetric",
        "performance": "ml:PerformanceMetric",
    }
    if lowered in keyword_map:
        return keyword_map[lowered]
    if ":" in category_value:
        return category_value
    return f"ml:{category_value}"


def _build_explore_category_query(category_name: str) -> str:
    target = _resolve_explore_category_target(category_name)
    return f"""
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?entity ?entity_type ?label
WHERE {{
    {{
        ?entity rdfs:subClassOf+ {target} .
        BIND("Class" AS ?entity_type)
        OPTIONAL {{ ?entity rdfs:label ?label }}
        FILTER(?entity != <http://www.w3.org/2002/07/owl#Nothing>)
    }}
    UNION
    {{
        ?entity rdf:type/rdfs:subClassOf* {target} .
        OPTIONAL {{ ?entity rdf:type/rdfs:label ?entity_type }}
        OPTIONAL {{ ?entity rdfs:label ?label }}
        FILTER(?entity != <http://www.w3.org/2002/07/owl#Nothing>)
    }}
}}
LIMIT 100
"""


def _performance_query_spec(question: str) -> dict[str, Any] | None:
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


def _build_performance_query_from_spec(
    spec: dict[str, Any],
    *,
    include_dataset: bool = False,
) -> str:
    dataset_projection = " ?test_dataset ?test_dataset_role" if include_dataset else ""
    dataset_pattern = ""
    if include_dataset:
        dataset_pattern = """
    ?ml_process ml:hasDataInput ?test_dataset .
    ?test_dataset rdf:type ?test_dataset_type .
    ?test_dataset_type rdfs:subClassOf* ml:TestDataSet .
    OPTIONAL { ?test_dataset_type rdfs:label ?test_dataset_role }
"""
    threshold_clause = ""
    if spec["threshold_op"] and spec["threshold_value"]:
        threshold_clause = f"FILTER(xsd:decimal(?model_performance_value) {spec['threshold_op']} {spec['threshold_value']})"
    return f"""
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?model_name ?model_performance_metric ?model_performance_value{dataset_projection} WHERE {{
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
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
    {dataset_pattern}
}}
ORDER BY {spec['order']}(xsd:decimal(?model_performance_value))
LIMIT {spec['limit']}
"""


def _build_performance_query(question: str) -> str | None:
    spec = _performance_query_spec(question)
    if not spec:
        return None
    return _build_performance_query_from_spec(spec)


def _question_requests_dataset_context(question: str) -> bool:
    lowered = question.lower()
    return any(token in lowered for token in ("test dataset", "dataset", "data set"))


def _question_requests_pipeline_context(question: str) -> bool:
    lowered = question.lower()
    return "pipeline" in lowered or "pipelines" in lowered


def _question_requests_model_context(question: str) -> bool:
    lowered = question.lower()
    return "model" in lowered or "models" in lowered


def _build_model_dataset_query(model_iris: list[str], *, dataset_kind: str = "test") -> str:
    escaped_models = " ".join(f"<{model}>" for model in model_iris if model)
    dataset_class = "ml:TestDataSet" if dataset_kind == "test" else "ml:MachineLearningDataSet"
    return f"""
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model_name ?dataset ?dataset_role WHERE {{
    VALUES ?model_name {{ {escaped_models} }}
    ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
    ?ml_process ml:hasDataInput ?dataset .
    ?dataset rdf:type ?dataset_type .
    ?dataset_type rdfs:subClassOf* {dataset_class} .
    OPTIONAL {{ ?dataset_type rdfs:label ?dataset_role }}
}}
LIMIT 200
"""


def _build_model_pipeline_query(model_iris: list[str]) -> str:
    escaped_models = " ".join(f"<{model}>" for model in model_iris if model)
    return f"""
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model_name ?pipeline WHERE {{
    VALUES ?model_name {{ {escaped_models} }}
    ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model_name .
}}
LIMIT 200
"""


def _dedupe_model_performance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (
            row.get("model_name"),
            row.get("model_performance_metric"),
            row.get("model_performance_value"),
            row.get("test_dataset"),
            row.get("test_dataset_role"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _aggregate_best_performance_by_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _merge_model_dataset_rows(
    performance_rows: list[dict[str, Any]],
    dataset_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    datasets_by_model: dict[str, list[dict[str, Any]]] = {}
    for row in dataset_rows:
        model_name = row.get("model_name")
        if not model_name:
            continue
        bucket = datasets_by_model.setdefault(model_name, [])
        candidate = {
            "test_dataset": row.get("dataset"),
            "test_dataset_role": row.get("dataset_role"),
        }
        if candidate not in bucket:
            bucket.append(candidate)
    merged = []
    for row in performance_rows:
        datasets = datasets_by_model.get(row.get("model_name"), [])
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


def _merge_model_pipeline_rows(
    performance_rows: list[dict[str, Any]],
    pipeline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pipelines_by_model: dict[str, list[str]] = {}
    for row in pipeline_rows:
        model_name = row.get("model_name")
        pipeline = row.get("pipeline")
        if not model_name or not pipeline:
            continue
        bucket = pipelines_by_model.setdefault(model_name, [])
        if pipeline not in bucket:
            bucket.append(pipeline)
    return [
        {
            **row,
            "pipelines": pipelines_by_model.get(row.get("model_name"), []),
        }
        for row in performance_rows
    ]


def _plan_performance_enrichment_steps(question: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if _question_requests_dataset_context(question):
        steps.append(
            {
                "tool": "find_test_datasets_for_models",
                "params": {"dataset_kind": "test"},
                "reasoning": "The question asks for related test-dataset context.",
            }
        )
    if _question_requests_pipeline_context(question):
        steps.append(
            {
                "tool": "find_pipelines_for_models",
                "params": {},
                "reasoning": "The question asks for related pipeline context.",
            }
        )
    return steps


async def _execute_performance_orchestration(
    *,
    question: str,
    resolved_repo: str,
    state: NLQQueryState,
    graphdb_client: GraphDBClient,
) -> NLQExecutionPayload:
    performance_spec = _performance_query_spec(question)
    if not performance_spec:
        raise ValueError("Performance orchestration requires a performance query spec.")

    performance_sparql = _build_performance_query_from_spec(performance_spec)
    performance_rows = await graphdb_client.query(
        performance_sparql,
        repo=resolved_repo,
        use_inference=False,
    )
    performance_rows = _dedupe_model_performance_rows(performance_rows)
    state.add_step(
        tool="performance_filter",
        params=performance_spec,
        sparql=performance_sparql,
        results=performance_rows,
        inference_used=False,
        reasoning="Deterministic performance filter query.",
    )

    model_iris = sorted({row.get("model_name") for row in performance_rows if row.get("model_name")})
    state.set_artifact("matching_models", model_iris)
    enrichment_plan = _plan_performance_enrichment_steps(question)
    for plan_step in enrichment_plan:
        state.add_plan_step(
            tool=plan_step["tool"],
            params=plan_step.get("params"),
            reasoning=plan_step.get("reasoning"),
        )

    should_enrich_per_model = bool(enrichment_plan) and bool(model_iris)
    combined_results = _aggregate_best_performance_by_model(performance_rows) if should_enrich_per_model else performance_rows
    sparql_parts = [f"-- Step 1: performance filter\n{performance_sparql}"]

    for index, plan_step in enumerate(enrichment_plan, start=2):
        tool = plan_step["tool"]
        if not model_iris:
            break

        if tool == "find_test_datasets_for_models":
            dataset_kind = plan_step.get("params", {}).get("dataset_kind", "test")
            step_sparql = _build_model_dataset_query(model_iris, dataset_kind=dataset_kind)
            step_rows = await graphdb_client.query(
                step_sparql,
                repo=resolved_repo,
                use_inference=False,
            )
            state.add_step(
                tool=tool,
                params={"model_iris": model_iris, "dataset_kind": dataset_kind},
                sparql=step_sparql,
                results=step_rows,
                inference_used=False,
                reasoning=plan_step.get("reasoning"),
            )
            combined_results = _merge_model_dataset_rows(combined_results, step_rows)
            sparql_parts.append(f"-- Step {index}: model {dataset_kind} datasets\n{step_sparql}")
            continue

        if tool == "find_pipelines_for_models":
            step_sparql = _build_model_pipeline_query(model_iris)
            step_rows = await graphdb_client.query(
                step_sparql,
                repo=resolved_repo,
                use_inference=False,
            )
            state.add_step(
                tool=tool,
                params={"model_iris": model_iris},
                sparql=step_sparql,
                results=step_rows,
                inference_used=False,
                reasoning=plan_step.get("reasoning"),
            )
            combined_results = _merge_model_pipeline_rows(combined_results, step_rows)
            sparql_parts.append(f"-- Step {index}: model pipelines\n{step_sparql}")

    state.set_artifact("merged_rows", combined_results)
    return NLQExecutionPayload(
        sparql="\n\n".join(sparql_parts),
        results=combined_results,
        inference_used=False,
        state=state,
    )


async def _execute_structured_tool(
    intent: QueryIntent,
    repo: str,
    use_inference: bool,
    graphdb_client: GraphDBClient,
) -> tuple[str, list[dict]]:
    params = intent.params or {}
    if intent.tool == "find_datasets":
        query_builder = FindDatasetsQueryBuilder(
            query_variables=[
                "?model",
                "?model_type",
                "?model_objective",
                "?dataset",
                "?ml_input_timestamp",
                "?model_output",
                "?model_output_utilization",
            ],
            search_term=params.get("search_term") or params.get("dataset_name") or "",
            dataset_role=_dataset_role_params_to_query_args(params.get("dataset_roles")),
            type_query=bool(params.get("type_query", False)),
            model_types=_normalize_list(params.get("model_types")),
            sort=None,
        )
        sparql = query_builder.build_query()
    elif intent.tool == "find_models":
        query_builder = FindModelsQueryBuilder(
            search_term=params.get("search_term") or params.get("dataset_name") or "",
            dataset_role=_dataset_role_params_to_query_args(params.get("dataset_roles")),
            model_types=_normalize_list(params.get("model_types")),
            sort=None,
        )
        sparql = query_builder.build_query()
    elif intent.tool == "find_pipelines":
        query_builder = FindPipelinesQueryBuilder(
            search_term=params.get("search_term") or params.get("pipeline_name") or "",
            toggle_constraint=bool(params.get("toggle_constraint", False)),
            sort=None,
            pipeline_types=_normalize_list(params.get("pipeline_types")),
        )
        sparql = query_builder.build_query()
    elif intent.tool == "analyze_deployed_models":
        sparql = DeployedModelsQueryBuilder(search_term=params.get("search_term") or "", sort=None).build_query()
    elif intent.tool == "compare_pipelines":
        sparql = _build_compare_pipelines_query(_pipeline_names_from_params(params))
    elif intent.tool == "get_artifact_details":
        sparql = IriQueryBuilder(params.get("iri") or "").build_query()
    elif intent.tool == "explore_category":
        sparql = _build_explore_category_query(
            params.get("category_name") or params.get("category") or params.get("search_term") or ""
        )
    else:
        raise ValueError(f"Unsupported structured tool: {intent.tool}")

    results = await graphdb_client.query(sparql, repo=repo, use_inference=use_inference)
    return sparql, results


async def _execute_with_state(
    *,
    question: str,
    intent: QueryIntent,
    resolved_repo: str,
    use_inference: bool,
    settings: MLLESettings,
    graphdb_client: GraphDBClient,
    gateway: LLMGateway,
) -> NLQExecutionPayload:
    state = NLQQueryState(question=question, repo=resolved_repo)
    state.set_artifact("intent", intent.model_dump())

    performance_spec = _performance_query_spec(question)
    if performance_spec:
        return await _execute_performance_orchestration(
            question=question,
            resolved_repo=resolved_repo,
            state=state,
            graphdb_client=graphdb_client,
        )

    if intent.tool in {
        "find_datasets",
        "find_models",
        "find_pipelines",
        "analyze_deployed_models",
        "compare_pipelines",
        "get_artifact_details",
        "explore_category",
    }:
        sparql, results = await _execute_structured_tool(
            intent, resolved_repo, use_inference, graphdb_client
        )
        state.add_step(
            tool=intent.tool,
            params=intent.params,
            sparql=sparql,
            results=results,
            inference_used=use_inference,
            reasoning=intent.reasoning,
        )
        return NLQExecutionPayload(
            sparql=sparql,
            results=results,
            inference_used=use_inference,
            state=state,
        )

    sparql, _ = await _generate_sparql(
        intent.params.get("question") or question,
        resolved_repo,
        settings,
        graphdb_client,
        gateway,
    )
    try:
        results = await graphdb_client.query(
            sparql,
            repo=resolved_repo,
            use_inference=use_inference,
        )
    except Exception as exc:
        repair_prompt = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "assistant", "content": sparql},
            {"role": "user", "content": f"{REPAIR_MESSAGE}\n\nExecution error:\n{exc}"},
        ]
        try:
            repaired = await gateway.chat_completion(repair_prompt, _active_provider_config(settings))
            if _contains_cannot_answer(repaired):
                raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
            sparql = _inject_prefixes(_extract_sparql(repaired), await _load_ontology_context(graphdb_client, resolved_repo))
            if _contains_cannot_answer(sparql):
                raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
            results = await graphdb_client.query(
                sparql,
                repo=resolved_repo,
                use_inference=use_inference,
            )
        except Exception as inner_exc:
            raise HTTPException(status_code=422, detail=str(inner_exc)) from inner_exc
    state.add_step(
        tool="custom_sparql",
        params=intent.params,
        sparql=sparql,
        results=results,
        inference_used=use_inference,
        reasoning=intent.reasoning,
    )
    return NLQExecutionPayload(
        sparql=sparql,
        results=results,
        inference_used=use_inference,
        state=state,
    )


async def _generate_answer(
    question: str,
    results: list[dict],
    settings: MLLESettings,
    gateway: LLMGateway,
    state: NLQQueryState | None = None,
) -> str:
    if not results:
        return "No matching results were found in the selected repository."
    preview = json.dumps(results[:20], indent=2)
    steps_text = ""
    if state and (state.plan or state.steps):
        plan_summaries = [
            {
                "tool": step.tool,
                "params": step.params,
                "reasoning": step.reasoning,
            }
            for step in state.plan
        ]
        step_summaries = [
            {
                "tool": step.tool,
                "params": step.params,
                "result_count": len(step.results),
            }
            for step in state.steps
        ]
        steps_text = (
            f"\n\nPlanned steps:\n{json.dumps(plan_summaries, indent=2)}"
            f"\n\nExecution steps:\n{json.dumps(step_summaries, indent=2)}"
        )
    try:
        return await gateway.chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Summarize ML ontology query results for a non-technical practitioner. "
                        "Be concise and factual. If the results already include joined fields such as "
                        "test_datasets or pipelines, use them directly and do not replace them with generic guesses."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nFiltered results:\n{preview}{steps_text}",
                },
            ],
            _active_provider_config(settings),
        )
    except LLMServiceError:
        return f"Found {len(results)} result(s) for the question."


async def execute_nlq(
    question: str,
    repo: str | None = None,
    answer_mode: str | None = None,
) -> NLQResponse:
    settings = load_settings()
    resolved_answer_mode = answer_mode or settings.answer_mode
    graphdb_client = GraphDBClient(
        base_url=settings.graphdb_url,
        default_repo=settings.graphdb_default_repo,
        repo_allowlist=settings.graphdb_repo_allowlist,
    )
    gateway = LLMGateway()

    try:
        resolved_repo = await graphdb_client.validate_repo(repo or settings.graphdb_default_repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    intent = await classify_intent(question, gateway, _active_provider_config(settings))
    if resolved_answer_mode == "exact":
        use_inference = False
    elif resolved_answer_mode == "conceptual":
        use_inference = True
    else:
        use_inference = intent.use_inference

    execution = await _execute_with_state(
        question=question,
        intent=intent,
        resolved_repo=resolved_repo,
        use_inference=use_inference,
        settings=settings,
        graphdb_client=graphdb_client,
        gateway=gateway,
    )

    answer = await _generate_answer(question, execution.results, settings, gateway, state=execution.state)
    return NLQResponse(
        question=question,
        intent=intent,
        sparql=execution.sparql,
        results=execution.results,
        answer=answer,
        repo_used=resolved_repo,
        inference_used=execution.inference_used,
    )


@router.post("/query")
async def nlq_query(body: NLQRequest) -> NLQResponse:
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")
    return await execute_nlq(body.question.strip(), repo=body.repo, answer_mode=body.answer_mode)
