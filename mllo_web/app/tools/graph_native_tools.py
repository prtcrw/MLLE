from __future__ import annotations

import statistics
from collections import deque
from typing import Any

from mllo_web.app.tools.common import (
    escape_literal as _escape_literal,
    is_iri as _is_iri,
    resolve_repo as _resolve_repo,
    response as _response,
    run_ask as _run_ask,
    run_query as _run_query,
    run_raw_query as _run_raw_query,
)

MLLO_NAMESPACE = "http://www.semanticweb.org/mnd14/ml/"

GRAPH_NATIVE_PREFIXES = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX prov: <http://www.w3.org/ns/prov#>
"""

HIDDEN_OR_SCHEMA_TYPES = {
    "http://www.w3.org/2002/07/owl#Thing",
    "http://www.w3.org/2000/01/rdf-schema#Resource",
    "http://www.w3.org/2002/07/owl#NamedIndividual",
    "http://www.w3.org/2002/07/owl#Class",
    "http://www.w3.org/2000/01/rdf-schema#Class",
    "http://www.w3.org/2002/07/owl#ObjectProperty",
    "http://www.w3.org/2002/07/owl#DatatypeProperty",
    "http://www.w3.org/2002/07/owl#AnnotationProperty",
}

UPSTREAM_LINEAGE_PREDICATES = {
    "http://www.w3.org/ns/prov#wasDerivedFrom",
    "http://www.w3.org/ns/prov#wasGeneratedBy",
    "http://www.w3.org/ns/prov#used",
    "http://www.w3.org/2000/01/rdf-schema#isDefinedBy",
    "http://www.semanticweb.org/mnd14/ml/informationContentEntityDerivedFrom",
}
DOWNSTREAM_LINEAGE_PREDICATES = {
    "http://www.w3.org/ns/prov#generated",
    "http://www.w3.org/ns/prov#wasDerivedFrom",
    "http://www.w3.org/ns/prov#wasGeneratedBy",
    "http://www.w3.org/ns/prov#used",
    "http://www.semanticweb.org/mnd14/ml/informationContentEntityDerivedFrom",
}


async def _resolve_label_to_iri(label_or_iri: str, repo: str | None = None) -> tuple[str, str]:
    if _is_iri(label_or_iri):
        _, resolved_repo = await _resolve_repo(repo)
        return label_or_iri, resolved_repo
    lookup = await find_node_by_label_tool(label_or_iri, repo=repo)
    if not lookup["results"]:
        raise ValueError(f"No node found for label '{label_or_iri}'")
    return lookup["results"][0]["node"], lookup["repo_used"]


def _normalize_node_description(rows: list[dict]) -> dict[str, list[dict[str, str | None]]]:
    description: dict[str, list[dict[str, str | None]]] = {}
    for row in rows:
        predicate = row.get("predicate")
        if not predicate:
            continue
        description.setdefault(predicate, []).append(
            {
                "predicateLabel": row.get("predicateLabel"),
                "object": row.get("object"),
                "objectLabel": row.get("objectLabel"),
            }
        )
    return description


def _surrounding_neighbors(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("neighbor")]


def _is_hidden_or_schema_type(value: str | None) -> bool:
    if not value:
        return False
    if value in HIDDEN_OR_SCHEMA_TYPES:
        return True
    return (
        value.startswith("http://purl.obolibrary.org/obo/BFO_")
        or value.startswith("https://spec.industrialontologies.org/ontology/core/Core/")
    )


def _local_name(value: str | None) -> str | None:
    if not value or not _is_iri(value):
        return value
    if "#" in value:
        return value.rsplit("#", 1)[-1]
    return value.rstrip("/").rsplit("/", 1)[-1]


def _collapse_neighbor_rows(rows: list[dict]) -> list[dict]:
    collapsed: dict[tuple[str | None, str | None, str | None], dict[str, Any]] = {}
    for row in rows:
        key = (row.get("direction"), row.get("predicate"), row.get("neighbor"))
        existing = collapsed.get(key)
        candidate_type = row.get("neighborType")
        candidate = {
            **row,
            "neighborLabel": row.get("neighborLabel") or _local_name(row.get("neighbor")),
        }
        if not existing:
            collapsed[key] = candidate
            continue
        existing_type = existing.get("neighborType")
        if _is_hidden_or_schema_type(existing_type) and not _is_hidden_or_schema_type(candidate_type):
            collapsed[key] = candidate
        elif not existing.get("neighborLabel") and candidate.get("neighborLabel"):
            collapsed[key] = candidate
    return list(collapsed.values())


def _normalize_label_matches(rows: list[dict]) -> list[dict]:
    normalized: dict[str, dict[str, Any]] = {}
    for row in rows:
        node = row.get("node")
        if not node:
            continue
        candidate = {
            **row,
            "matchedLabel": row.get("matchedLabel") or _local_name(node),
        }
        existing = normalized.get(node)
        if not existing:
            normalized[node] = candidate
            continue
        existing_type = existing.get("type")
        candidate_type = candidate.get("type")
        if _is_hidden_or_schema_type(existing_type) and not _is_hidden_or_schema_type(candidate_type):
            normalized[node] = candidate
    return sorted(
        normalized.values(),
        key=lambda row: (
            _is_hidden_or_schema_type(row.get("type")),
            row.get("matchedLabel") or "",
            row.get("node") or "",
        ),
    )


def _normalize_entity_rows(
    rows: list[dict],
    iri_key: str,
    label_key: str,
    type_key: str | None = None,
) -> list[dict]:
    normalized = []
    for row in rows:
        candidate = dict(row)
        iri_value = candidate.get(iri_key)
        if type_key and _is_hidden_or_schema_type(candidate.get(type_key)):
            candidate.pop(type_key, None)
        if not candidate.get(label_key):
            candidate[label_key] = _local_name(iri_value)
        normalized.append(candidate)
    return normalized


async def filter_by_string_tool(search_term: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?node ?label ?type WHERE {{
  {{
    ?node rdfs:label|skos:prefLabel|skos:altLabel|rdfs:comment ?matchedText .
    FILTER(CONTAINS(LCASE(STR(?matchedText)), LCASE("{_escape_literal(search_term)}")))
    BIND(STR(?matchedText) AS ?label)
  }} UNION {{
    ?node ?p ?o .
    FILTER(isIRI(?node))
    BIND(REPLACE(STR(?node), "^.*(#|/)", "") AS ?localName)
    FILTER(CONTAINS(LCASE(?localName), LCASE("{_escape_literal(search_term)}")))
    BIND(?localName AS ?label)
  }}
  OPTIONAL {{ ?node a ?type . FILTER(!isBlank(?type)) }}
  FILTER(isIRI(?node))
}} ORDER BY ?type ?label
LIMIT 50
"""
    return await _run_query("filter_by_string", sparql, repo=repo)


