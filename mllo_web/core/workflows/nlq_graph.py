from __future__ import annotations

import logging
import os
import re
from typing import Any, Literal, TypedDict

from fastapi import HTTPException
from pydantic import BaseModel, Field

from mllo_web.app.api.services.graphdb_client import GraphDBClient
from mllo_web.app.api.services.settings_model import MLLESettings
from mllo_web.core.domain.nlq import NLQExecutionPayload, NLQQueryState, NLQResponse
from mllo_web.core.llm import LLMGateway, QueryIntent, classify_intent
from mllo_web.core.workflows.answering import generate_answer
from mllo_web.core.workflows.generation import (
    build_empty_result_repair_messages,
    build_execution_repair_messages,
    contains_cannot_answer,
    empty_result_fallback_candidates,
    extract_sparql,
    generate_sparql,
    inject_prefixes,
    relationship_fallback_candidates,
)
from mllo_web.core.workflows.lineage import execute_lineage_orchestration, lineage_query_spec
from mllo_web.core.workflows.lineage import current_question_text
from mllo_web.core.workflows.performance import execute_performance_orchestration, performance_query_spec
from mllo_web.core.workflows.schema_bridge import schema_bridge_grounding
from mllo_web.core.workflows.shared import active_provider_config

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - exercised only when optional dependency is absent locally.
    END = "__end__"
    START = "__start__"
    StateGraph = None  # type: ignore[assignment]

try:
    from pydantic_ai import Agent as PydanticAIAgent
except ImportError:  # pragma: no cover - pydantic-ai is a declared runtime dependency.
    PydanticAIAgent = None  # type: ignore[assignment]


STRUCTURED_TOOLS = {
    "find_datasets",
    "find_models",
    "find_pipelines",
    "analyze_deployed_models",
    "compare_pipelines",
    "get_artifact_details",
    "explore_category",
}
MAX_GRAPH_ITERATIONS = 20
MAX_SPARQL_REPAIRS = 5
OWL_CLASS_IRI = "http://www.w3.org/2002/07/owl#Class"
RDFS_CLASS_IRI = "http://www.w3.org/2000/01/rdf-schema#Class"
OWL_NAMED_INDIVIDUAL_IRI = "http://www.w3.org/2002/07/owl#NamedIndividual"
OWL_ANNOTATION_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#AnnotationProperty"
OWL_ONTOLOGY_IRI = "http://www.w3.org/2002/07/owl#Ontology"
PROMPT_PREFIXES = {
    "http://www.semanticweb.org/mnd14/ml/": "ml:",
    "http://purl.obolibrary.org/obo/": "bfo:",
    "https://spec.industrialontologies.org/ontology/core/Core/": "iof-core:",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
    "http://www.w3.org/2002/07/owl#": "owl:",
    "http://www.w3.org/2004/02/skos/core#": "skos:",
}


def _normalize_custom_result_aliases(question: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    focused = current_question_text(question).lower()
    if "model output" not in focused:
        return rows
    normalized: list[dict[str, Any]] = []
    for row in rows:
        updated = dict(row)
        if "output_dataset" not in updated:
            if "model_output" in updated:
                updated["output_dataset"] = updated["model_output"]
            elif "input_artifact" in updated and ("later" in focused or "another process" in focused):
                updated["output_dataset"] = updated["input_artifact"]
        normalized.append(updated)
    return normalized


def _local_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    if "#" in value:
        return value.rsplit("#", 1)[-1]
    return value.rstrip("/").rsplit("/", 1)[-1]


def _iter_observation_rows(observations: dict[str, Any] | None):
    if not isinstance(observations, dict):
        return
    for result in observations.get("results", []):
        if not isinstance(result, dict):
            continue
        tool = result.get("tool")
        payload = result.get("payload") or []
        if isinstance(payload, dict):
            nested = payload.get("results") or payload.get("payload") or []
            payload = nested if isinstance(nested, list) else []
        if not isinstance(payload, list):
            continue
        for row in payload:
            if isinstance(row, dict):
                yield tool, row


def _observation_node_priority(tool: str | None, field: str, row: dict[str, Any], iri: str) -> tuple[int, int, int, str]:
    type_value = row.get("type") or row.get(f"{field}_type")
    is_class = type_value in {OWL_CLASS_IRI, RDFS_CLASS_IRI}
    try:
        match_rank = int(float(str(row.get("match_rank", 9))))
    except (TypeError, ValueError):
        match_rank = 9
    try:
        node_kind_rank = int(float(str(row.get("node_kind_rank", 9))))
    except (TypeError, ValueError):
        node_kind_rank = 9
    exact_local_match = row.get("matched_term") and str(row.get("matched_term")).lower() == _local_name(iri).lower()
    tool_rank = 0 if tool in {"local_filter_by_string", "graphdb_lucene_term_search"} else 2
    class_penalty = 2 if is_class else 0
    exact_penalty = 0 if exact_local_match else 1
    return (tool_rank + class_penalty + exact_penalty, match_rank, node_kind_rank, iri)


def _canonical_iris_from_graph_observations(observations: dict[str, Any] | None) -> dict[str, str]:
    best: dict[str, tuple[tuple[int, int, int, str], str]] = {}
    node_fields = {
        "node",
        "seed",
        "neighbor",
        "individual",
        "class",
        "start",
        "end",
        "mid1",
        "mid2",
        "literal_node",
        "literal_source",
        "shared_neighbor",
        "bridge_node",
        "bridge_out_neighbor",
        "source1",
        "source1_out_neighbor",
        "source2",
        "source2_out_neighbor",
    }
    for tool, row in _iter_observation_rows(observations):
        for field in node_fields:
            iri = row.get(field)
            if not isinstance(iri, str) or not iri.startswith(("http://", "https://")):
                continue
            local = _local_name(iri)
            if not local:
                continue
            key = local.lower()
            priority = _observation_node_priority(tool, field, row, iri)
            if key not in best or priority < best[key][0]:
                best[key] = (priority, iri)
    return {key: iri for key, (_, iri) in best.items()}


def _canonicalize_sparql_iri_constants(sparql: str, canonical_iris: dict[str, str]) -> tuple[str, list[dict[str, str]]]:
    if not sparql or not canonical_iris:
        return sparql, []
    replacements: list[dict[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        iri = match.group(1)
        canonical = canonical_iris.get(_local_name(iri).lower())
        if not canonical or canonical == iri:
            return match.group(0)
        replacements.append(
            {
                "from": iri,
                "to": canonical,
                "from_label": str(_compact_graph_value(iri)),
                "to_label": str(_compact_graph_value(canonical)),
            }
        )
        return f"<{canonical}>"

    rewritten = re.sub(r"<([^>\s]+)>", replace, sparql)
    return rewritten, replacements


class LangGraphOrchestrationError(RuntimeError):
    """Raised when graph wiring/runtime fails and legacy orchestration should be used."""


class NLQPlannerAction(BaseModel):
    action: Literal[
        "structured_tool",
        "graph_native_tool",
        "custom_sparql",
        "repair_sparql",
        "answer",
        "cannot_answer",
    ]
    tool: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""


class PydanticAIPlannerAdapter:
    """Typed planner boundary for PydanticAI-style structured agent outputs.

    MLLE keeps its existing LLMGateway as the provider transport, but this
    adapter gives the graph the same validated output contract PydanticAI
    agents would use when they emit an action.
    """

    output_type = NLQPlannerAction
    agent_cls = PydanticAIAgent

    @classmethod
    def validate_action(cls, payload: dict[str, Any] | NLQPlannerAction) -> NLQPlannerAction:
        return payload if isinstance(payload, NLQPlannerAction) else cls.output_type.model_validate(payload)


class NLQGraphState(TypedDict, total=False):
    question: str
    requested_repo: str | None
    requested_answer_mode: str | None
    force_custom_sparql: bool
    custom_sparql_enhanced_prompt: bool
    resolved_answer_mode: str
    settings: MLLESettings
    graphdb_client: GraphDBClient
    gateway: LLMGateway
    resolved_repo: str
    use_inference: bool
    intent: QueryIntent
    query_state: NLQQueryState
    action: NLQPlannerAction
    execution: NLQExecutionPayload
    answer: str
    response: NLQResponse
    graph_iterations: int
    repair_attempts: int


def _pydantic_ai_available() -> bool:
    return PydanticAIAgent is not None


def _answer_mode_inference(answer_mode: str, intent: QueryIntent) -> bool:
    if answer_mode == "exact":
        return False
    if answer_mode == "conceptual":
        return True
    return intent.use_inference


def _search_term_from_question(question: str) -> str:
    terms = _search_terms_from_question(question, max_terms=1)
    return terms[0] if terms else current_question_text(question)


def _search_terms_from_question(question: str, max_terms: int = 8) -> list[str]:
    question = current_question_text(question)
    terms: list[str] = []
    stopwords = {
        "about",
        "above",
        "after",
        "along",
        "also",
        "and",
        "answer",
        "are",
        "based",
        "before",
        "below",
        "between",
        "does",
        "find",
        "from",
        "get",
        "greater",
        "is",
        "less",
        "list",
        "me",
        "make",
        "more",
        "over",
        "related",
        "return",
        "show",
        "than",
        "that",
        "their",
        "them",
        "there",
        "used",
        "using",
        "what",
        "which",
        "to",
        "with",
    }

    def add(term: str) -> None:
        normalized = term.strip().strip(".,;:()[]{}")
        if normalized and normalized.lower() not in stopwords and normalized.lower() not in {existing.lower() for existing in terms}:
            terms.append(normalized)

    iri_match = re.search(r"https?://\S+", question)
    if iri_match:
        add(iri_match.group(0).rstrip(".,)"))

    for quoted in re.findall(r"['\"]([^'\"]{3,})['\"]", question):
        add(quoted)

    candidates = re.findall(r"\b[A-Z][A-Za-z0-9_:-]*\d+\b|\b[A-Z][A-Za-z0-9_:-]{3,}\b", question)
    for candidate in candidates:
        add(candidate)

    words = re.findall(r"[A-Za-z][A-Za-z0-9_:-]+", question)
    useful = [word for word in words if word.lower() not in stopwords]
    for word in useful:
        lowered = word.lower()
        if lowered.endswith("ies") and len(word) > 4:
            add(word[:-3] + "y")
        elif lowered.endswith("s") and not lowered.endswith("ss") and len(word) > 4:
            add(word[:-1])
        add(word)
    return terms[:max_terms]


def _sparql_string_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    return f'"{escaped}"'


def _graphdb_lucene_connector_name() -> str | None:
    connector = os.getenv("GRAPHDB_LUCENE_CONNECTOR", "").strip()
    if not connector:
        return None
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", connector):
        logger.warning("Ignoring invalid GRAPHDB_LUCENE_CONNECTOR value: %s", connector)
        return None
    return connector


def _lucene_query_for_term(term: str) -> str:
    term = term.strip()
    if not term:
        return term
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{4,}", term):
        return f"{term}~1"
    if " " in term:
        return f'"{term}"'
    return term


def _sparql_iri_values(nodes: list[str]) -> str:
    return " ".join(f"<{node}>" for node in nodes if node.startswith(("http://", "https://")))


def _compact_graph_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value.startswith(("http://", "https://")):
        for namespace, prefix in PROMPT_PREFIXES.items():
            if value.startswith(namespace):
                return f"{prefix}{value[len(namespace):]}"
        if "#" in value:
            return value.rsplit("#", 1)[-1]
        return value.rstrip("/").rsplit("/", 1)[-1]
    return value


def _compact_graph_row(tool: str | None, row: dict[str, Any]) -> dict[str, Any]:
    compacted = {key: _compact_graph_value(value) for key, value in row.items() if value is not None}
    key_sets = {
        "local_filter_by_string": ("matched_term", "node", "label", "type", "match_rank", "node_kind_rank"),
        "graphdb_lucene_term_search": ("matched_term", "node", "label", "type", "score"),
        "local_node_hops": ("seed", "seed_type", "direction", "property", "neighbor", "neighbor_type"),
        "class_seed_instances": ("class", "individual", "individual_type"),
        "class_instance_node_hops": ("seed", "seed_type", "direction", "property", "neighbor", "neighbor_type"),
        "individual_literal_properties": ("seed", "seed_type", "property", "value"),
        "observed_bridge_patterns": (
            "literal_node",
            "literal_node_type",
            "literal_property",
            "literal_value",
            "literal_source",
            "literal_source_type",
            "source_to_literal_property",
            "shared_neighbor",
            "shared_neighbor_type",
            "source_to_shared_neighbor_property",
            "bridge_node",
            "bridge_node_type",
            "bridge_to_shared_neighbor_property",
            "bridge_out_property",
            "bridge_out_neighbor",
            "bridge_out_neighbor_type",
        ),
        "observed_join_skeletons": (
            "literal_node",
            "literal_property",
            "literal_value",
            "source1",
            "source1_to_literal_property",
            "source1_out_property",
            "source1_out_neighbor",
            "source2",
            "source2_to_neighbor_property",
            "source2_out_property",
            "source2_out_neighbor",
        ),
        "candidate_connection_paths": ("start", "end", "path_shape", "p1", "mid1", "p2", "mid2", "p3"),
    }
    keys = key_sets.get(tool)
    if not keys:
        return compacted
    return {key: compacted[key] for key in keys if key in compacted}


def _dedupe_compact_rows(tool: str | None, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    compact_rows: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, Any], ...]] = set()
    for row in rows:
        compacted = _compact_graph_row(tool, row)
        signature = tuple(sorted(compacted.items()))
        if signature in seen:
            continue
        seen.add(signature)
        compact_rows.append(compacted)
        if len(compact_rows) >= limit:
            break
    return compact_rows


def _compact_graph_observations_for_prompt(observations: dict[str, Any] | None) -> dict[str, Any] | None:
    if not observations:
        return observations
    row_limits = {
        "local_filter_by_string": 28,
        "graphdb_lucene_term_search": 16,
        "local_node_hops": 32,
        "class_seed_instances": 36,
        "class_instance_node_hops": 40,
        "individual_literal_properties": 32,
        "observed_bridge_patterns": 28,
        "observed_join_skeletons": 20,
        "candidate_connection_paths": 40,
    }
    compact_results = []
    for result in observations.get("results", []):
        tool = result.get("tool")
        payload = result.get("payload") or []
        if isinstance(payload, dict):
            payload = payload.get("results") or payload.get("payload") or []
        if not isinstance(payload, list):
            payload = []
        limit = row_limits.get(tool, 60)
        compact_payload = _dedupe_compact_rows(tool, payload, limit)
        compact_results.append(
            {
                "tool": tool,
                "row_count": len(payload),
                "payload": compact_payload,
            }
        )
    return {
        "search_term": observations.get("search_term"),
        "search_terms": observations.get("search_terms", []),
        "probe_strategy": observations.get("probe_strategy", []),
        "results": compact_results,
    }


def _is_class_row(row: dict[str, Any]) -> bool:
    return row.get("type") in {OWL_CLASS_IRI, RDFS_CLASS_IRI}


def _is_individualish_row(row: dict[str, Any]) -> bool:
    row_type = row.get("type")
    return bool(row.get("node")) and row_type not in {OWL_CLASS_IRI, RDFS_CLASS_IRI, OWL_ANNOTATION_PROPERTY_IRI, OWL_ONTOLOGY_IRI}


def _is_probe_seed_row(row: dict[str, Any]) -> bool:
    return _is_class_row(row) or _is_individualish_row(row)


def _ranked_nodes_by_term(
    rows: list[dict[str, Any]],
    term_order: list[str],
    *,
    predicate=None,
    per_term: int = 3,
    total: int = 24,
) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    terms = term_order or sorted({str(row.get("matched_term")) for row in rows if row.get("matched_term")})
    for term in terms:
        taken_for_term = 0
        for row in rows:
            if row.get("matched_term") != term:
                continue
            if predicate and not predicate(row):
                continue
            node = row.get("node")
            if not node or node in seen:
                continue
            selected.append(node)
            seen.add(node)
            taken_for_term += 1
            if taken_for_term >= per_term or len(selected) >= total:
                break
        if len(selected) >= total:
            break
    return selected


def _ranked_instance_nodes_by_class(
    rows: list[dict[str, Any]],
    class_order: list[str],
    *,
    per_class: int = 4,
    total: int = 40,
) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for class_iri in class_order:
        taken_for_class = 0
        for row in rows:
            if row.get("class") != class_iri:
                continue
            node = row.get("individual")
            if not node or node in seen:
                continue
            selected.append(node)
            seen.add(node)
            taken_for_class += 1
            if taken_for_class >= per_class or len(selected) >= total:
                break
        if len(selected) >= total:
            break
    return selected


async def _query_node_hops(
    graphdb_client: GraphDBClient,
    repo: str,
    seed_nodes: list[str],
    *,
    limit: int = 160,
) -> list[dict[str, Any]]:
    values = _sparql_iri_values(seed_nodes)
    if not values:
        return []
    hop_sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?seed ?seed_label ?seed_type ?direction ?property ?neighbor ?neighbor_label ?neighbor_type WHERE {{
  VALUES ?seed {{ {values} }}
  {{
    ?seed ?property ?neighbor .
    FILTER(isIRI(?neighbor))
    BIND("outgoing" AS ?direction)
  }}
  UNION
  {{
    ?neighbor ?property ?seed .
    FILTER(isIRI(?neighbor))
    BIND("incoming" AS ?direction)
  }}
  OPTIONAL {{ ?seed rdfs:label ?seed_label }}
  OPTIONAL {{ ?seed rdf:type ?seed_type }}
  OPTIONAL {{ ?neighbor rdfs:label ?neighbor_label }}
  OPTIONAL {{ ?neighbor rdf:type ?neighbor_type }}
}}
LIMIT {limit}
"""
    return await graphdb_client.query(hop_sparql, repo=repo, use_inference=False, show_upper_ontology=True)


async def _query_literal_properties(
    graphdb_client: GraphDBClient,
    repo: str,
    seed_nodes: list[str],
    *,
    limit: int = 220,
) -> list[dict[str, Any]]:
    values = _sparql_iri_values(seed_nodes)
    if not values:
        return []
    literal_sparql = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?seed ?seed_type ?property ?value WHERE {{
  VALUES ?seed {{ {values} }}
  ?seed ?property ?value .
  FILTER(!isIRI(?value))
  OPTIONAL {{ ?seed a ?seed_type }}
}}
LIMIT {limit}
"""
    return await graphdb_client.query(literal_sparql, repo=repo, use_inference=False, show_upper_ontology=True)


def _literal_seed_nodes_for_skeletons(literal_rows: list[dict[str, Any]], *, total: int = 40) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    low_priority_properties = (
        "label",
        "definition",
        "comment",
        "example",
        "equivalentclass",
        "subclassof",
    )

    def priority(row: dict[str, Any]) -> tuple[int, str]:
        prop = str(_compact_graph_value(row.get("property", ""))).lower()
        value = str(row.get("value", ""))
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", value):
            return (0, prop)
        if any(term in prop for term in ("value", "score", "result", "accuracy", "loss", "metric", "measure")):
            return (1, prop)
        if any(term in prop for term in low_priority_properties):
            return (4, prop)
        return (2, prop)

    for row in sorted(literal_rows, key=priority):
        seed = row.get("seed")
        if seed and seed not in seen:
            selected.append(seed)
            seen.add(seed)
        if len(selected) >= total:
            break
    return selected


async def _query_observed_join_skeletons(
    graphdb_client: GraphDBClient,
    repo: str,
    literal_nodes: list[str],
    *,
    limit: int = 320,
) -> list[dict[str, Any]]:
    values = _sparql_iri_values(literal_nodes)
    if not values:
        return []
    skeleton_sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT
  ?literal_node ?literal_node_type ?literal_property ?literal_value
  ?source1 ?source1_type ?source1_to_literal_property
  ?source1_out_property ?source1_out_neighbor ?source1_out_neighbor_type
  ?source2 ?source2_type ?source2_to_neighbor_property
  ?source2_out_property ?source2_out_neighbor ?source2_out_neighbor_type
WHERE {{
  VALUES ?literal_node {{ {values} }}
  ?literal_node ?literal_property ?literal_value .
  FILTER(!isIRI(?literal_value))
  OPTIONAL {{ ?literal_node rdf:type ?literal_node_type }}
  OPTIONAL {{
    ?source1 ?source1_to_literal_property ?literal_node .
    FILTER(isIRI(?source1))
    FILTER(?source1 != ?literal_node)
    OPTIONAL {{ ?source1 rdf:type ?source1_type }}
    OPTIONAL {{
      ?source1 ?source1_out_property ?source1_out_neighbor .
      FILTER(isIRI(?source1_out_neighbor))
      FILTER(?source1_out_neighbor != ?literal_node)
      FILTER(?source1_out_property != rdf:type && ?source1_out_property != rdfs:subClassOf)
      OPTIONAL {{ ?source1_out_neighbor rdf:type ?source1_out_neighbor_type }}
      OPTIONAL {{
        ?source2 ?source2_to_neighbor_property ?source1_out_neighbor .
        FILTER(isIRI(?source2))
        FILTER(?source2 != ?source1 && ?source2 != ?literal_node)
        FILTER(?source2_to_neighbor_property != rdf:type && ?source2_to_neighbor_property != rdfs:subClassOf)
        OPTIONAL {{ ?source2 rdf:type ?source2_type }}
        OPTIONAL {{
          ?source2 ?source2_out_property ?source2_out_neighbor .
          FILTER(isIRI(?source2_out_neighbor))
          FILTER(?source2_out_neighbor != ?source1_out_neighbor)
          FILTER(?source2_out_neighbor != ?source1)
          FILTER(?source2_out_property != rdf:type && ?source2_out_property != rdfs:subClassOf)
          OPTIONAL {{ ?source2_out_neighbor rdf:type ?source2_out_neighbor_type }}
        }}
      }}
    }}
  }}
}}
LIMIT {limit}
"""
    return await graphdb_client.query(skeleton_sparql, repo=repo, use_inference=False, show_upper_ontology=True)


def _low_information_type(value: Any) -> bool:
    compacted = str(_compact_graph_value(value or ""))
    return (
        not compacted
        or compacted
        in {
            "owl:Thing",
            "owl:NamedIndividual",
            "iof-core:InformationContentEntity",
            "bfo:BFO_0000002",
            "bfo:BFO_0000003",
            "bfo:BFO_0000031",
            "bfo:BFO_0000015",
        }
        or compacted.startswith("_:")
    )


def _observed_bridge_pattern_rows(skeleton_rows: list[dict[str, Any]], *, limit: int = 96) -> list[dict[str, Any]]:
    """Condense raw node-hop skeletons into bridge-shaped evidence rows."""

    def priority(row: dict[str, Any]) -> tuple[int, int, int, int, int, str, str]:
        source2_type = str(_compact_graph_value(row.get("source2_type", ""))).lower()
        shared_neighbor_type = str(_compact_graph_value(row.get("source1_out_neighbor_type", ""))).lower()
        source1_out_property = str(_compact_graph_value(row.get("source1_out_property", ""))).lower()
        source2_out_property = str(_compact_graph_value(row.get("source2_out_property", ""))).lower()
        type_values = (
            row.get("literal_node_type"),
            row.get("source1_type"),
            row.get("source1_out_neighbor_type"),
            row.get("source2_type"),
            row.get("source2_out_neighbor_type"),
        )
        ml_type_count = sum(1 for value in type_values if str(_compact_graph_value(value or "")).startswith("ml:"))
        important_bridge = "modelexecution" in source2_type or any(
            term in source2_out_property for term in ("executes", "hasdatainput", "hasdataoutput")
        )
        data_bridge = any(term in source1_out_property for term in ("hasdatainput", "hasdataoutput", "derivedfrom"))
        metric_bridge = any(term in shared_neighbor_type for term in ("metric", "accuracy", "loss", "precision", "recall"))
        numeric_literal = _looks_numeric_literal(row.get("literal_value"))
        return (
            0 if numeric_literal else 1,
            0 if data_bridge else 1,
            0 if "modelexecution" in source2_type else 1,
            0 if important_bridge else 1,
            1 if metric_bridge else 0,
            -ml_type_count,
            str(_compact_graph_value(row.get("source2", ""))),
            str(_compact_graph_value(row.get("source2_out_property", ""))),
        )

    patterns: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, Any], ...]] = set()
    for row in sorted(skeleton_rows, key=priority):
        if not row.get("source1") or not row.get("source2") or not row.get("source1_out_neighbor"):
            continue
        if not row.get("source2_out_property") or not row.get("source2_out_neighbor"):
            continue

        compacted = {
            "literal_node": _compact_graph_value(row.get("literal_node")),
            "literal_node_type": _compact_graph_value(row.get("literal_node_type")),
            "literal_property": _compact_graph_value(row.get("literal_property")),
            "literal_value": row.get("literal_value"),
            "literal_source": _compact_graph_value(row.get("source1")),
            "literal_source_type": _compact_graph_value(row.get("source1_type")),
            "source_to_literal_property": _compact_graph_value(row.get("source1_to_literal_property")),
            "shared_neighbor": _compact_graph_value(row.get("source1_out_neighbor")),
            "shared_neighbor_type": _compact_graph_value(row.get("source1_out_neighbor_type")),
            "source_to_shared_neighbor_property": _compact_graph_value(row.get("source1_out_property")),
            "bridge_node": _compact_graph_value(row.get("source2")),
            "bridge_node_type": _compact_graph_value(row.get("source2_type")),
            "bridge_to_shared_neighbor_property": _compact_graph_value(row.get("source2_to_neighbor_property")),
            "bridge_out_property": _compact_graph_value(row.get("source2_out_property")),
            "bridge_out_neighbor": _compact_graph_value(row.get("source2_out_neighbor")),
            "bridge_out_neighbor_type": _compact_graph_value(row.get("source2_out_neighbor_type")),
        }

        type_values = (
            compacted.get("literal_node_type"),
            compacted.get("literal_source_type"),
            compacted.get("shared_neighbor_type"),
            compacted.get("bridge_node_type"),
            compacted.get("bridge_out_neighbor_type"),
        )
        if all(_low_information_type(value) for value in type_values):
            continue

        signature = tuple(sorted(compacted.items()))
        if signature in seen:
            continue
        seen.add(signature)
        patterns.append(compacted)
        if len(patterns) >= limit:
            break
    return patterns


async def _query_term_matches(
    graphdb_client: GraphDBClient,
    repo: str,
    search_terms: list[str],
    *,
    per_term_limit: int = 30,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, term in enumerate(search_terms):
        term_literal = _sparql_string_literal(term)
        sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?matched_term ?term_rank ?node ?label ?type ?match_rank ?node_kind_rank WHERE {{
  BIND({term_literal} AS ?matched_term)
  BIND({index} AS ?term_rank)
  {{
    ?node rdfs:label|skos:prefLabel|skos:altLabel ?label .
    BIND(STR(?label) AS ?match_text)
  }}
  UNION
  {{
    ?node ?p ?o .
    BIND(IF(CONTAINS(STR(?node), "#"), STRAFTER(STR(?node), "#"), REPLACE(STR(?node), "^.*/", "")) AS ?label)
    BIND(STR(?label) AS ?match_text)
  }}
  FILTER(CONTAINS(LCASE(?match_text), LCASE(?matched_term)))
  BIND(
    IF(
      LCASE(?match_text) = LCASE(?matched_term),
      0,
      IF(
        STRSTARTS(LCASE(?match_text), LCASE(?matched_term)) || STRENDS(LCASE(?match_text), LCASE(?matched_term)),
        1,
        2
      )
    ) AS ?match_rank
  )
  OPTIONAL {{ ?node rdf:type ?type }}
  BIND(
    IF(
      ?type IN (owl:Class, rdfs:Class),
      0,
      IF(?type = owl:NamedIndividual, 1, 2)
    ) AS ?node_kind_rank
  )
}}
ORDER BY ?match_rank ?node_kind_rank ?node ?type
LIMIT {per_term_limit}
"""
        rows.extend(await graphdb_client.query(sparql, repo=repo, use_inference=False, show_upper_ontology=True))
    return rows


async def _query_lucene_term_matches(
    graphdb_client: GraphDBClient,
    repo: str,
    search_terms: list[str],
    *,
    per_term_limit: int = 30,
) -> list[dict[str, Any]]:
    connector = _graphdb_lucene_connector_name()
    if not connector:
        return []
    rows: list[dict[str, Any]] = []
    connector_iri = f"http://www.ontotext.com/connectors/lucene/instance/{connector}"
    for index, term in enumerate(search_terms):
        term_literal = _sparql_string_literal(term)
        lucene_query_literal = _sparql_string_literal(_lucene_query_for_term(term))
        sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX luc: <http://www.ontotext.com/connectors/lucene#>
SELECT DISTINCT ?matched_term ?term_rank ?node ?label ?type ?score ?match_rank ?node_kind_rank WHERE {{
  BIND({term_literal} AS ?matched_term)
  BIND({index} AS ?term_rank)
  BIND({lucene_query_literal} AS ?lucene_query)
  ?search a <{connector_iri}> ;
          luc:query ?lucene_query ;
          luc:entities ?node .
  OPTIONAL {{ ?node rdfs:label ?label }}
  OPTIONAL {{ ?node rdf:type ?type }}
  OPTIONAL {{ ?search luc:score ?score }}
  BIND(-1 AS ?match_rank)
  BIND(
    IF(
      ?type IN (owl:Class, rdfs:Class),
      0,
      IF(?type = owl:NamedIndividual, 1, 2)
    ) AS ?node_kind_rank
  )
}}
ORDER BY DESC(?score) ?node_kind_rank ?node ?type
LIMIT {per_term_limit}
"""
        rows.extend(await graphdb_client.query(sparql, repo=repo, use_inference=False, show_upper_ontology=True))
    return rows


async def _query_class_instances(
    graphdb_client: GraphDBClient,
    repo: str,
    class_nodes: list[str],
    *,
    limit: int = 180,
) -> list[dict[str, Any]]:
    values = _sparql_iri_values(class_nodes)
    if not values:
        return []
    instance_sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?class ?individual ?individual_label ?individual_type WHERE {{
  VALUES ?class {{ {values} }}
  ?individual rdf:type/rdfs:subClassOf* ?class .
  FILTER(isIRI(?individual))
  FILTER(?individual != ?class)
  OPTIONAL {{ ?individual rdfs:label ?individual_label }}
  OPTIONAL {{ ?individual rdf:type ?individual_type }}
}}
ORDER BY ?class ?individual ?individual_type
LIMIT {limit}
"""
    return await graphdb_client.query(instance_sparql, repo=repo, use_inference=False, show_upper_ontology=True)


async def _query_connection_paths(
    graphdb_client: GraphDBClient,
    repo: str,
    endpoint_nodes: list[str],
    *,
    limit: int = 180,
) -> list[dict[str, Any]]:
    values = _sparql_iri_values(endpoint_nodes)
    if not values:
        return []
    path_sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?start ?end ?path_shape ?p1 ?mid1 ?p2 ?mid2 ?p3 ?start_type ?end_type WHERE {{
  VALUES ?start {{ {values} }}
  VALUES ?end {{ {values} }}
  FILTER(?start != ?end)
  {{
    ?start ?p1 ?end .
    BIND("direct_out" AS ?path_shape)
  }}
  UNION
  {{
    ?end ?p1 ?start .
    BIND("direct_in" AS ?path_shape)
  }}
  UNION
  {{
    ?start ?p1 ?mid1 .
    ?mid1 ?p2 ?end .
    FILTER(isIRI(?mid1))
    BIND("out_out" AS ?path_shape)
  }}
  UNION
  {{
    ?start ?p1 ?mid1 .
    ?end ?p2 ?mid1 .
    FILTER(isIRI(?mid1))
    BIND("out_in" AS ?path_shape)
  }}
  UNION
  {{
    ?mid1 ?p1 ?start .
    ?mid1 ?p2 ?end .
    FILTER(isIRI(?mid1))
    BIND("in_out" AS ?path_shape)
  }}
  UNION
  {{
    ?mid1 ?p1 ?start .
    ?end ?p2 ?mid1 .
    FILTER(isIRI(?mid1))
    BIND("in_in" AS ?path_shape)
  }}
  UNION
  {{
    ?start ?p1 ?mid1 .
    ?mid2 ?p2 ?mid1 .
    ?mid2 ?p3 ?end .
    FILTER(isIRI(?mid1) && isIRI(?mid2))
    BIND("out_shared_in_out" AS ?path_shape)
  }}
  OPTIONAL {{ ?start a ?start_type }}
  OPTIONAL {{ ?end a ?end_type }}
  FILTER(!BOUND(?p1) || (?p1 NOT IN (rdf:type, rdfs:subClassOf)))
  FILTER(!BOUND(?p2) || (?p2 NOT IN (rdf:type, rdfs:subClassOf)))
  FILTER(!BOUND(?p3) || (?p3 NOT IN (rdf:type, rdfs:subClassOf)))
  FILTER(!BOUND(?mid1) || (?mid1 != ?start && ?mid1 != ?end))
  FILTER(!BOUND(?mid2) || (?mid2 != ?start && ?mid2 != ?end))
}}
LIMIT {limit}
"""
    return await graphdb_client.query(path_sparql, repo=repo, use_inference=False, show_upper_ontology=True)


def _expand_prefixed_name(term: str, ctx: dict) -> str | None:
    if ":" not in term:
        return None
    prefix, local = term.split(":", 1)
    namespace = dict(ctx.get("prefixes", {})).get(prefix)
    return f"{namespace}{local}" if namespace else None


def _extract_sparql_predicate_terms(sparql: str) -> list[str]:
    body = re.sub(r"(?m)^\s*PREFIX\s+.+$", "", sparql)
    body = "\n".join(line.split("#", 1)[0] for line in body.splitlines())
    terms: list[str] = []

    def add(term: str) -> None:
        if term not in terms:
            terms.append(term)

    for term in re.findall(r";\s*([\w-]+:[\w-]+)\s+", body):
        add(term)
    for term in re.findall(r"(?:^|[{\.\n]\s*)(?:\?\w+|<[^>]+>|[\w-]+:[\w-]+)\s+([\w-]+:[\w-]+)\s+", body):
        add(term)
    for term in re.findall(r"[/(|]\s*([\w-]+:[\w-]+)", body):
        add(term)
    return [term for term in terms if term not in {"rdf:type"}]


def _extract_sparql_class_terms(sparql: str) -> list[str]:
    body = re.sub(r"(?m)^\s*PREFIX\s+.+$", "", sparql)
    body = "\n".join(line.split("#", 1)[0] for line in body.splitlines())
    terms: list[str] = []
    for term in re.findall(r"(?:\ba\s+|\brdf:type(?:/rdfs:subClassOf[*+]?)?\s+)([\w-]+:[\w-]+)", body):
        if term not in terms:
            terms.append(term)
    return terms


def _row_count_value(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    value = rows[0].get("count") or rows[0].get("cnt") or rows[0].get("callret-0") or 0
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return 0


def _prefix_block_for_debug(sparql: str, ctx: dict) -> str:
    prefixes = dict(ctx.get("prefixes", {}))
    for prefix, namespace in re.findall(r"PREFIX\s+(\w[\w-]*):\s*<([^>]+)>", sparql, re.IGNORECASE):
        prefixes[prefix] = namespace
    defaults = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }
    for prefix, namespace in defaults.items():
        prefixes.setdefault(prefix, namespace)
    return "\n".join(f"PREFIX {prefix}: <{namespace}>" for prefix, namespace in sorted(prefixes.items()))


def _extract_where_body(sparql: str) -> str:
    match = re.search(r"\bWHERE\s*\{", sparql, re.IGNORECASE)
    if not match:
        return ""
    start = sparql.find("{", match.start())
    if start == -1:
        return ""
    depth = 0
    in_string = False
    quote_char = ""
    for index in range(start, len(sparql)):
        char = sparql[index]
        prev = sparql[index - 1] if index > 0 else ""
        if char in {"'", '"'} and prev != "\\":
            if in_string and char == quote_char:
                in_string = False
                quote_char = ""
            elif not in_string:
                in_string = True
                quote_char = char
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return sparql[start + 1:index]
    return sparql[start + 1:]


def _split_route_clauses(sparql: str) -> list[str]:
    body = _extract_where_body(sparql)
    clauses: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        clause = " ".join(part.strip() for part in buffer if part.strip()).strip()
        buffer.clear()
        if clause:
            clauses.append(clause)

    for raw_line in body.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line in {"{", "}"} or line.upper().startswith(("UNION", "OPTIONAL")):
            flush()
            continue
        if line.upper().startswith(("FILTER", "BIND")):
            flush()
            clauses.append(line.rstrip(".").strip())
            continue
        buffer.append(line)
        if line.endswith("."):
            flush()
    flush()
    return clauses


def _variables_in_clause(clause: str) -> list[str]:
    variables: list[str] = []
    for variable in re.findall(r"\?[A-Za-z_][A-Za-z0-9_]*", clause):
        if variable not in variables:
            variables.append(variable)
    return variables


def _coerce_numeric_filter_literals(sparql: str) -> str:
    def replace_var_left(match: re.Match[str]) -> str:
        variable, operator, number = match.groups()
        return f"FILTER(xsd:decimal({variable}) {operator} {number})"

    def replace_var_right(match: re.Match[str]) -> str:
        number, operator, variable = match.groups()
        return f"FILTER({number} {operator} xsd:decimal({variable}))"

    rewritten = re.sub(
        r"FILTER\s*\(\s*(\?[A-Za-z_][A-Za-z0-9_]*)\s*([<>]=?)\s*([-+]?\d+(?:\.\d+)?)\s*\)",
        replace_var_left,
        sparql,
        flags=re.IGNORECASE,
    )
    rewritten = re.sub(
        r"FILTER\s*\(\s*([-+]?\d+(?:\.\d+)?)\s*([<>]=?)\s*(\?[A-Za-z_][A-Za-z0-9_]*)\s*\)",
        replace_var_right,
        rewritten,
        flags=re.IGNORECASE,
    )
    return rewritten


async def _count_debug_pattern(
    graphdb_client: GraphDBClient,
    repo: str,
    prefix_block: str,
    clauses: list[str],
    *,
    use_inference: bool,
) -> int:
    if not clauses:
        return 0
    where_body = "\n  ".join(clauses)
    count_sparql = f"""
{prefix_block}
SELECT (COUNT(*) AS ?count) WHERE {{
  {where_body}
}}
"""
    rows = await graphdb_client.query(count_sparql, repo=repo, use_inference=use_inference)
    return _row_count_value(rows)


async def _sample_debug_variable(
    graphdb_client: GraphDBClient,
    repo: str,
    prefix_block: str,
    prior_clauses: list[str],
    variable: str,
    *,
    use_inference: bool,
    limit: int = 12,
) -> list[dict[str, Any]]:
    if not prior_clauses:
        return []
    where_body = "\n  ".join(prior_clauses)
    var_name = variable.lstrip("?")
    sample_sparql = f"""
{prefix_block}
SELECT DISTINCT {variable} ?{var_name}_type WHERE {{
  {where_body}
  OPTIONAL {{ {variable} rdf:type ?{var_name}_type }}
}}
LIMIT {limit}
"""
    rows = await graphdb_client.query(sample_sparql, repo=repo, use_inference=use_inference, show_upper_ontology=True)
    compact_rows = []
    for row in rows:
        compact_rows.append(
            {
                "value": _compact_graph_value(row.get(var_name)),
                "type": _compact_graph_value(row.get(f"{var_name}_type")),
            }
        )
    return compact_rows


async def _sample_debug_variable_neighborhood(
    graphdb_client: GraphDBClient,
    repo: str,
    prefix_block: str,
    prior_clauses: list[str],
    variable: str,
    *,
    use_inference: bool,
    limit: int = 24,
) -> list[dict[str, Any]]:
    if not prior_clauses:
        return []
    where_body = "\n  ".join(prior_clauses)
    var_name = variable.lstrip("?")
    neighborhood_sparql = f"""
{prefix_block}
SELECT DISTINCT {variable} ?direction ?property ?neighbor ?neighbor_type WHERE {{
  {{
    {where_body}
    {variable} ?property ?neighbor .
    FILTER(isIRI(?neighbor))
    OPTIONAL {{ ?neighbor rdf:type ?neighbor_type }}
    BIND("outgoing" AS ?direction)
  }}
  UNION
  {{
    {where_body}
    ?neighbor ?property {variable} .
    FILTER(isIRI(?neighbor))
    OPTIONAL {{ ?neighbor rdf:type ?neighbor_type }}
    BIND("incoming" AS ?direction)
  }}
}}
LIMIT {limit}
"""
    rows = await graphdb_client.query(neighborhood_sparql, repo=repo, use_inference=use_inference, show_upper_ontology=True)
    compact_rows = []
    for row in rows:
        compact_rows.append(
            {
                "value": _compact_graph_value(row.get(var_name)),
                "direction": row.get("direction"),
                "property": _compact_graph_value(row.get("property")),
                "neighbor": _compact_graph_value(row.get("neighbor")),
                "neighbor_type": _compact_graph_value(row.get("neighbor_type")),
            }
        )
    return compact_rows


async def _sample_debug_pivot_context(
    graphdb_client: GraphDBClient,
    repo: str,
    prefix_block: str,
    prior_clauses: list[str],
    variable: str,
    *,
    use_inference: bool,
    limit: int = 48,
) -> list[dict[str, Any]]:
    if not prior_clauses:
        return []
    where_body = "\n  ".join(prior_clauses)
    var_name = variable.lstrip("?")
    pivot_sparql = f"""
{prefix_block}
SELECT DISTINCT {variable} ?pivot ?pivot_to_bound_property ?pivot_property ?pivot_neighbor ?pivot_neighbor_type WHERE {{
  {{
    {where_body}
    ?pivot ?pivot_to_bound_property {variable} .
    FILTER(isIRI(?pivot))
  }}
  UNION
  {{
    {where_body}
    {variable} ?pivot_to_bound_property ?pivot .
    FILTER(isIRI(?pivot))
  }}
  ?pivot ?pivot_property ?pivot_neighbor .
  FILTER(isIRI(?pivot_neighbor))
  OPTIONAL {{ ?pivot_neighbor rdf:type ?pivot_neighbor_type }}
}}
LIMIT {limit}
"""
    rows = await graphdb_client.query(pivot_sparql, repo=repo, use_inference=use_inference, show_upper_ontology=True)
    compact_rows = []
    for row in rows:
        compact_rows.append(
            {
                "value": _compact_graph_value(row.get(var_name)),
                "pivot": _compact_graph_value(row.get("pivot")),
                "pivot_to_bound_property": _compact_graph_value(row.get("pivot_to_bound_property")),
                "pivot_property": _compact_graph_value(row.get("pivot_property")),
                "pivot_neighbor": _compact_graph_value(row.get("pivot_neighbor")),
                "pivot_neighbor_type": _compact_graph_value(row.get("pivot_neighbor_type")),
            }
        )
    return compact_rows


async def _debug_join_route(
    sparql: str,
    ctx: dict,
    graphdb_client: GraphDBClient,
    repo: str,
    *,
    use_inference: bool = False,
) -> dict[str, Any]:
    prefix_block = _prefix_block_for_debug(sparql, ctx)
    clauses = _split_route_clauses(sparql)
    join_clause_counts: list[dict[str, Any]] = []
    prior_clauses: list[str] = []
    first_zero_join: dict[str, Any] | None = None
    prior_variables: set[str] = set()

    for index, clause in enumerate(clauses, start=1):
        clause_entry: dict[str, Any] = {"index": index, "clause": clause}
        is_filter_or_bind = clause.upper().startswith(("FILTER", "BIND"))
        if not is_filter_or_bind:
            try:
                clause_entry["clause_count"] = await _count_debug_pattern(
                    graphdb_client,
                    repo,
                    prefix_block,
                    [clause],
                    use_inference=use_inference,
                )
            except Exception as exc:
                clause_entry["clause_error"] = str(exc)

        cumulative_clauses = [*prior_clauses, clause]
        try:
            cumulative_count = await _count_debug_pattern(
                graphdb_client,
                repo,
                prefix_block,
                cumulative_clauses,
                use_inference=use_inference,
            )
            clause_entry["cumulative_count"] = cumulative_count
        except Exception as exc:
            cumulative_count = 0
            clause_entry["cumulative_error"] = str(exc)

        previous_count = join_clause_counts[-1].get("cumulative_count") if join_clause_counts else None
        if first_zero_join is None and cumulative_count == 0:
            first_zero_join = {
                "index": index,
                "clause": clause,
                "previous_cumulative_count": previous_count,
                "cumulative_count": cumulative_count,
                "variables": _variables_in_clause(clause),
            }
        join_clause_counts.append(clause_entry)
        prior_clauses = cumulative_clauses
        prior_variables.update(_variables_in_clause(clause))

    variable_samples: dict[str, list[dict[str, Any]]] = {}
    variable_neighborhoods: dict[str, list[dict[str, Any]]] = {}
    pivot_contexts: dict[str, list[dict[str, Any]]] = {}
    if first_zero_join and first_zero_join["index"] > 1:
        supporting_prior_clauses = clauses[: first_zero_join["index"] - 1]
        supporting_variables = {variable for clause in supporting_prior_clauses for variable in _variables_in_clause(clause)}
        for variable in first_zero_join.get("variables", []):
            if variable not in supporting_variables:
                continue
            try:
                variable_samples[variable] = await _sample_debug_variable(
                    graphdb_client,
                    repo,
                    prefix_block,
                    supporting_prior_clauses,
                    variable,
                    use_inference=use_inference,
                )
            except Exception as exc:
                variable_samples[variable] = [{"error": str(exc)}]
            try:
                variable_neighborhoods[variable] = await _sample_debug_variable_neighborhood(
                    graphdb_client,
                    repo,
                    prefix_block,
                    supporting_prior_clauses,
                    variable,
                    use_inference=use_inference,
                )
            except Exception as exc:
                variable_neighborhoods[variable] = [{"error": str(exc)}]
            try:
                pivot_contexts[variable] = await _sample_debug_pivot_context(
                    graphdb_client,
                    repo,
                    prefix_block,
                    supporting_prior_clauses,
                    variable,
                    use_inference=use_inference,
                )
            except Exception as exc:
                pivot_contexts[variable] = [{"error": str(exc)}]

    return {
        "clauses": clauses,
        "join_clause_counts": join_clause_counts,
        "first_zero_join": first_zero_join,
        "variable_samples_at_collapse": variable_samples,
        "variable_neighborhoods_at_collapse": variable_neighborhoods,
        "pivot_contexts_at_collapse": pivot_contexts,
        "instruction": (
            "Use join_clause_counts to find the first cumulative join/filter that collapses to zero. "
            "Repair by replacing that clause or route with observed neighbors/paths from variable samples and graph observations."
        ),
    }


def _route_debug_repair_candidates(sparql: str, empty_debug: dict[str, Any]) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    numeric_cast = _coerce_numeric_filter_literals(sparql)
    if numeric_cast != sparql:
        candidates.append(("coerce_numeric_filter_literals", numeric_cast))
    candidates.extend(_class_constraint_bridge_repair_candidates(sparql, empty_debug))
    return candidates


def _class_constraint_bridge_repair_candidates(sparql: str, empty_debug: dict[str, Any]) -> list[tuple[str, str]]:
    route_debug = empty_debug.get("join_route_debug_after_numeric_cast") or empty_debug.get("join_route_debug") or {}
    first_zero = route_debug.get("first_zero_join") or {}
    clause = str(first_zero.get("clause") or "")
    match = re.match(
        r"^\s*(\?[A-Za-z_][A-Za-z0-9_]*)\s+(?:a|rdf:type(?:/rdfs:subClassOf[*+]?)?)\s+([\w-]+:[\w-]+)\s*\.?\s*$",
        clause,
    )
    if not match:
        return []

    variable, target_class = match.groups()
    neighborhoods = (route_debug.get("variable_neighborhoods_at_collapse") or {}).get(variable) or []
    bridge_hops = []
    for row in neighborhoods:
        if row.get("neighbor_type") != target_class:
            continue
        property_name = row.get("property")
        if not property_name or property_name == "rdf:type":
            continue
        direction = row.get("direction")
        if direction in {"outgoing", "incoming"}:
            bridge_hops.append((direction, property_name))
    if not bridge_hops:
        return []

    clauses = route_debug.get("clauses") or _split_route_clauses(sparql)
    try:
        zero_index = int(first_zero.get("index", 0))
    except (TypeError, ValueError):
        zero_index = 0
    prior_clauses = clauses[: max(0, zero_index - 1)] if zero_index else clauses
    binding_clause = ""
    for prior_clause in reversed(prior_clauses):
        if variable not in prior_clause:
            continue
        if prior_clause.upper().startswith(("FILTER", "BIND")) or "rdf:type" in prior_clause or " a " in prior_clause:
            continue
        binding_clause = prior_clause
        break
    if not binding_clause:
        return []

    bridge_variable = f"{variable}_bridge"
    candidates: list[tuple[str, str]] = []
    for direction, property_name in bridge_hops[:2]:
        rewritten_binding = re.sub(rf"{re.escape(variable)}\b", bridge_variable, binding_clause, count=1)
        if rewritten_binding == binding_clause:
            continue
        bridge_clause = (
            f"{bridge_variable} {property_name} {variable} ."
            if direction == "outgoing"
            else f"{variable} {property_name} {bridge_variable} ."
        )
        repaired = _replace_clause_with_bridge(sparql, binding_clause, rewritten_binding, bridge_clause)
        if repaired and repaired != sparql:
            candidates.append((f"bridge_class_constraint_via_{property_name}", repaired))
    return candidates


def _replace_clause_with_bridge(
    sparql: str,
    original_clause: str,
    rewritten_clause: str,
    bridge_clause: str,
) -> str | None:
    lines = sparql.splitlines()
    normalized_original = original_clause.strip().rstrip(".").strip()
    for index, line in enumerate(lines):
        code = line.split("#", 1)[0].strip().rstrip(".").strip()
        if code != normalized_original:
            continue
        indent = line[: len(line) - len(line.lstrip())]
        lines[index] = f"{indent}{rewritten_clause.rstrip('.') } ."
        lines.insert(index + 1, f"{indent}{bridge_clause}")
        return "\n".join(lines)

    pattern = re.escape(original_clause.strip())
    replacement = f"{rewritten_clause.rstrip('.')} .\n  {bridge_clause}"
    repaired, count = re.subn(pattern, replacement, sparql, count=1)
    return repaired if count else None


def _selected_variables_from_sparql(sparql: str, rows: list[dict[str, Any]]) -> list[str]:
    header_match = re.search(r"\bSELECT\b(.+?)\bWHERE\b", sparql, re.IGNORECASE | re.DOTALL)
    variables: list[str] = []
    if header_match:
        for variable in re.findall(r"\?([A-Za-z_][A-Za-z0-9_]*)", header_match.group(1)):
            if variable not in variables:
                variables.append(variable)
    if not variables and rows:
        variables = list(rows[0].keys())
    return variables


def _numeric_filter_variables_from_sparql(sparql: str) -> list[str]:
    variables: list[str] = []
    for filter_body in re.findall(r"FILTER\s*\((.*?)\)", sparql, re.IGNORECASE | re.DOTALL):
        if not re.search(r"[<>]=?\s*[-+]?\d|[-+]?\d(?:\.\d+)?\s*[<>]=?", filter_body):
            continue
        for variable in re.findall(r"\?([A-Za-z_][A-Za-z0-9_]*)", filter_body):
            if variable not in variables:
                variables.append(variable)
    return variables


def _required_answer_slots(question: str) -> list[str]:
    focused = current_question_text(question).lower()
    slots: list[str] = []

    def has_word(*words: str) -> bool:
        return any(re.search(rf"\b{re.escape(word)}\b", focused) for word in words)

    has_dataset_word = has_word("dataset", "datasets") or bool(re.search(r"\bdata\s+sets?\b", focused))
    if has_word("model", "models"):
        slots.append("model")
    if any(term in focused for term in ("performance", "accuracy", "score", "metric")):
        slots.append("performance_value")
    if has_word("test", "tests") and has_dataset_word:
        slots.append("test_dataset")
    elif has_dataset_word:
        slots.append("dataset")
    if has_word("pipeline", "pipelines", "process", "processes", "execution", "executions"):
        slots.append("pipeline")
    return slots


def _candidate_columns_for_slot(slot: str, selected_variables: list[str]) -> list[str]:
    lowered = {variable: variable.lower() for variable in selected_variables}
    if slot == "model":
        return [
            variable
            for variable, name in lowered.items()
            if "model" in name and "evaluation" not in name and "performance" not in name and "output" not in name
        ]
    if slot == "performance_value":
        return [
            variable
            for variable, name in lowered.items()
            if any(term in name for term in ("performance", "accuracy", "score", "value"))
        ]
    if slot in {"test_dataset", "dataset"}:
        return [variable for variable, name in lowered.items() if "dataset" in name or "data" in name]
    if slot == "pipeline":
        return [variable for variable, name in lowered.items() if any(term in name for term in ("pipeline", "process", "execution"))]
    return []


def _find_class_iri(ctx: dict, local_name: str) -> str | None:
    normalized = local_name.lower()
    for row in ctx.get("classes", []):
        iri = row.get("iri", "")
        if _local_name(iri).lower() == normalized:
            return iri
    prefix = dict(ctx.get("prefixes", {})).get("ml")
    return f"{prefix}{local_name}" if prefix else None


def _iri_sample_values(rows: list[dict[str, Any]], column: str, *, limit: int = 12) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = row.get(column)
        if isinstance(value, str) and value.startswith(("http://", "https://")) and value not in values:
            values.append(value)
        if len(values) >= limit:
            break
    return values


async def _sample_answer_column_types(
    graphdb_client: GraphDBClient,
    repo: str,
    values: list[str],
    *,
    use_inference: bool,
) -> list[dict[str, Any]]:
    if not values:
        return []
    value_block = _sparql_iri_values(values)
    sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?node ?type WHERE {{
  VALUES ?node {{ {value_block} }}
  OPTIONAL {{ ?node rdf:type ?type }}
}}
LIMIT 80
"""
    rows = await graphdb_client.query(sparql, repo=repo, use_inference=use_inference, show_upper_ontology=True)
    return [{"node": _compact_graph_value(row.get("node")), "type": _compact_graph_value(row.get("type"))} for row in rows]


async def _count_class_membership(
    graphdb_client: GraphDBClient,
    repo: str,
    values: list[str],
    class_iri: str | None,
    *,
    use_inference: bool,
) -> int:
    if not values or not class_iri:
        return 0
    value_block = _sparql_iri_values(values)
    sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT (COUNT(DISTINCT ?node) AS ?count) WHERE {{
  VALUES ?node {{ {value_block} }}
  ?node rdf:type/rdfs:subClassOf* <{class_iri}> .
}}
"""
    rows = await graphdb_client.query(sparql, repo=repo, use_inference=use_inference)
    return _row_count_value(rows)


async def _debug_answer_semantics(
    question: str,
    sparql: str,
    rows: list[dict[str, Any]],
    ctx: dict,
    graphdb_client: GraphDBClient,
    repo: str,
    *,
    use_inference: bool,
) -> dict[str, Any]:
    selected_variables = _selected_variables_from_sparql(sparql, rows)
    numeric_filter_variables = _numeric_filter_variables_from_sparql(sparql)
    required_slots = _required_answer_slots(question)
    failures: list[dict[str, Any]] = []
    slot_debug: dict[str, Any] = {}
    class_targets = {
        "model": _find_class_iri(ctx, "MachineLearningModel"),
        "test_dataset": _find_class_iri(ctx, "TestDataSet"),
    }

    for slot in required_slots:
        candidates = _candidate_columns_for_slot(slot, selected_variables)
        slot_entry: dict[str, Any] = {"candidate_columns": candidates}
        if not candidates:
            failures.append({"slot": slot, "reason": "missing_selected_column"})
            slot_debug[slot] = slot_entry
            continue

        non_null_candidates = [
            column
            for column in candidates
            if any(row.get(column) not in {None, ""} for row in rows[:20])
        ]
        slot_entry["non_null_candidate_columns"] = non_null_candidates
        if not non_null_candidates:
            failures.append({"slot": slot, "reason": "selected_columns_are_unbound"})
            slot_debug[slot] = slot_entry
            continue

        if slot in {"model", "test_dataset"}:
            class_iri = class_targets[slot]
            best_membership = 0
            best_column = None
            for column in non_null_candidates:
                sample_values = _iri_sample_values(rows, column)
                types = await _sample_answer_column_types(
                    graphdb_client,
                    repo,
                    sample_values,
                    use_inference=use_inference,
                )
                membership_count = await _count_class_membership(
                    graphdb_client,
                    repo,
                    sample_values,
                    class_iri,
                    use_inference=use_inference,
                )
                slot_entry.setdefault("columns", {})[column] = {
                    "sample_values": [_compact_graph_value(value) for value in sample_values],
                    "sample_types": types[:20],
                    "target_class": _compact_graph_value(class_iri),
                    "target_class_membership_count": membership_count,
                }
                if membership_count > best_membership:
                    best_membership = membership_count
                    best_column = column
            slot_entry["best_column"] = best_column
            if best_membership == 0:
                failures.append({"slot": slot, "reason": "selected_values_do_not_match_requested_class"})

        if slot == "performance_value":
            numeric_column = None
            for column in non_null_candidates:
                values = [row.get(column) for row in rows[:20]]
                if any(_looks_numeric_literal(value) for value in values):
                    numeric_column = column
                    break
            slot_entry["numeric_column"] = numeric_column
            slot_entry["numeric_filter_variables"] = numeric_filter_variables
            if numeric_column is None:
                failures.append({"slot": slot, "reason": "missing_numeric_result_column"})

        slot_debug[slot] = slot_entry

    return {
        "required_slots": required_slots,
        "selected_variables": selected_variables,
        "numeric_filter_variables": numeric_filter_variables,
        "failures": failures,
        "slot_debug": slot_debug,
        "instruction": (
            "A non-empty SPARQL result is still wrong if selected columns do not satisfy requested answer slots. "
            "Repair by selecting variables for missing slots and by routing values to the requested classes."
        ),
    }


def _looks_numeric_literal(value: Any) -> bool:
    if value is None:
        return False
    return bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", str(value)))


def _limit_debug_rows(rows: Any, limit: int) -> Any:
    if isinstance(rows, list):
        return rows[:limit]
    return rows


def _compact_join_route_debug_for_prompt(debug: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(debug, dict):
        return None
    first_zero = debug.get("first_zero_join") or {}
    first_zero_index = first_zero.get("index")
    clause_counts = debug.get("join_clause_counts") or []
    if isinstance(first_zero_index, int):
        selected_counts = []
        for row in clause_counts:
            try:
                row_index = int(row.get("index", 0))
            except (TypeError, ValueError):
                row_index = 0
            if row_index == 1 or abs(row_index - first_zero_index) <= 2:
                selected_counts.append(row)
    else:
        selected_counts = clause_counts[:8]

    compact_counts = []
    for row in selected_counts[:10]:
        compact_counts.append(
            {
                key: row[key]
                for key in ("index", "clause", "clause_count", "cumulative_count", "clause_error", "cumulative_error")
                if key in row
            }
        )

    def compact_debug_map(value: Any, limit: int) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {key: _limit_debug_rows(rows, limit) for key, rows in value.items()}

    return {
        "join_clause_counts": compact_counts,
        "first_zero_join": first_zero or None,
        "variable_samples_at_collapse": compact_debug_map(debug.get("variable_samples_at_collapse"), 8),
        "variable_neighborhoods_at_collapse": compact_debug_map(debug.get("variable_neighborhoods_at_collapse"), 10),
        "pivot_contexts_at_collapse": compact_debug_map(debug.get("pivot_contexts_at_collapse"), 12),
        "instruction": debug.get("instruction"),
    }


def _compact_empty_debug_for_prompt(debug: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(debug, dict):
        return None
    return {
        "predicate_counts": _limit_debug_rows(debug.get("predicate_counts") or [], 16),
        "class_counts": _limit_debug_rows(debug.get("class_counts") or [], 16),
        "zero_support_predicates": debug.get("zero_support_predicates") or [],
        "zero_support_classes": debug.get("zero_support_classes") or [],
        "join_route_debug": _compact_join_route_debug_for_prompt(debug.get("join_route_debug")),
        "numeric_filter_cast_candidate": debug.get("numeric_filter_cast_candidate"),
        "join_route_debug_after_numeric_cast": _compact_join_route_debug_for_prompt(debug.get("join_route_debug_after_numeric_cast")),
        "instruction": debug.get("instruction"),
    }


def _compact_answer_semantic_debug_for_prompt(debug: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(debug, dict):
        return None
    slot_debug = {}
    for slot, entry in (debug.get("slot_debug") or {}).items():
        if not isinstance(entry, dict):
            slot_debug[slot] = entry
            continue
        compact_entry = {
            key: entry[key]
            for key in ("candidate_columns", "non_null_candidate_columns", "best_column", "numeric_column", "numeric_filter_variables")
            if key in entry
        }
        columns = {}
        for column, column_entry in (entry.get("columns") or {}).items():
            if not isinstance(column_entry, dict):
                columns[column] = column_entry
                continue
            columns[column] = {
                "sample_values": _limit_debug_rows(column_entry.get("sample_values") or [], 6),
                "sample_types": _limit_debug_rows(column_entry.get("sample_types") or [], 8),
                "target_class": column_entry.get("target_class"),
                "target_class_membership_count": column_entry.get("target_class_membership_count"),
            }
        if columns:
            compact_entry["columns"] = columns
        slot_debug[slot] = compact_entry
    return {
        "required_slots": debug.get("required_slots") or [],
        "selected_variables": debug.get("selected_variables") or [],
        "numeric_filter_variables": debug.get("numeric_filter_variables") or [],
        "failures": debug.get("failures") or [],
        "slot_debug": slot_debug,
        "instruction": debug.get("instruction"),
    }


def _compact_repair_grounding_context(context: dict[str, Any]) -> dict[str, Any]:
    compacted = dict(context)
    graph_observations = compacted.get("graph_native_observations")
    if isinstance(graph_observations, dict):
        repair_limits = {
            "local_filter_by_string": 20,
            "graphdb_lucene_term_search": 12,
            "local_node_hops": 24,
            "class_seed_instances": 28,
            "class_instance_node_hops": 32,
            "individual_literal_properties": 28,
            "observed_bridge_patterns": 48,
            "observed_join_skeletons": 24,
            "candidate_connection_paths": 36,
        }
        compact_results = []
        for result in graph_observations.get("results", []):
            if not isinstance(result, dict):
                continue
            tool = result.get("tool")
            payload = result.get("payload") if isinstance(result.get("payload"), list) else []
            limit = repair_limits.get(str(tool), 20)
            compact_results.append(
                {
                    "tool": tool,
                    "row_count": result.get("row_count", len(payload)),
                    "payload": payload[:limit],
                }
            )
        compacted["graph_native_observations"] = {
            "search_term": graph_observations.get("search_term"),
            "search_terms": graph_observations.get("search_terms", []),
            "probe_strategy": graph_observations.get("probe_strategy", []),
            "results": compact_results,
        }
    if "sparql_empty_result_debug" in compacted:
        compacted["sparql_empty_result_debug"] = _compact_empty_debug_for_prompt(compacted.get("sparql_empty_result_debug"))
    if "answer_semantic_debug" in compacted:
        compacted["answer_semantic_debug"] = _compact_answer_semantic_debug_for_prompt(compacted.get("answer_semantic_debug"))
    return compacted


def _numeric_threshold_from_text(*texts: str) -> str | None:
    for text in texts:
        for pattern in (
            r"(?:more than|greater than|above|over|>)\s*([-+]?\d+(?:\.\d+)?)",
            r"FILTER\s*\([^)]*[<>]=?\s*([-+]?\d+(?:\.\d+)?)",
        ):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
    return None


def _observed_bridge_answer_candidates(
    question: str,
    sparql: str,
    grounding_context: dict[str, Any],
    ctx: dict,
) -> list[tuple[str, str]]:
    graph_observations = (grounding_context or {}).get("graph_native_observations") or {}
    bridge_rows: list[dict[str, Any]] = []
    for result in graph_observations.get("results", []):
        if result.get("tool") == "observed_bridge_patterns" and isinstance(result.get("payload"), list):
            bridge_rows.extend(result["payload"])
    if not bridge_rows:
        return []

    required_slots = set(_required_answer_slots(question))
    if not {"performance_value", "model", "pipeline"}.issubset(required_slots):
        return []
    dataset_slot = "test_dataset" if "test_dataset" in required_slots else "dataset" if "dataset" in required_slots else None
    if not dataset_slot:
        return []

    def is_model_row(row: dict[str, Any]) -> bool:
        neighbor_type = str(row.get("bridge_out_neighbor_type", "")).lower()
        neighbor = str(row.get("bridge_out_neighbor", "")).lower()
        prop = str(row.get("bridge_out_property", "")).lower()
        return "model" in neighbor_type or "model" in neighbor or "executes" in prop

    def is_dataset_row(row: dict[str, Any]) -> bool:
        neighbor_type = str(row.get("bridge_out_neighbor_type", "")).lower()
        neighbor = str(row.get("bridge_out_neighbor", "")).lower()
        return "dataset" in neighbor_type or "dataset" in neighbor

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in bridge_rows:
        key = (
            row.get("literal_property"),
            row.get("source_to_literal_property"),
            row.get("source_to_shared_neighbor_property"),
            row.get("bridge_to_shared_neighbor_property"),
            row.get("bridge_node_type"),
        )
        if all(key):
            groups.setdefault(key, []).append(row)

    threshold = _numeric_threshold_from_text(question, sparql) or "0"
    prefix_map = dict(ctx.get("prefixes", {}))
    ml_prefix = prefix_map.get("ml", "http://www.semanticweb.org/mnd14/ml/")
    prefixes = {
        "ml": ml_prefix,
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }
    for row in bridge_rows:
        for value in row.values():
            if isinstance(value, str) and ":" in value:
                prefix = value.split(":", 1)[0]
                if prefix in prefix_map:
                    prefixes[prefix] = prefix_map[prefix]
    prefix_block = "\n".join(f"PREFIX {prefix}: <{namespace}>" for prefix, namespace in sorted(prefixes.items()))

    candidates: list[tuple[str, str]] = []
    for rows in groups.values():
        model_row = next((row for row in rows if is_model_row(row)), None)
        dataset_row = next((row for row in rows if is_dataset_row(row)), None)
        evidence_row = model_row or dataset_row or rows[0]
        if not model_row or not dataset_row:
            continue
        literal_property = evidence_row.get("literal_property")
        source_to_literal_property = evidence_row.get("source_to_literal_property")
        source_to_shared_property = evidence_row.get("source_to_shared_neighbor_property")
        bridge_to_shared_property = evidence_row.get("bridge_to_shared_neighbor_property")
        model_property = model_row.get("bridge_out_property")
        dataset_property = dataset_row.get("bridge_out_property")
        if not all((literal_property, source_to_literal_property, source_to_shared_property, bridge_to_shared_property, model_property, dataset_property)):
            continue

        model_class = _find_class_iri(ctx, "MachineLearningModel")
        dataset_class = _find_class_iri(ctx, "TestDataSet") if dataset_slot == "test_dataset" else None
        model_constraint = "  ?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel .\n" if model_class and model_class.startswith(ml_prefix) else ""
        dataset_constraint = "  ?test_dataset rdf:type/rdfs:subClassOf* ml:TestDataSet .\n" if dataset_class and dataset_class.startswith(ml_prefix) else ""
        candidate = f"""{prefix_block}
SELECT DISTINCT ?model ?performance_value ?test_dataset ?pipeline WHERE {{
  ?performance_result {literal_property} ?performance_value .
  FILTER(xsd:decimal(?performance_value) > {threshold})
  ?literal_source {source_to_literal_property} ?performance_result .
  ?literal_source {source_to_shared_property} ?shared_artifact .
  ?pipeline {bridge_to_shared_property} ?shared_artifact .
  ?pipeline {model_property} ?model .
{model_constraint}  ?pipeline {dataset_property} ?test_dataset .
{dataset_constraint}}}
LIMIT 100"""
        if candidate not in [existing for _, existing in candidates]:
            candidates.append(("observed_bridge_answer_synthesis", candidate))
    return candidates[:2]


def _property_iri_by_local_name(ctx: dict, local_name: str) -> str | None:
    target = local_name.lower()
    for section in ("object_properties", "datatype_properties", "annotation_properties"):
        for row in ctx.get(section, []) or []:
            iri = row.get("iri")
            if isinstance(iri, str) and _local_name(iri).lower() == target:
                return iri
    prefix = dict(ctx.get("prefixes", {})).get("ml")
    return f"{prefix}{local_name}" if prefix else None


def _sparql_iri(value: str) -> str:
    return f"<{value}>" if value.startswith(("http://", "https://")) else value


def _observed_seed_iris(observations: dict[str, Any] | None) -> list[str]:
    seeds: list[str] = []
    for tool, row in _iter_observation_rows(observations):
        if tool not in {"local_filter_by_string", "graphdb_lucene_term_search"}:
            continue
        node = row.get("node")
        if not isinstance(node, str) or not node.startswith(("http://", "https://")):
            continue
        if row.get("type") in {OWL_CLASS_IRI, RDFS_CLASS_IRI, OWL_ANNOTATION_PROPERTY_IRI, OWL_ONTOLOGY_IRI}:
            continue
        try:
            match_rank = int(float(str(row.get("match_rank", 9))))
        except (TypeError, ValueError):
            match_rank = 9
        if match_rank > 0:
            continue
        if node not in seeds:
            seeds.append(node)
    return seeds[:6]


def _relation_local(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _local_name(value).lower())


def _is_upstream_question(question: str) -> bool:
    focused = current_question_text(question).lower()
    return any(term in focused for term in ("upstream", "lineage", "source", "origin", "create", "created", "make", "made", "from", "used to"))


def _is_downstream_question(question: str) -> bool:
    focused = current_question_text(question).lower()
    return any(term in focused for term in ("downstream", "consume", "consumed", "use", "uses", "used by", "artifact"))


def _is_source_relation(property_iri: Any) -> bool:
    local = _relation_local(property_iri)
    return any(term in local for term in ("derivedfrom", "source", "input", "origin", "basedon", "generatedfrom"))


def _is_input_relation(property_iri: Any) -> bool:
    local = _relation_local(property_iri)
    return "input" in local or "consume" in local or "uses" in local


def _is_output_relation(property_iri: Any) -> bool:
    local = _relation_local(property_iri)
    return "output" in local or "produce" in local or "create" in local or "generated" in local


def _observed_node_hop_answer_candidates(
    question: str,
    observations: dict[str, Any] | None,
    ctx: dict,
) -> list[tuple[str, str]]:
    seed_iris = _observed_seed_iris(observations)
    if not seed_iris:
        return []
    hop_rows = [row for tool, row in _iter_observation_rows(observations) if tool in {"local_node_hops", "class_instance_node_hops"}]
    if not hop_rows:
        return []

    rdf_prefix = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    prefix_block = f"PREFIX rdf: <{rdf_prefix}>"
    has_input = _property_iri_by_local_name(ctx, "hasDataInput")
    has_output = _property_iri_by_local_name(ctx, "hasDataOutput")
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(reason: str, sparql: str) -> None:
        if sparql not in seen:
            candidates.append((reason, sparql))
            seen.add(sparql)

    wants_upstream = _is_upstream_question(question)
    wants_downstream = _is_downstream_question(question)

    for seed in seed_iris:
        seed_term = _sparql_iri(seed)
        if wants_upstream:
            for row in hop_rows:
                if row.get("seed") != seed or row.get("direction") != "outgoing":
                    continue
                property_iri = row.get("property")
                if not isinstance(property_iri, str) or not property_iri.startswith(("http://", "https://")):
                    continue
                if not _is_source_relation(property_iri):
                    continue
                add(
                    f"observed_upstream_direct_{_local_name(property_iri)}",
                    f"""{prefix_block}
SELECT DISTINCT ?source ?source_type WHERE {{
  {seed_term} <{property_iri}> ?source .
  FILTER(isIRI(?source))
  OPTIONAL {{ ?source rdf:type ?source_type }}
}}
LIMIT 100""",
                )
            if has_input:
                for row in hop_rows:
                    if row.get("seed") != seed or row.get("direction") != "incoming":
                        continue
                    property_iri = row.get("property")
                    process = row.get("neighbor")
                    if not isinstance(process, str) or not process.startswith(("http://", "https://")):
                        continue
                    if not isinstance(property_iri, str) or not _is_output_relation(property_iri):
                        continue
                    add(
                        "observed_upstream_process_inputs",
                        f"""{prefix_block}
SELECT DISTINCT ?process ?source ?source_type WHERE {{
  ?process <{property_iri}> {seed_term} .
  ?process <{has_input}> ?source .
  FILTER(isIRI(?source))
  OPTIONAL {{ ?source rdf:type ?source_type }}
}}
LIMIT 100""",
                    )
                    break

        if wants_downstream:
            for row in hop_rows:
                if row.get("seed") != seed or row.get("direction") != "incoming":
                    continue
                property_iri = row.get("property")
                if not isinstance(property_iri, str) or not property_iri.startswith(("http://", "https://")):
                    continue
                if _is_input_relation(property_iri) and has_output:
                    add(
                        "observed_downstream_process_outputs",
                        f"""{prefix_block}
SELECT DISTINCT ?process ?downstream_artifact ?downstream_artifact_type WHERE {{
  ?process <{property_iri}> {seed_term} .
  ?process <{has_output}> ?downstream_artifact .
  FILTER(isIRI(?downstream_artifact))
  OPTIONAL {{ ?downstream_artifact rdf:type ?downstream_artifact_type }}
}}
LIMIT 100""",
                    )
                if _is_source_relation(property_iri):
                    add(
                        f"observed_downstream_direct_{_local_name(property_iri)}",
                        f"""{prefix_block}
SELECT DISTINCT ?downstream_artifact ?downstream_artifact_type WHERE {{
  ?downstream_artifact <{property_iri}> {seed_term} .
  FILTER(isIRI(?downstream_artifact))
  OPTIONAL {{ ?downstream_artifact rdf:type ?downstream_artifact_type }}
}}
LIMIT 100""",
                    )
    return candidates[:6]


async def _debug_empty_sparql(
    sparql: str,
    ctx: dict,
    graphdb_client: GraphDBClient,
    repo: str,
    *,
    use_inference: bool = False,
) -> dict[str, Any]:
    predicate_counts = []
    for term in _extract_sparql_predicate_terms(sparql)[:24]:
        iri = _expand_prefixed_name(term, ctx)
        if not iri:
            continue
        count_sparql = f"""
SELECT (COUNT(*) AS ?count) WHERE {{
  ?s <{iri}> ?o .
}}
"""
        try:
            rows = await graphdb_client.query(count_sparql, repo=repo, use_inference=use_inference)
            predicate_counts.append({"term": term, "count": _row_count_value(rows)})
        except Exception as exc:
            predicate_counts.append({"term": term, "error": str(exc)})

    class_counts = []
    for term in _extract_sparql_class_terms(sparql)[:24]:
        iri = _expand_prefixed_name(term, ctx)
        if not iri:
            continue
        count_sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT (COUNT(*) AS ?count) WHERE {{
  ?s rdf:type/rdfs:subClassOf* <{iri}> .
}}
"""
        try:
            rows = await graphdb_client.query(count_sparql, repo=repo, use_inference=use_inference)
            class_counts.append({"term": term, "count": _row_count_value(rows)})
        except Exception as exc:
            class_counts.append({"term": term, "error": str(exc)})

    numeric_cast_sparql = _coerce_numeric_filter_literals(sparql)
    join_route_debug = await _debug_join_route(
        sparql,
        ctx,
        graphdb_client,
        repo,
        use_inference=use_inference,
    )
    numeric_cast_join_route_debug = None
    if numeric_cast_sparql != sparql:
        numeric_cast_join_route_debug = await _debug_join_route(
            numeric_cast_sparql,
            ctx,
            graphdb_client,
            repo,
            use_inference=use_inference,
        )

    return {
        "predicate_counts": predicate_counts,
        "class_counts": class_counts,
        "zero_support_predicates": [row["term"] for row in predicate_counts if row.get("count") == 0],
        "zero_support_classes": [row["term"] for row in class_counts if row.get("count") == 0],
        "join_route_debug": join_route_debug,
        "numeric_filter_cast_candidate": numeric_cast_sparql if numeric_cast_sparql != sparql else None,
        "join_route_debug_after_numeric_cast": numeric_cast_join_route_debug,
        "instruction": "If a generated query returns zero rows, prefer exact observed join skeletons and avoid predicates/classes with zero support unless another observed row explicitly requires them.",
    }


async def _run_safe_graph_native_probe(question: str, repo: str, graphdb_client: GraphDBClient | None = None) -> dict[str, Any]:
    from mllo_web.core.tools.graph_native import filter_by_string_tool, list_all_classes_tool

    search_terms = _search_terms_from_question(question)
    search_term = search_terms[0] if search_terms else ""
    observations: dict[str, Any] = {
        "search_term": search_term,
        "search_terms": search_terms,
        "probe_strategy": [
            "approximate_term_match_to_candidate_iris",
            "optional_graphdb_lucene_full_text_match_to_candidate_iris",
            "inspect_seed_hops",
            "expand_class_seeds_to_individuals",
            "inspect_individual_hops",
            "inspect_literal_tables_for_selected_individuals",
            "distill_exact_observed_join_skeletons_around_literal_values",
            "find_short_connection_paths_between_selected_nodes",
        ],
        "results": [],
    }
    if graphdb_client is not None and search_terms:
        node_rows = await _query_term_matches(graphdb_client, repo, search_terms)
        observations["results"].append({"tool": "local_filter_by_string", "payload": node_rows})
        fts_rows: list[dict[str, Any]] = []
        if _graphdb_lucene_connector_name():
            try:
                fts_rows = await _query_lucene_term_matches(graphdb_client, repo, search_terms)
                observations["results"].append({"tool": "graphdb_lucene_term_search", "payload": fts_rows})
            except Exception as exc:
                logger.info("GraphDB Lucene term search failed; continuing with string matches: %s", exc)
                observations["results"].append({"tool": "graphdb_lucene_term_search_error", "payload": [{"error": str(exc)}]})
        candidate_rows = [*node_rows, *fts_rows]
        seed_nodes = _ranked_nodes_by_term(candidate_rows, search_terms, predicate=_is_probe_seed_row, per_term=3, total=24)
        seed_hop_rows: list[dict[str, Any]] = []
        if seed_nodes:
            seed_hop_rows = await _query_node_hops(graphdb_client, repo, seed_nodes)
            observations["results"].append(
                {
                    "tool": "local_node_hops",
                    "payload": seed_hop_rows,
                }
            )
        class_seed_nodes = _ranked_nodes_by_term(candidate_rows, search_terms, predicate=_is_class_row, per_term=12, total=64)
        instance_rows = await _query_class_instances(graphdb_client, repo, class_seed_nodes) if class_seed_nodes else []
        instance_nodes: list[str] = []
        instance_hop_rows: list[dict[str, Any]] = []
        if instance_rows:
            observations["results"].append({"tool": "class_seed_instances", "payload": instance_rows})
            instance_nodes = _ranked_instance_nodes_by_class(instance_rows, class_seed_nodes, per_class=5, total=48)
            if instance_nodes:
                instance_hop_rows = await _query_node_hops(graphdb_client, repo, instance_nodes, limit=220)
                observations["results"].append(
                    {
                        "tool": "class_instance_node_hops",
                        "payload": instance_hop_rows,
                    }
                )
        individual_seed_nodes = _ranked_nodes_by_term(candidate_rows, search_terms, predicate=_is_individualish_row, per_term=4, total=36)
        literal_seed_nodes: list[str] = []
        seen_literal_seed_nodes: set[str] = set()
        for node in [*individual_seed_nodes, *instance_nodes]:
            if node not in seen_literal_seed_nodes:
                literal_seed_nodes.append(node)
                seen_literal_seed_nodes.add(node)
            if len(literal_seed_nodes) >= 50:
                break
        for row in [*seed_hop_rows, *instance_hop_rows]:
            neighbor = row.get("neighbor")
            neighbor_type = row.get("neighbor_type")
            if neighbor and neighbor_type not in {OWL_CLASS_IRI, RDFS_CLASS_IRI, OWL_ANNOTATION_PROPERTY_IRI, OWL_ONTOLOGY_IRI} and neighbor not in seen_literal_seed_nodes:
                literal_seed_nodes.append(neighbor)
                seen_literal_seed_nodes.add(neighbor)
            if len(literal_seed_nodes) >= 80:
                break
        literal_rows = await _query_literal_properties(graphdb_client, repo, literal_seed_nodes) if literal_seed_nodes else []
        if literal_rows:
            observations["results"].append({"tool": "individual_literal_properties", "payload": literal_rows})
            skeleton_seed_nodes = _literal_seed_nodes_for_skeletons(literal_rows)
            skeleton_rows = await _query_observed_join_skeletons(graphdb_client, repo, skeleton_seed_nodes) if skeleton_seed_nodes else []
            if skeleton_rows:
                bridge_pattern_rows = _observed_bridge_pattern_rows(skeleton_rows)
                if bridge_pattern_rows:
                    observations["results"].append({"tool": "observed_bridge_patterns", "payload": bridge_pattern_rows})
                observations["results"].append({"tool": "observed_join_skeletons", "payload": skeleton_rows})
        endpoint_source_nodes = [*individual_seed_nodes, *instance_nodes] or seed_nodes
        endpoint_nodes = []
        seen_endpoint_nodes: set[str] = set()
        for node in endpoint_source_nodes:
            if node not in seen_endpoint_nodes:
                endpoint_nodes.append(node)
                seen_endpoint_nodes.add(node)
            if len(endpoint_nodes) >= 36:
                break
        connection_rows = await _query_connection_paths(graphdb_client, repo, endpoint_nodes) if len(endpoint_nodes) >= 2 else []
        if connection_rows:
            observations["results"].append({"tool": "candidate_connection_paths", "payload": connection_rows})
        return observations
    for term in search_terms[:3]:
        lookup = await filter_by_string_tool(term, repo=repo)
        observations["results"].append({"tool": "filter_by_string", "search_term": term, "payload": lookup})
    if not observations["results"]:
        classes = await list_all_classes_tool(repo=repo)
        observations["results"].append({"tool": "list_all_classes", "payload": classes})
    return observations


async def _initialize_context(state: NLQGraphState) -> dict[str, Any]:
    settings = state["settings"]
    graphdb_client = state["graphdb_client"]
    resolved_repo = await graphdb_client.validate_repo(state.get("requested_repo") or settings.graphdb_default_repo)
    query_state = NLQQueryState(question=state["question"], repo=resolved_repo)
    query_state.set_artifact(
        "orchestration",
        {
            "engine": "langgraph",
            "langgraph_available": StateGraph is not None,
            "pydantic_ai_available": _pydantic_ai_available(),
            "max_graph_iterations": MAX_GRAPH_ITERATIONS,
            "max_sparql_repairs": MAX_SPARQL_REPAIRS,
            "force_custom_sparql": state.get("force_custom_sparql", False),
            "custom_sparql_enhanced_prompt": state.get("custom_sparql_enhanced_prompt", False),
        },
    )
    return {
        "resolved_repo": resolved_repo,
        "resolved_answer_mode": state.get("requested_answer_mode") or settings.answer_mode,
        "query_state": query_state,
        "graph_iterations": 0,
        "repair_attempts": 0,
    }


async def _plan_action(state: NLQGraphState) -> dict[str, Any]:
    question = state["question"]
    gateway = state["gateway"]
    settings = state["settings"]
    query_state = state["query_state"]
    intent = await classify_intent(question, gateway, active_provider_config(settings))
    use_inference = _answer_mode_inference(state["resolved_answer_mode"], intent)
    query_state.set_artifact("intent", intent.model_dump())
    query_state.set_artifact(
        "planner",
        {
            "adapter": "pydantic_ai_contract",
            "pydantic_ai_available": _pydantic_ai_available(),
            "note": "Planner actions are validated through Pydantic models; MLLE LLMGateway remains the provider transport.",
        },
    )

    if state.get("force_custom_sparql", False):
        action = PydanticAIPlannerAdapter.validate_action(
            {
                "action": "graph_native_tool",
                "tool": "safe_ontology_probe",
                "params": {"search_term": _search_term_from_question(question), "force_custom_sparql": True},
                "reasoning": "Forced custom SPARQL mode bypasses deterministic routes.",
            }
        )
    elif lineage_query_spec(question):
        action = PydanticAIPlannerAdapter.validate_action(
            {
                "action": "structured_tool",
                "tool": "lineage",
                "params": {"question": question},
                "reasoning": "Lineage/provenance wording maps to the deterministic lineage graph node.",
            }
        )
    elif performance_query_spec(question):
        action = PydanticAIPlannerAdapter.validate_action(
            {
                "action": "structured_tool",
                "tool": "performance",
                "params": {"question": question},
                "reasoning": "Metric/ranking wording maps to the deterministic performance graph node.",
            }
        )
    elif intent.tool in STRUCTURED_TOOLS:
        action = PydanticAIPlannerAdapter.validate_action(
            {
                "action": "structured_tool",
                "tool": intent.tool,
                "params": intent.params,
                "reasoning": intent.reasoning,
            }
        )
    else:
        action = PydanticAIPlannerAdapter.validate_action(
            {
                "action": "graph_native_tool",
                "tool": "safe_ontology_probe",
                "params": {"search_term": _search_term_from_question(question)},
                "reasoning": "Ambiguous/custom question: inspect ontology context before custom SPARQL generation.",
            }
        )

    query_state.add_plan_step(tool=action.tool or action.action, params=action.params, reasoning=action.reasoning)
    query_state.set_artifact("planner_action", action.model_dump())
    return {
        "intent": intent,
        "use_inference": use_inference,
        "action": action,
        "query_state": query_state,
        "graph_iterations": state.get("graph_iterations", 0) + 1,
    }


def _route_after_plan(state: NLQGraphState) -> str:
    action = state["action"].action
    if state.get("graph_iterations", 0) > MAX_GRAPH_ITERATIONS:
        return "cannot_answer"
    if action == "structured_tool":
        return "structured"
    if action == "graph_native_tool":
        return "graph_native"
    if action == "custom_sparql":
        return "custom_sparql"
    if action == "cannot_answer":
        return "cannot_answer"
    return "custom_sparql"


async def _execute_structured_node(state: NLQGraphState) -> dict[str, Any]:
    from mllo_web.core.workflows.nlq import _execute_structured_tool

    action = state["action"]
    intent = state["intent"]
    query_state = state["query_state"]
    resolved_repo = state["resolved_repo"]
    graphdb_client = state["graphdb_client"]

    if action.tool == "lineage":
        execution = await execute_lineage_orchestration(
            question=state["question"],
            resolved_repo=resolved_repo,
            state=query_state,
            graphdb_client=graphdb_client,
            payload_type=NLQExecutionPayload,
        )
        return {"execution": execution, "query_state": execution.state}

    if action.tool == "performance":
        execution = await execute_performance_orchestration(
            question=state["question"],
            resolved_repo=resolved_repo,
            state=query_state,
            graphdb_client=graphdb_client,
            payload_type=NLQExecutionPayload,
        )
        return {"execution": execution, "query_state": execution.state}

    sparql, results = await _execute_structured_tool(intent, resolved_repo, state["use_inference"], graphdb_client)
    query_state.add_step(
        tool=intent.tool,
        params=intent.params,
        sparql=sparql,
        results=results,
        inference_used=state["use_inference"],
        reasoning=intent.reasoning,
    )
    return {
        "execution": NLQExecutionPayload(
            sparql=sparql,
            results=results,
            inference_used=state["use_inference"],
            state=query_state,
        ),
        "query_state": query_state,
    }


async def _execute_graph_native_node(state: NLQGraphState) -> dict[str, Any]:
    query_state = state["query_state"]
    action = state["action"]
    try:
        observations = await _run_safe_graph_native_probe(state["question"], state["resolved_repo"], state["graphdb_client"])
        query_state.set_artifact("graph_native_observations", observations)
        query_state.add_step(
            tool=action.tool or "safe_ontology_probe",
            params=action.params,
            results=observations.get("results", []),
            inference_used=False,
            reasoning=action.reasoning,
        )
    except Exception as exc:
        logger.info("Graph-native probe failed; continuing with custom SPARQL: %s", exc)
        query_state.set_artifact("graph_native_probe_error", str(exc))

    custom_action = PydanticAIPlannerAdapter.validate_action(
        {
            "action": "custom_sparql",
            "tool": "custom_sparql",
            "params": state["intent"].params or {"question": state["question"]},
            "reasoning": "Use graph-native observations as grounding context, then generate custom SPARQL.",
        }
    )
    query_state.add_plan_step(tool="custom_sparql", params=custom_action.params, reasoning=custom_action.reasoning)
    return {
        "action": custom_action,
        "query_state": query_state,
        "graph_iterations": state.get("graph_iterations", 0) + 1,
    }


async def _execute_custom_sparql_node(state: NLQGraphState) -> dict[str, Any]:
    settings = state["settings"]
    gateway = state["gateway"]
    graphdb_client = state["graphdb_client"]
    query_state = state["query_state"]
    intent = state["intent"]
    question = state["question"]
    resolved_repo = state["resolved_repo"]
    use_inference = state["use_inference"]
    raw_graph_native_observations = query_state.get_artifact("graph_native_observations")
    graph_native_observations = _compact_graph_observations_for_prompt(raw_graph_native_observations)
    query_state.set_artifact("graph_native_observations_prompt", graph_native_observations)
    canonical_iris = _canonical_iris_from_graph_observations(raw_graph_native_observations)
    if canonical_iris:
        query_state.set_artifact(
            "custom_sparql_observed_canonical_iris",
            {local: _compact_graph_value(iri) for local, iri in sorted(canonical_iris.items())[:80]},
        )
    enhanced_prompt = state.get("custom_sparql_enhanced_prompt", False)
    bridge_grounding = await schema_bridge_grounding(question, graphdb_client, resolved_repo) if enhanced_prompt else {}
    prompt_mode = "enhanced_schema_grounding" if enhanced_prompt else "pure_node_hops"
    query_state.set_artifact("custom_sparql_prompt_mode", prompt_mode)
    if enhanced_prompt and bridge_grounding:
        query_state.set_artifact("schema_bridge_grounding", bridge_grounding)
    grounding_context = {
        "prompt_mode": prompt_mode,
        "graph_native_observations": graph_native_observations,
    }
    if enhanced_prompt and bridge_grounding:
        grounding_context["schema_bridge_grounding"] = bridge_grounding
    sparql, ctx = await generate_sparql(
        intent.params.get("question") or current_question_text(question),
        resolved_repo,
        settings,
        graphdb_client,
        gateway,
        grounding_context=grounding_context,
        enhanced_prompt=enhanced_prompt,
    )

    should_validate_answer_semantics = (
        state.get("force_custom_sparql", False)
        and not enhanced_prompt
        and bool((graph_native_observations or {}).get("results"))
    )

    async def answer_semantic_failure(
        current_sparql: str,
        current_results: list[dict[str, Any]],
        artifact_suffix: str,
    ) -> dict[str, Any] | None:
        if not should_validate_answer_semantics or not current_results:
            return None
        try:
            debug = await _debug_answer_semantics(
                question,
                current_sparql,
                current_results,
                ctx,
                graphdb_client,
                resolved_repo,
                use_inference=use_inference,
            )
            query_state.set_artifact(f"sparql_answer_semantic_debug_{artifact_suffix}", debug)
        except Exception as exc:
            query_state.set_artifact(f"sparql_answer_semantic_debug_error_{artifact_suffix}", str(exc))
            return None
        return debug if debug.get("failures") else None

    def successful_execution(current_sparql: str, current_results: list[dict[str, Any]], repair_attempt: int) -> dict[str, Any]:
        query_state.add_step(
            tool="custom_sparql",
            params=intent.params,
            sparql=current_sparql,
            results=current_results,
            inference_used=use_inference,
            reasoning=intent.reasoning,
        )
        query_state.set_artifact("sparql_repair_attempts", repair_attempt)
        return {
            "execution": NLQExecutionPayload(
                sparql=current_sparql,
                results=current_results,
                inference_used=use_inference,
                state=query_state,
            ),
            "query_state": query_state,
            "repair_attempts": repair_attempt,
        }

    def apply_observed_canonical_iris(current_sparql: str, artifact_suffix: str) -> str:
        rewritten, replacements = _canonicalize_sparql_iri_constants(current_sparql, canonical_iris)
        if replacements:
            query_state.set_artifact(
                f"sparql_canonical_iri_rewrite_{artifact_suffix}",
                {"replacements": replacements, "sparql": rewritten},
            )
        return rewritten

    last_error: Exception | None = None
    for repair_attempt in range(MAX_SPARQL_REPAIRS + 1):
        try:
            sparql = apply_observed_canonical_iris(sparql, str(repair_attempt + 1))
            results = await graphdb_client.query(sparql, repo=resolved_repo, use_inference=use_inference)
            if not results and not state.get("force_custom_sparql", False):
                for reason, candidate in [*empty_result_fallback_candidates(sparql), *relationship_fallback_candidates(question)]:
                    candidate = inject_prefixes(candidate, ctx)
                    candidate = apply_observed_canonical_iris(candidate, f"{repair_attempt + 1}_candidate_{reason}")
                    try:
                        candidate_results = await graphdb_client.query(candidate, repo=resolved_repo, use_inference=use_inference)
                    except Exception as exc:
                        query_state.set_artifact(
                            f"sparql_empty_result_candidate_error_{repair_attempt + 1}_{reason}",
                            {"error": str(exc), "sparql": candidate},
                        )
                        continue
                    query_state.set_artifact(
                        f"sparql_empty_result_candidate_{repair_attempt + 1}_{reason}",
                        {"row_count": len(candidate_results), "sparql": candidate},
                    )
                    if candidate_results:
                        sparql = candidate
                        results = candidate_results
                        break
            results = _normalize_custom_result_aliases(question, results)
            semantic_failure = await answer_semantic_failure(sparql, results, f"{repair_attempt + 1}")
            if results and not semantic_failure:
                return successful_execution(sparql, results, repair_attempt)

            if not results:
                for reason, candidate in _observed_node_hop_answer_candidates(question, raw_graph_native_observations, ctx):
                    candidate = apply_observed_canonical_iris(candidate, f"{repair_attempt + 1}_observed_node_hop_candidate_{reason}")
                    try:
                        candidate_results = await graphdb_client.query(candidate, repo=resolved_repo, use_inference=use_inference)
                    except Exception as exc:
                        query_state.set_artifact(
                            f"sparql_observed_node_hop_candidate_error_{repair_attempt + 1}_{reason}",
                            {"error": str(exc), "sparql": candidate},
                        )
                        continue
                    candidate_results = _normalize_custom_result_aliases(question, candidate_results)
                    query_state.set_artifact(
                        f"sparql_observed_node_hop_candidate_{repair_attempt + 1}_{reason}",
                        {"row_count": len(candidate_results), "sparql": candidate},
                    )
                    if not candidate_results:
                        continue
                    semantic_failure = await answer_semantic_failure(
                        candidate,
                        candidate_results,
                        f"{repair_attempt + 1}_observed_node_hop_candidate_{reason}",
                    )
                    if not semantic_failure:
                        return successful_execution(candidate, candidate_results, repair_attempt)

            if (not results or semantic_failure) and repair_attempt < MAX_SPARQL_REPAIRS:
                repair_tool = "repair_sparql_answer_semantics" if semantic_failure else "repair_sparql_empty_result"
                repair_reason = (
                    "Repair custom SPARQL after it returned rows that do not satisfy the requested answer slots."
                    if semantic_failure
                    else "Repair custom SPARQL after it executed but returned no rows."
                )
                query_state.add_plan_step(
                    tool=repair_tool,
                    params={"attempt": repair_attempt + 1},
                    reasoning=repair_reason,
                )
                repair_grounding_context = (
                    {**grounding_context, "answer_semantic_debug": semantic_failure}
                    if semantic_failure
                    else grounding_context
                )
                empty_debug: dict[str, Any] | None = None
                if not results:
                    try:
                        empty_debug = await _debug_empty_sparql(
                            sparql,
                            ctx,
                            graphdb_client,
                            resolved_repo,
                            use_inference=use_inference,
                        )
                        query_state.set_artifact(f"sparql_empty_result_debug_{repair_attempt + 1}", empty_debug)
                        repair_grounding_context = {
                            **repair_grounding_context,
                            "sparql_empty_result_debug": empty_debug,
                        }
                    except Exception as exc:
                        query_state.set_artifact(f"sparql_empty_result_debug_error_{repair_attempt + 1}", str(exc))
                route_candidate_advanced = False
                if not results and empty_debug:
                    for reason, candidate in _route_debug_repair_candidates(sparql, empty_debug):
                        candidate = inject_prefixes(candidate, ctx)
                        candidate = apply_observed_canonical_iris(candidate, f"{repair_attempt + 1}_route_candidate_{reason}")
                        try:
                            candidate_results = await graphdb_client.query(candidate, repo=resolved_repo, use_inference=use_inference)
                        except Exception as exc:
                            query_state.set_artifact(
                                f"sparql_empty_result_route_candidate_error_{repair_attempt + 1}_{reason}",
                                {"error": str(exc), "sparql": candidate},
                            )
                            continue
                        query_state.set_artifact(
                            f"sparql_empty_result_route_candidate_{repair_attempt + 1}_{reason}",
                            {"row_count": len(candidate_results), "sparql": candidate},
                        )
                        if candidate_results:
                            sparql = candidate
                            results = _normalize_custom_result_aliases(question, candidate_results)
                            semantic_failure = await answer_semantic_failure(
                                sparql,
                                results,
                                f"{repair_attempt + 1}_route_candidate_{reason}",
                            )
                            if not semantic_failure:
                                return successful_execution(sparql, results, repair_attempt)
                            repair_grounding_context = {
                                **repair_grounding_context,
                                "answer_semantic_debug": semantic_failure,
                            }
                            break
                        if candidate != sparql:
                            sparql = candidate
                            route_candidate_advanced = True
                            break
                    if not results and route_candidate_advanced:
                        continue
                for reason, candidate in _observed_bridge_answer_candidates(question, sparql, repair_grounding_context, ctx):
                    candidate = apply_observed_canonical_iris(candidate, f"{repair_attempt + 1}_observed_bridge_candidate_{reason}")
                    try:
                        candidate_results = await graphdb_client.query(candidate, repo=resolved_repo, use_inference=use_inference)
                    except Exception as exc:
                        query_state.set_artifact(
                            f"sparql_observed_bridge_candidate_error_{repair_attempt + 1}_{reason}",
                            {"error": str(exc), "sparql": candidate},
                        )
                        continue
                    candidate_results = _normalize_custom_result_aliases(question, candidate_results)
                    query_state.set_artifact(
                        f"sparql_observed_bridge_candidate_{repair_attempt + 1}_{reason}",
                        {"row_count": len(candidate_results), "sparql": candidate},
                    )
                    if not candidate_results:
                        continue
                    semantic_failure = await answer_semantic_failure(
                        candidate,
                        candidate_results,
                        f"{repair_attempt + 1}_observed_bridge_candidate_{reason}",
                    )
                    if not semantic_failure:
                        return successful_execution(candidate, candidate_results, repair_attempt)
                    repair_grounding_context = {
                        **repair_grounding_context,
                        "answer_semantic_debug": semantic_failure,
                    }
                repair_prompt = build_empty_result_repair_messages(
                    question,
                    sparql,
                    ctx,
                    _compact_repair_grounding_context(repair_grounding_context),
                    enhanced_prompt=enhanced_prompt,
                )
                repaired = await gateway.chat_completion(
                    repair_prompt,
                    active_provider_config(settings),
                    purpose="sparql_repair_empty_result",
                )
                if contains_cannot_answer(repaired):
                    break
                sparql = inject_prefixes(extract_sparql(repaired), ctx)
                query_state.set_artifact(
                    f"sparql_empty_result_repair_{repair_attempt + 1}",
                    {"sparql": sparql},
                )
                continue
            if semantic_failure:
                last_error = RuntimeError("Generated SPARQL returned rows that do not satisfy the requested answer slots.")
                break
            return successful_execution(sparql, results, repair_attempt)
        except Exception as exc:
            last_error = exc
            if repair_attempt >= MAX_SPARQL_REPAIRS:
                break
            query_state.add_plan_step(
                tool="repair_sparql",
                params={"attempt": repair_attempt + 1},
                reasoning="Repair custom SPARQL after GraphDB execution failed.",
            )
            repair_prompt = build_execution_repair_messages(sparql, exc, enhanced_prompt=enhanced_prompt)
            repaired = await gateway.chat_completion(
                repair_prompt,
                active_provider_config(settings),
                purpose="sparql_repair_execution",
            )
            if contains_cannot_answer(repaired):
                raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
            sparql = inject_prefixes(extract_sparql(repaired), ctx)
            query_state.set_artifact(
                f"sparql_repair_{repair_attempt + 1}",
                {"error": str(exc), "sparql": sparql},
            )

    query_state.set_artifact("sparql_repair_limit_reached", True)
    raise HTTPException(status_code=422, detail=f"Generated SPARQL could not be executed after repairs: {last_error}")


async def _cannot_answer_node(state: NLQGraphState) -> dict[str, Any]:
    query_state = state["query_state"]
    query_state.set_artifact("cannot_answer_reason", "Graph iteration limit reached or planner chose cannot_answer.")
    execution = NLQExecutionPayload(sparql="", results=[], inference_used=False, state=query_state)
    return {"execution": execution, "query_state": query_state}


async def _answer_node(state: NLQGraphState) -> dict[str, Any]:
    execution = state["execution"]
    answer = await generate_answer(state["question"], execution.results, state["settings"], state["gateway"], state=execution.state)
    response = NLQResponse(
        question=state["question"],
        intent=state["intent"],
        execution_tool=execution.state.execution_tool(),
        sparql=execution.sparql,
        results=execution.results,
        answer=answer,
        repo_used=state["resolved_repo"],
        inference_used=execution.inference_used,
    )
    return {"answer": answer, "response": response, "query_state": execution.state}


def _build_langgraph():
    if StateGraph is None:
        return None
    graph = StateGraph(NLQGraphState)
    graph.add_node("initialize", _initialize_context)
    graph.add_node("plan", _plan_action)
    graph.add_node("structured", _execute_structured_node)
    graph.add_node("graph_native", _execute_graph_native_node)
    graph.add_node("custom_sparql", _execute_custom_sparql_node)
    graph.add_node("cannot_answer", _cannot_answer_node)
    graph.add_node("answer", _answer_node)
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "plan")
    graph.add_conditional_edges(
        "plan",
        _route_after_plan,
        {
            "structured": "structured",
            "graph_native": "graph_native",
            "custom_sparql": "custom_sparql",
            "cannot_answer": "cannot_answer",
        },
    )
    graph.add_edge("graph_native", "custom_sparql")
    graph.add_edge("structured", "answer")
    graph.add_edge("custom_sparql", "answer")
    graph.add_edge("cannot_answer", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


async def _run_compat_graph(initial_state: NLQGraphState) -> NLQGraphState:
    state: NLQGraphState = dict(initial_state)
    state.update(await _initialize_context(state))
    state.update(await _plan_action(state))
    route = _route_after_plan(state)
    if route == "structured":
        state.update(await _execute_structured_node(state))
    elif route == "graph_native":
        state.update(await _execute_graph_native_node(state))
        state.update(await _execute_custom_sparql_node(state))
    elif route == "custom_sparql":
        state.update(await _execute_custom_sparql_node(state))
    elif route == "cannot_answer":
        state.update(await _cannot_answer_node(state))
    else:
        raise LangGraphOrchestrationError(f"Unknown graph route: {route}")
    state.update(await _answer_node(state))
    return state


async def execute_nlq_graph(
    *,
    question: str,
    repo: str | None,
    answer_mode: str | None,
    settings: MLLESettings,
    graphdb_client: GraphDBClient,
    gateway: LLMGateway,
    force_custom_sparql: bool = False,
    custom_sparql_enhanced_prompt: bool = False,
) -> tuple[NLQResponse, NLQQueryState]:
    initial_state: NLQGraphState = {
        "question": question,
        "requested_repo": repo,
        "requested_answer_mode": answer_mode,
        "settings": settings,
        "graphdb_client": graphdb_client,
        "gateway": gateway,
        "force_custom_sparql": force_custom_sparql,
        "custom_sparql_enhanced_prompt": custom_sparql_enhanced_prompt,
    }
    try:
        graph = _build_langgraph()
        if graph is None:
            final_state = await _run_compat_graph(initial_state)
        else:
            final_state = await graph.ainvoke(initial_state, config={"recursion_limit": MAX_GRAPH_ITERATIONS + 5})
    except LangGraphOrchestrationError:
        raise
    except (HTTPException, ValueError):
        raise
    except Exception as exc:
        if exc.__class__.__module__.startswith("langgraph"):
            raise LangGraphOrchestrationError(str(exc)) from exc
        raise

    response = final_state.get("response")
    query_state = final_state.get("query_state")
    if not response or not query_state:
        raise LangGraphOrchestrationError("LangGraph execution completed without response state.")
    return response, query_state