async def find_by_type_tool(class_iri: str, limit: int = 50, repo: str | None = None) -> dict:
    resolved_class_iri, resolved_repo = await _resolve_label_to_iri(class_iri, repo=repo)
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?individual ?label WHERE {{
  ?individual a ?individualType .
  ?individualType rdfs:subClassOf* <{resolved_class_iri}> .
  OPTIONAL {{ ?individual rdfs:label|skos:prefLabel ?label }}
  FILTER(isIRI(?individual))
  FILTER NOT EXISTS {{ ?individual a owl:Class }}
  FILTER NOT EXISTS {{ ?individual a rdfs:Class }}
  FILTER NOT EXISTS {{ ?individual a owl:ObjectProperty }}
  FILTER NOT EXISTS {{ ?individual a owl:DatatypeProperty }}
  FILTER NOT EXISTS {{ ?individual a owl:AnnotationProperty }}
}} ORDER BY ?label
LIMIT {min(limit, 100)}
"""
    return await _run_query("find_by_type", sparql, repo=resolved_repo)


async def find_by_property_value_tool(property_iri: str, value: str, repo: str | None = None) -> dict:
    escaped_value = _escape_literal(value)
    iri_union = f'?node <{property_iri}> <{value}> .' if _is_iri(value) else ""
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?node ?label WHERE {{
  {{
    ?node <{property_iri}> "{escaped_value}" .
  }} UNION {{
    ?node <{property_iri}> "{escaped_value}"^^xsd:string .
  }}
  {"UNION { " + iri_union + " }" if iri_union else ""}
  OPTIONAL {{ ?node rdfs:label|skos:prefLabel ?label }}
  OPTIONAL {{ ?node a ?type }}
  FILTER(!isBlank(?node))
}} LIMIT 50
"""
    return await _run_query("find_by_property_value", sparql, repo=repo)


async def list_all_classes_tool(repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?class (SAMPLE(?label) AS ?label) (COUNT(DISTINCT ?instance) AS ?count) WHERE {{
  ?instance a ?class .
  FILTER(isIRI(?instance) && isIRI(?class))
  FILTER(?class NOT IN (
    owl:Thing,
    rdfs:Resource,
    owl:NamedIndividual,
    owl:Class,
    owl:ObjectProperty,
    owl:DatatypeProperty,
    owl:AnnotationProperty,
    rdfs:Class,
    rdf:List,
    rdf:Property
  ))
  FILTER(!STRSTARTS(STR(?class), "http://purl.obolibrary.org/obo/BFO_"))
  FILTER(!STRSTARTS(STR(?class), "https://spec.industrialontologies.org/ontology/core/Core/"))
  FILTER NOT EXISTS {{ ?instance a owl:Class }}
  FILTER NOT EXISTS {{ ?instance a rdfs:Class }}
  FILTER NOT EXISTS {{ ?instance a owl:ObjectProperty }}
  FILTER NOT EXISTS {{ ?instance a owl:DatatypeProperty }}
  FILTER NOT EXISTS {{ ?instance a owl:AnnotationProperty }}
  OPTIONAL {{ ?class rdfs:label|skos:prefLabel ?label }}
}} GROUP BY ?class
ORDER BY DESC(?count)
LIMIT 100
"""
    return await _run_query("list_all_classes", sparql, repo=repo)


async def list_all_properties_tool(class_iri: str | None = None, repo: str | None = None) -> dict:
    if class_iri:
        resolved_class_iri, resolved_repo = await _resolve_label_to_iri(class_iri, repo=repo)
        sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?property (SAMPLE(?label) AS ?label) (COUNT(*) AS ?usage) WHERE {{
  ?s a ?subjectType .
  ?subjectType rdfs:subClassOf* <{resolved_class_iri}> .
  ?s ?property ?o .
  FILTER(isIRI(?property))
  FILTER(?property != rdf:type)
  FILTER(?property NOT IN (rdfs:subClassOf, rdfs:domain, rdfs:range, rdfs:subPropertyOf, rdf:first, rdf:rest))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2002/07/owl#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2000/01/rdf-schema#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  FILTER NOT EXISTS {{ ?s a owl:Class }}
  FILTER NOT EXISTS {{ ?s a rdfs:Class }}
  FILTER NOT EXISTS {{ ?s a owl:ObjectProperty }}
  FILTER NOT EXISTS {{ ?s a owl:DatatypeProperty }}
  FILTER NOT EXISTS {{ ?s a owl:AnnotationProperty }}
  OPTIONAL {{ ?property rdfs:label|skos:prefLabel ?label }}
}} GROUP BY ?property
ORDER BY DESC(?usage)
LIMIT 100
"""
        return await _run_query("list_all_properties", sparql, repo=resolved_repo)

    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?property (SAMPLE(?label) AS ?label) (COUNT(*) AS ?usage) WHERE {{
  ?s ?property ?o .
  FILTER(isIRI(?property))
  FILTER(?property != rdf:type)
  FILTER(?property NOT IN (rdfs:subClassOf, rdfs:domain, rdfs:range, rdfs:subPropertyOf, rdf:first, rdf:rest))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2002/07/owl#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2000/01/rdf-schema#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  FILTER NOT EXISTS {{ ?s a owl:Class }}
  FILTER NOT EXISTS {{ ?s a rdfs:Class }}
  FILTER NOT EXISTS {{ ?s a owl:ObjectProperty }}
  FILTER NOT EXISTS {{ ?s a owl:DatatypeProperty }}
  FILTER NOT EXISTS {{ ?s a owl:AnnotationProperty }}
  OPTIONAL {{ ?property rdfs:label|skos:prefLabel ?label }}
}} GROUP BY ?property
ORDER BY DESC(?usage)
LIMIT 100
"""
    return await _run_query("list_all_properties", sparql, repo=repo)


async def find_surrounding_nodes_tool(iri: str, depth: int = 1, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?direction ?predicate ?predicateLabel ?neighbor ?neighborLabel ?neighborType WHERE {{
  {{
    BIND("outgoing" AS ?direction)
    <{iri}> ?predicate ?neighbor .
    FILTER(!isBlank(?neighbor))
  }} UNION {{
    BIND("incoming" AS ?direction)
    ?neighbor ?predicate <{iri}> .
    FILTER(!isBlank(?neighbor))
  }}
  OPTIONAL {{ ?neighbor rdfs:label|skos:prefLabel ?neighborLabel }}
  OPTIONAL {{ ?neighbor a ?neighborType . FILTER(!isBlank(?neighborType)) }}
  OPTIONAL {{ ?predicate rdfs:label|skos:prefLabel ?predicateLabel }}
}} ORDER BY ?direction ?predicate
LIMIT 100
"""
    base = await _run_query("find_surrounding_nodes", sparql, repo=repo)
    base["results"] = _collapse_neighbor_rows(base["results"])
    base["count"] = len(base["results"])
    if depth <= 1:
        return base

    expanded = list(base["results"])
    second_level_targets = [
        row["neighbor"] for row in expanded
        if row.get("neighbor") and _is_iri(row["neighbor"])
    ][:20]
    for target in second_level_targets:
        nested = await find_surrounding_nodes_tool(target, depth=1, repo=base["repo_used"])
        expanded.extend(nested["results"][:20])
    expanded = _collapse_neighbor_rows(expanded)
    return _response("find_surrounding_nodes", expanded, base["repo_used"], inference_used=False, depth=depth)


async def describe_node_tool(iri: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?predicate ?predicateLabel ?object ?objectLabel WHERE {{
  <{iri}> ?predicate ?object .
  FILTER(!isBlank(?object))
  OPTIONAL {{ ?predicate rdfs:label|skos:prefLabel ?predicateLabel }}
  OPTIONAL {{
    ?object rdfs:label|skos:prefLabel ?objectLabel .
    FILTER(!isLiteral(?object))
  }}
}} ORDER BY ?predicate
"""
    results, resolved_repo = await _run_raw_query(sparql, repo=repo, show_upper_ontology=True)
    cleaned_rows = []
    for row in results:
        if row.get("predicate") == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" and _is_hidden_or_schema_type(row.get("object")):
            continue
        cleaned_rows.append(
            {
                **row,
                "objectLabel": row.get("objectLabel") or _local_name(row.get("object")),
            }
        )
    return _response("describe_node", _normalize_node_description(cleaned_rows), resolved_repo)


async def find_node_by_label_tool(label: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?node ?matchedLabel ?type WHERE {{
  ?node rdfs:label|skos:prefLabel|skos:altLabel ?matchedLabel .
  FILTER(LCASE(STR(?matchedLabel)) = LCASE("{_escape_literal(label)}"))
  OPTIONAL {{ ?node a ?type . FILTER(!isBlank(?type)) }}
  FILTER(!isBlank(?node))
}} LIMIT 20
"""
    response = await _run_query("find_node_by_label", sparql, repo=repo)
    response["results"] = _normalize_label_matches(response["results"])
    response["count"] = len(response["results"])
    return response


async def compare_nodes_tool(iri_1: str, iri_2: str, repo: str | None = None) -> dict:
    node1 = await describe_node_tool(iri_1, repo=repo)
    node2 = await describe_node_tool(iri_2, repo=node1["repo_used"])
    desc1 = node1["results"]
    desc2 = node2["results"]
    shared_properties = {
        predicate: {"first": desc1[predicate], "second": desc2[predicate]}
        for predicate in desc1
        if predicate in desc2
    }
    only_in_first = {predicate: values for predicate, values in desc1.items() if predicate not in desc2}
    only_in_second = {predicate: values for predicate, values in desc2.items() if predicate not in desc1}
    value_differences = {
        predicate: values
        for predicate, values in shared_properties.items()
        if values["first"] != values["second"]
    }
    return _response(
        "compare_nodes",
        {
            "shared_properties": shared_properties,
            "only_in_first": only_in_first,
            "only_in_second": only_in_second,
            "value_differences": value_differences,
        },
        node2["repo_used"],
    )


async def find_common_neighbors_tool(iri_1: str, iri_2: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?common ?commonLabel ?commonType ?predicateFrom1 ?predicateFrom2 WHERE {{
  {{
    <{iri_1}> ?predicateFrom1 ?common .
    <{iri_2}> ?predicateFrom2 ?common .
  }} UNION {{
    ?common ?predicateFrom1 <{iri_1}> .
    ?common ?predicateFrom2 <{iri_2}> .
  }}
  FILTER(!isBlank(?common))
  FILTER(?common != <{iri_1}> && ?common != <{iri_2}>)
  OPTIONAL {{ ?common rdfs:label|skos:prefLabel ?commonLabel }}
  OPTIONAL {{ ?common a ?commonType . FILTER(!isBlank(?commonType)) }}
}} LIMIT 50
"""
    response = await _run_query("find_common_neighbors", sparql, repo=repo)
    normalized = []
    for row in response["results"]:
        if _is_hidden_or_schema_type(row.get("commonType")):
            row = {key: value for key, value in row.items() if key != "commonType"}
        if not row.get("commonLabel"):
            row["commonLabel"] = _local_name(row.get("common"))
        normalized.append(row)
    response["results"] = normalized
    response["count"] = len(normalized)
    return response


async def graph_traversal_tool(start_iri: str, target_class: str, max_hops: int = 5, repo: str | None = None) -> dict:
    hop_limit = min(max_hops, 5)
    resolved_target_class, resolved_repo = await _resolve_label_to_iri(target_class, repo=repo)
    queue: deque[tuple[str, int]] = deque([(start_iri, 0)])
    visited = {start_iri}
    found: list[dict[str, Any]] = []

    while queue:
        current, hop = queue.popleft()
        if hop >= hop_limit:
            continue
        neighbors = await find_surrounding_nodes_tool(current, depth=1, repo=resolved_repo)
        for row in _surrounding_neighbors(neighbors["results"]):
            neighbor = row["neighbor"]
            if not _is_iri(neighbor) or neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append((neighbor, hop + 1))
            membership = await check_class_membership_tool(
                neighbor,
                resolved_target_class,
                use_inference=False,
                repo=resolved_repo,
            )
            if membership.get("boolean"):
                found.append(
                    {
                        "result": neighbor,
                        "resultLabel": row.get("neighborLabel"),
                        "path": None,
                        "hops": hop + 1,
                    }
                )

    found = _normalize_entity_rows(found, "result", "resultLabel")
    return _response("graph_traversal", found, resolved_repo, max_hops=hop_limit)


async def find_shortest_path_tool(iri_1: str, iri_2: str, repo: str | None = None) -> dict:
    _, resolved_repo = await _resolve_repo(repo)
    frontier = deque([iri_1])
    visited = {iri_1}
    path_map: dict[str, list[dict[str, Any]]] = {iri_1: []}

    for hop in range(1, 6):
        next_frontier: deque[str] = deque()
        while frontier:
            node = frontier.popleft()
            neighbors = await find_surrounding_nodes_tool(node, depth=1, repo=resolved_repo)
            for item in _surrounding_neighbors(neighbors["results"]):
                neighbor_iri = item["neighbor"]
                if not _is_iri(neighbor_iri) or neighbor_iri in visited:
                    continue
                path_map[neighbor_iri] = path_map[node] + [item]
                if neighbor_iri == iri_2:
                    return _response("find_shortest_path", path_map[neighbor_iri], resolved_repo, hops=hop)
                visited.add(neighbor_iri)
                next_frontier.append(neighbor_iri)
        frontier = next_frontier
        if not frontier:
            break

    return _response("find_shortest_path", [], resolved_repo, path=None, message="No path found within 5 hops")


async def find_all_paths_tool(iri_1: str, iri_2: str, max_hops: int = 3, repo: str | None = None) -> dict:
    hop_limit = min(max_hops, 3)
    _, resolved_repo = await _resolve_repo(repo)
    queue: deque[tuple[str, list[dict[str, Any]], set[str]]] = deque([(iri_1, [], {iri_1})])
    paths: list[list[dict[str, Any]]] = []

    while queue and len(paths) < 20:
        current, path, seen = queue.popleft()
        if len(path) >= hop_limit:
            continue
        neighbors = await find_surrounding_nodes_tool(current, depth=1, repo=resolved_repo)
        for item in _surrounding_neighbors(neighbors["results"]):
            neighbor_iri = item["neighbor"]
            if not _is_iri(neighbor_iri) or neighbor_iri in seen:
                continue
            next_path = path + [item]
            if neighbor_iri == iri_2:
                paths.append(next_path)
                continue
            queue.append((neighbor_iri, next_path, seen | {neighbor_iri}))

    return _response("find_all_paths", paths, resolved_repo, max_hops=hop_limit)


async def trace_lineage_tool(iri: str, direction: str = "upstream", max_hops: int = 10, repo: str | None = None) -> dict:
    hop_limit = min(max_hops, 10)
    _, resolved_repo = await _resolve_repo(repo)
    queue: deque[tuple[str, int]] = deque([(iri, 0)])
    visited = {iri}
    lineage: list[dict[str, Any]] = []

    while queue:
        current, hop = queue.popleft()
        if hop >= hop_limit:
            continue
        neighbors = await find_surrounding_nodes_tool(current, depth=1, repo=resolved_repo)
        for row in _surrounding_neighbors(neighbors["results"]):
            predicate = row.get("predicate")
            direction_value = row.get("direction")
            neighbor = row.get("neighbor")
            if not _is_iri(neighbor) or neighbor in visited:
                continue

            is_upstream_edge = (
                (direction_value == "outgoing" and predicate in UPSTREAM_LINEAGE_PREDICATES)
                or (direction_value == "incoming" and predicate == "http://www.w3.org/ns/prov#generated")
            )
            is_downstream_edge = (
                (direction_value == "incoming" and predicate in DOWNSTREAM_LINEAGE_PREDICATES)
                or (direction_value == "outgoing" and predicate == "http://www.w3.org/ns/prov#generated")
            )

            if direction == "downstream" and not is_downstream_edge:
                continue
            if direction != "downstream" and not is_upstream_edge:
                continue

            visited.add(neighbor)
            queue.append((neighbor, hop + 1))
            lineage.append(
                {
                    ("descendant" if direction == "downstream" else "ancestor"): neighbor,
                    ("descendantLabel" if direction == "downstream" else "ancestorLabel"): row.get("neighborLabel") or _local_name(neighbor),
                    ("descendantType" if direction == "downstream" else "ancestorType"): row.get("neighborType"),
                    "predicate": predicate,
                    "hops": hop + 1,
                }
            )

    key_iri = "descendant" if direction == "downstream" else "ancestor"
    key_label = "descendantLabel" if direction == "downstream" else "ancestorLabel"
    key_type = "descendantType" if direction == "downstream" else "ancestorType"
    lineage = _normalize_entity_rows(lineage, key_iri, key_label, key_type)
    return _response("trace_lineage", lineage, resolved_repo, direction=direction, max_hops=hop_limit)


async def find_subgraph_tool(root_iri: str, depth: int = 2, repo: str | None = None) -> dict:
    depth = min(depth, 3)
    _, resolved_repo = await _resolve_repo(repo)
    nodes: dict[str, dict[str, Any]] = {root_iri: {"id": root_iri, "label": root_iri, "type": ""}}
    edges: list[dict[str, Any]] = []
    frontier = [root_iri]
    visited = {root_iri}

    for _ in range(depth):
        next_frontier: list[str] = []
        for node_iri in frontier:
            result = await find_surrounding_nodes_tool(node_iri, depth=1, repo=resolved_repo)
            for row in _surrounding_neighbors(result["results"]):
                neighbor = row["neighbor"]
                if not _is_iri(neighbor):
                    continue
                nodes.setdefault(
                    neighbor,
                    {
                        "id": neighbor,
                        "label": row.get("neighborLabel") or neighbor,
                        "type": "" if _is_hidden_or_schema_type(row.get("neighborType")) else (row.get("neighborType") or ""),
                    },
                )
                edges.append(
                    {
                        "source": node_iri if row.get("direction") == "outgoing" else neighbor,
                        "target": neighbor if row.get("direction") == "outgoing" else node_iri,
                        "predicate": row.get("predicate"),
                        "predicateLabel": row.get("predicateLabel", ""),
                    }
                )
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
        frontier = next_frontier

    return _response("find_subgraph", {"nodes": list(nodes.values()), "edges": edges}, resolved_repo, depth=depth)


async def get_class_hierarchy_tool(root_class: str | None = None, repo: str | None = None) -> dict:
    root_filter = ""
    resolved_repo = repo
    if root_class:
        resolved_root_class, resolved_repo = await _resolve_label_to_iri(root_class, repo=repo)
        root_filter = f"FILTER(?child = <{resolved_root_class}> || EXISTS {{ ?child rdfs:subClassOf+ <{resolved_root_class}> }})"
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?child ?childLabel ?parent ?parentLabel WHERE {{
  ?child rdfs:subClassOf ?parent .
  FILTER(!isBlank(?child) && !isBlank(?parent))
  FILTER(!STRSTARTS(STR(?parent), "http://www.w3.org/2002/07/owl#"))
  FILTER(!STRSTARTS(STR(?parent), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  OPTIONAL {{ ?child rdfs:label|skos:prefLabel ?childLabel }}
  OPTIONAL {{ ?parent rdfs:label|skos:prefLabel ?parentLabel }}
  {root_filter}
}} ORDER BY ?parent ?child
"""
    response = await _run_query("get_class_hierarchy", sparql, repo=resolved_repo)
    response["results"] = [
        {
            **row,
            "childLabel": row.get("childLabel") or _local_name(row.get("child")),
            "parentLabel": row.get("parentLabel") or _local_name(row.get("parent")),
        }
        for row in response["results"]
        if not _is_hidden_or_schema_type(row.get("child")) and not _is_hidden_or_schema_type(row.get("parent"))
    ]
    response["count"] = len(response["results"])
    return response


async def get_class_schema_tool(class_iri: str, repo: str | None = None) -> dict:
    resolved_class_iri, resolved_repo = await _resolve_label_to_iri(class_iri, repo=repo)
    ontology_defined_sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?property ?propertyLabel ?range ?rangeLabel WHERE {{
  ?property rdfs:domain <{resolved_class_iri}> .
  OPTIONAL {{ ?property rdfs:range ?range }}
  OPTIONAL {{ ?property rdfs:label|skos:prefLabel ?propertyLabel }}
  OPTIONAL {{ ?range rdfs:label|skos:prefLabel ?rangeLabel }}
  FILTER(?property != rdf:type)
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2002/07/owl#"))
}} ORDER BY ?property
"""
    instance_usage_sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?property ?propertyLabel (COUNT(?instance) AS ?usage) WHERE {{
  ?instance a ?instanceType .
  ?instanceType rdfs:subClassOf* <{resolved_class_iri}> .
  ?instance ?property ?value .
  FILTER(?property != rdf:type)
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2002/07/owl#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2000/01/rdf-schema#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  OPTIONAL {{ ?property rdfs:label|skos:prefLabel ?propertyLabel }}
}} GROUP BY ?property ?propertyLabel
ORDER BY DESC(?usage)
"""
    ontology_defined, _ = await _run_raw_query(ontology_defined_sparql, repo=resolved_repo, show_upper_ontology=True)
    instance_usage, _ = await _run_raw_query(instance_usage_sparql, repo=resolved_repo, show_upper_ontology=True)
    ontology_defined = [
        {
            **row,
            "propertyLabel": row.get("propertyLabel") or _local_name(row.get("property")),
            "rangeLabel": row.get("rangeLabel") or _local_name(row.get("range")),
        }
        for row in ontology_defined
        if not _is_hidden_or_schema_type(row.get("range"))
    ]
    instance_usage = [
        {
            **row,
            "propertyLabel": row.get("propertyLabel") or _local_name(row.get("property")),
        }
        for row in instance_usage
    ]
    return _response("get_class_schema", {"ontology_defined": ontology_defined, "instance_usage": instance_usage}, resolved_repo)


async def find_related_classes_tool(class_iri: str, repo: str | None = None) -> dict:
    resolved_class_iri, resolved_repo = await _resolve_label_to_iri(class_iri, repo=repo)
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?property ?propertyLabel ?relatedClass ?relatedClassLabel WHERE {{
  {{
    ?property rdfs:domain <{resolved_class_iri}> .
    ?property rdfs:range ?relatedClass .
  }} UNION {{
    ?property rdfs:range <{resolved_class_iri}> .
    ?property rdfs:domain ?relatedClass .
  }} UNION {{
    ?instance a ?instanceType .
    ?instanceType rdfs:subClassOf* <{resolved_class_iri}> .
    ?instance ?property ?target .
    ?target a ?targetType .
    ?targetType rdfs:subClassOf* ?relatedClass .
    FILTER(isIRI(?target))
  }} UNION {{
    ?instance a ?instanceType .
    ?instanceType rdfs:subClassOf* <{resolved_class_iri}> .
    ?source ?property ?instance .
    ?source a ?sourceType .
    ?sourceType rdfs:subClassOf* ?relatedClass .
    FILTER(isIRI(?source))
  }}
  FILTER(!isBlank(?relatedClass))
  FILTER(!isBlank(?property))
  FILTER(?property != rdf:type)
  FILTER(!STRSTARTS(STR(?relatedClass), "http://www.w3.org/2002/07/owl#"))
  FILTER(!STRSTARTS(STR(?relatedClass), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2002/07/owl#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/2000/01/rdf-schema#"))
  FILTER(!STRSTARTS(STR(?property), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  OPTIONAL {{ ?property rdfs:label|skos:prefLabel ?propertyLabel }}
  OPTIONAL {{ ?relatedClass rdfs:label|skos:prefLabel ?relatedClassLabel }}
}} ORDER BY ?property
"""
    results, _ = await _run_raw_query(sparql, repo=resolved_repo, show_upper_ontology=True)
    normalized = [
        {
            **row,
            "propertyLabel": row.get("propertyLabel") or _local_name(row.get("property")),
            "relatedClassLabel": row.get("relatedClassLabel") or _local_name(row.get("relatedClass")),
        }
        for row in results
        if not _is_hidden_or_schema_type(row.get("relatedClass"))
        and not _is_hidden_or_schema_type(row.get("property"))
    ]
    deduped: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for row in normalized:
        deduped[(row.get("property"), row.get("relatedClass"))] = row
    final_results = list(deduped.values())
    return _response("find_related_classes", final_results, resolved_repo)


async def get_namespace_summary_tool(repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?namespace (COUNT(*) AS ?tripleCount) WHERE {{
  ?s ?p ?o .
  BIND(REPLACE(STR(?s), "(#|/)[^#/]*$", "$1") AS ?namespace)
  FILTER(isIRI(?s))
}} GROUP BY ?namespace
ORDER BY DESC(?tripleCount)
LIMIT 50
"""
    return await _run_query("get_namespace_summary", sparql, repo=repo, show_upper_ontology=True)


async def check_class_membership_tool(iri: str, class_iri: str, use_inference: bool = False, repo: str | None = None) -> dict:
    resolved_class_iri, resolved_repo = await _resolve_label_to_iri(class_iri, repo=repo)
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
ASK {{
  <{iri}> a ?type .
  ?type rdfs:subClassOf* <{resolved_class_iri}> .
}}
"""
    return await _run_ask("check_class_membership", sparql, repo=resolved_repo, use_inference=use_inference)


async def count_by_type_tool(repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?class (SAMPLE(?classLabel) AS ?classLabel) (COUNT(DISTINCT ?instance) AS ?count) WHERE {{
  ?instance a ?class .
  FILTER(isIRI(?instance) && isIRI(?class))
  FILTER(?class NOT IN (
    owl:Thing, rdfs:Resource, owl:NamedIndividual, owl:Class,
    owl:ObjectProperty, owl:DatatypeProperty, owl:AnnotationProperty, rdfs:Class, rdf:List, rdf:Property
  ))
  FILTER(!STRSTARTS(STR(?class), "http://purl.obolibrary.org/obo/BFO_"))
  FILTER(!STRSTARTS(STR(?class), "https://spec.industrialontologies.org/ontology/core/Core/"))
  FILTER NOT EXISTS {{ ?instance a owl:Class }}
  FILTER NOT EXISTS {{ ?instance a rdfs:Class }}
  FILTER NOT EXISTS {{ ?instance a owl:ObjectProperty }}
  FILTER NOT EXISTS {{ ?instance a owl:DatatypeProperty }}
  FILTER NOT EXISTS {{ ?instance a owl:AnnotationProperty }}
  OPTIONAL {{ ?class rdfs:label|skos:prefLabel ?classLabel }}
}} GROUP BY ?class
ORDER BY DESC(?count)
"""
    return await _run_query("count_by_type", sparql, repo=repo)


async def count_by_property_tool(property_iri: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?value ?valueLabel (COUNT(?node) AS ?count) WHERE {{
  ?node <{property_iri}> ?value .
  FILTER(!isBlank(?node))
  OPTIONAL {{
    ?value rdfs:label|skos:prefLabel ?valueLabel .
    FILTER(!isLiteral(?value))
  }}
}} GROUP BY ?value ?valueLabel
ORDER BY DESC(?count)
LIMIT 100
"""
    response = await _run_query("count_by_property", sparql, repo=repo)
    response["results"] = [
        {
            **row,
            "valueLabel": row.get("valueLabel") or _local_name(row.get("value")),
        }
        for row in response["results"]
        if not _is_hidden_or_schema_type(row.get("value"))
    ]
    response["count"] = len(response["results"])
    return response


async def get_property_distribution_tool(class_iri: str, property_iri: str, repo: str | None = None) -> dict:
    resolved_class_iri, resolved_repo = await _resolve_label_to_iri(class_iri, repo=repo)
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?value (COUNT(DISTINCT ?instance) AS ?count) WHERE {{
  ?instance a ?instanceType .
  ?instanceType rdfs:subClassOf* <{resolved_class_iri}> .
  ?instance <{property_iri}> ?value .
}} GROUP BY ?value
ORDER BY DESC(?count)
"""
    results, _ = await _run_raw_query(sparql, repo=resolved_repo, use_inference=True)
    total = sum(int(row["count"]) for row in results) or 1
    distribution = [
        {
            **row,
            "valueLabel": _local_name(row.get("value")),
            "count": int(row["count"]),
            "percentage": round((int(row["count"]) / total) * 100, 2),
        }
        for row in results
    ]
    return _response("get_property_distribution", distribution, resolved_repo)


async def find_missing_properties_tool(class_iri: str, required_properties: list[str], repo: str | None = None) -> dict:
    resolved_class_iri, resolved_repo = await _resolve_label_to_iri(class_iri, repo=repo)
    missing_map: dict[str, dict[str, Any]] = {}
    for property_iri in required_properties:
        sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?instance ?instanceLabel WHERE {{
  ?instance a ?instanceType .
  ?instanceType rdfs:subClassOf* <{resolved_class_iri}> .
  FILTER NOT EXISTS {{ ?instance <{property_iri}> ?value }}
  OPTIONAL {{ ?instance rdfs:label|skos:prefLabel ?instanceLabel }}
}} ORDER BY ?instanceLabel
"""
        results, _ = await _run_raw_query(sparql, repo=resolved_repo)
        for row in results:
            instance = row["instance"]
            entry = missing_map.setdefault(
                instance,
                {
                    "instance": instance,
                    "instanceLabel": row.get("instanceLabel") or _local_name(instance),
                    "missing_properties": [],
                },
            )
            entry["missing_properties"].append(property_iri)
    return _response("find_missing_properties", list(missing_map.values()), resolved_repo)


async def find_outliers_tool(class_iri: str, property_iri: str, repo: str | None = None) -> dict:
    resolved_class_iri, resolved_repo = await _resolve_label_to_iri(class_iri, repo=repo)
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?instance ?instanceLabel ?value WHERE {{
  ?instance a ?instanceType .
  ?instanceType rdfs:subClassOf* <{resolved_class_iri}> .
  ?instance <{property_iri}> ?value .
  FILTER(isNumeric(?value))
  OPTIONAL {{ ?instance rdfs:label|skos:prefLabel ?instanceLabel }}
}} ORDER BY ?value
"""
    results, _ = await _run_raw_query(sparql, repo=resolved_repo)
    if not results:
        return _response("find_outliers", {"mean": None, "stdev": None, "outliers": []}, resolved_repo)
    numeric_results = [{**row, "instanceLabel": row.get("instanceLabel") or _local_name(row.get("instance")), "value": float(row["value"])} for row in results]
    values = [row["value"] for row in numeric_results]
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    outliers = [row for row in numeric_results if abs(row["value"] - mean) > 2 * stdev] if stdev else []
    return _response("find_outliers", {"mean": mean, "stdev": stdev, "outliers": outliers}, resolved_repo)


async def find_external_links_tool(iri: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
PREFIX schema: <https://schema.org/>
SELECT DISTINCT ?linkType ?externalResource WHERE {{
  VALUES ?linkType {{
    owl:sameAs skos:exactMatch skos:closeMatch
    rdfs:seeAlso schema:sameAs prov:wasDerivedFrom
  }}
  <{iri}> ?linkType ?externalResource .
  FILTER(!isLiteral(?externalResource))
}} ORDER BY ?linkType
"""
    response = await _run_query("find_external_links", sparql, repo=repo, show_upper_ontology=True)
    response["results"] = _normalize_entity_rows(response["results"], "externalResource", "externalResource", None)
    return response


async def find_cross_ontology_nodes_tool(namespace_uri: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?externalNode ?externalLabel ?mlloNode ?mlloLabel ?predicate WHERE {{
  {{
    ?externalNode ?predicate ?mlloNode .
    FILTER(STRSTARTS(STR(?externalNode), "{_escape_literal(namespace_uri)}"))
    FILTER(!STRSTARTS(STR(?mlloNode), "{_escape_literal(namespace_uri)}"))
  }} UNION {{
    ?mlloNode ?predicate ?externalNode .
    FILTER(STRSTARTS(STR(?externalNode), "{_escape_literal(namespace_uri)}"))
    FILTER(!STRSTARTS(STR(?mlloNode), "{_escape_literal(namespace_uri)}"))
  }}
  OPTIONAL {{ ?externalNode rdfs:label|skos:prefLabel ?externalLabel }}
  OPTIONAL {{ ?mlloNode rdfs:label|skos:prefLabel ?mlloLabel }}
}} LIMIT 100
"""
    response = await _run_query("find_cross_ontology_nodes", sparql, repo=repo, show_upper_ontology=True)
    response["results"] = [
        {
            **row,
            "externalLabel": row.get("externalLabel") or _local_name(row.get("externalNode")),
            "mlloLabel": row.get("mlloLabel") or _local_name(row.get("mlloNode")),
        }
        for row in response["results"]
    ]
    response["count"] = len(response["results"])
    return response


async def find_bridge_nodes_tool(namespace_1: str, namespace_2: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT DISTINCT ?bridge ?bridgeLabel ?ns1Node ?ns2Node ?pred1 ?pred2 WHERE {{
  ?ns1Node ?pred1 ?bridge .
  ?bridge ?pred2 ?ns2Node .
  FILTER(STRSTARTS(STR(?ns1Node), "{_escape_literal(namespace_1)}"))
  FILTER(STRSTARTS(STR(?ns2Node), "{_escape_literal(namespace_2)}"))
  FILTER(!STRSTARTS(STR(?bridge), "{_escape_literal(namespace_1)}"))
  FILTER(!STRSTARTS(STR(?bridge), "{_escape_literal(namespace_2)}"))
  OPTIONAL {{ ?bridge rdfs:label|skos:prefLabel ?bridgeLabel }}
}} LIMIT 50
"""
    response = await _run_query("find_bridge_nodes", sparql, repo=repo, show_upper_ontology=True)
    response["results"] = [
        {
            **row,
            "bridgeLabel": row.get("bridgeLabel") or _local_name(row.get("bridge")),
        }
        for row in response["results"]
    ]
    response["count"] = len(response["results"])
    return response


async def get_annotation_properties_tool(iri: str, repo: str | None = None) -> dict:
    sparql = f"""
{GRAPH_NATIVE_PREFIXES}
SELECT ?annotationProperty ?value ?lang WHERE {{
  VALUES ?annotationProperty {{
    rdfs:label rdfs:comment skos:prefLabel skos:altLabel
    skos:definition skos:example skos:note skos:scopeNote
    skos:editorialNote skos:historyNote
  }}
  <{iri}> ?annotationProperty ?value .
  BIND(LANG(?value) AS ?lang)
}} ORDER BY ?annotationProperty
"""
    response = await _run_query("get_annotation_properties", sparql, repo=repo, show_upper_ontology=True)
    response["results"] = [
        {
            **row,
            "annotationPropertyLabel": _local_name(row.get("annotationProperty")),
        }
        for row in response["results"]
    ]
    response["count"] = len(response["results"])
    return response


async def find_by_external_id_tool(id_value: str, id_property: str | None = None, repo: str | None = None) -> dict:
    escaped_value = _escape_literal(id_value)
    if id_property:
        value_pattern = f'?node <{id_property}> "{escaped_value}" .'
        if _is_iri(id_value):
            value_pattern = f"""
  {{
    ?node <{id_property}> "{escaped_value}" .
  }} UNION {{
    ?node <{id_property}> <{id_value}> .
  }}
"""
        sparql = f"""
{GRAPH_NATIVE_PREFIXES}
PREFIX schema: <https://schema.org/>
SELECT DISTINCT ?node ?nodeLabel ?nodeType WHERE {{
  {value_pattern}
  OPTIONAL {{ ?node rdfs:label|skos:prefLabel ?nodeLabel }}
  OPTIONAL {{ ?node a ?nodeType . FILTER(!isBlank(?nodeType)) }}
}} LIMIT 10
"""
    else:
        value_pattern = f"""
  VALUES ?identifierProperty {{
    schema:identifier schema:url owl:sameAs
    <http://purl.org/dc/terms/identifier>
    <http://www.w3.org/2004/02/skos/core#notation>
  }}
  ?node ?identifierProperty "{escaped_value}" .
"""
        if _is_iri(id_value):
            value_pattern = f"""
  {{
    VALUES ?identifierProperty {{
      schema:identifier schema:url owl:sameAs
      <http://purl.org/dc/terms/identifier>
      <http://www.w3.org/2004/02/skos/core#notation>
    }}
    ?node ?identifierProperty "{escaped_value}" .
  }} UNION {{
    VALUES ?identifierProperty {{
      schema:identifier schema:url owl:sameAs
      <http://purl.org/dc/terms/identifier>
      <http://www.w3.org/2004/02/skos/core#notation>
    }}
    ?node ?identifierProperty <{id_value}> .
  }}
"""
        sparql = f"""
{GRAPH_NATIVE_PREFIXES}
PREFIX schema: <https://schema.org/>
SELECT DISTINCT ?node ?nodeLabel ?nodeType ?identifierProperty WHERE {{
  {value_pattern}
  OPTIONAL {{ ?node rdfs:label|skos:prefLabel ?nodeLabel }}
  OPTIONAL {{ ?node a ?nodeType . FILTER(!isBlank(?nodeType)) }}
}} LIMIT 10
"""
    response = await _run_query("find_by_external_id", sparql, repo=repo, show_upper_ontology=True)
    normalized = []
    for row in response["results"]:
        candidate = {
            **row,
            "nodeLabel": row.get("nodeLabel") or _local_name(row.get("node")),
        }
        if _is_hidden_or_schema_type(candidate.get("nodeType")):
            candidate.pop("nodeType", None)
        normalized.append(candidate)
    response["results"] = normalized
    response["count"] = len(normalized)
    return response
