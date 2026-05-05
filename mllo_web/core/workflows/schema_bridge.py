from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from mllo_web.core.workflows.lineage import current_question_text


ML_NS = "http://www.semanticweb.org/mnd14/ml/"
BFO_NS = "http://purl.obolibrary.org/obo/"
IOF_CORE_NS = "https://spec.industrialontologies.org/ontology/core/Core/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"


def _iri(local: str, namespace: str = ML_NS) -> str:
    return f"{namespace}{local}"


def _local_name(iri: str | None) -> str:
    if not iri:
        return ""
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _iri_ref(iri: str) -> str:
    return f"<{iri}>"


@dataclass(frozen=True)
class ResolvedSeed:
    term: str
    iri: str
    classes: tuple[str, ...] = ()
    label: str | None = None


@dataclass(frozen=True)
class SchemaEdge:
    source_class: str
    property_iri: str
    target_class: str
    count: int = 1

    @property
    def source_local(self) -> str:
        return _local_name(self.source_class)

    @property
    def property_local(self) -> str:
        return _local_name(self.property_iri)

    @property
    def target_local(self) -> str:
        return _local_name(self.target_class)


@dataclass(frozen=True)
class SchemaPathStep:
    edge: SchemaEdge
    reversed: bool = False

    @property
    def source_class(self) -> str:
        return self.edge.target_class if self.reversed else self.edge.source_class

    @property
    def target_class(self) -> str:
        return self.edge.source_class if self.reversed else self.edge.target_class


@dataclass(frozen=True)
class SchemaBridgePath:
    score: float
    start_class: str
    target_class: str
    path: tuple[str, ...] = ()


@dataclass
class ObservedSchemaGraph:
    edges: tuple[SchemaEdge, ...]

    @property
    def class_iris(self) -> set[str]:
        return {edge.source_class for edge in self.edges} | {edge.target_class for edge in self.edges}

    @property
    def class_locals(self) -> set[str]:
        return {_local_name(iri) for iri in self.class_iris}

    @property
    def property_locals(self) -> set[str]:
        return {_local_name(edge.property_iri) for edge in self.edges}

    def neighbors(self, class_iri: str) -> list[SchemaPathStep]:
        steps: list[SchemaPathStep] = []
        for edge in self.edges:
            if edge.source_class == class_iri:
                steps.append(SchemaPathStep(edge=edge, reversed=False))
            if edge.target_class == class_iri:
                steps.append(SchemaPathStep(edge=edge, reversed=True))
        return steps

    def find_paths(self, seed_classes: set[str], target_classes: set[str], *, max_hops: int = 4, limit: int = 8) -> list[tuple[SchemaPathStep, ...]]:
        paths: list[tuple[SchemaPathStep, ...]] = []
        queue: list[tuple[str, tuple[SchemaPathStep, ...], set[str]]] = [
            (seed_class, (), {seed_class}) for seed_class in seed_classes if seed_class in self.class_iris
        ]
        while queue and len(paths) < limit:
            current, path, seen = queue.pop(0)
            if path and current in target_classes:
                paths.append(path)
                continue
            if len(path) >= max_hops:
                continue
            for step in self.neighbors(current):
                next_class = step.target_class
                if next_class in seen:
                    continue
                queue.append((next_class, (*path, step), {*seen, next_class}))
        return paths


OBSERVED_SCHEMA_QUERY = f"""
PREFIX rdf: <{RDF_NS}>
PREFIX rdfs: <{RDFS_NS}>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?source_class ?property ?target_class (COUNT(*) AS ?count) WHERE {{
  ?s ?property ?o .
  FILTER(isIRI(?s) && isIRI(?o))
  ?s rdf:type ?source_class .
  ?o rdf:type ?target_class .
  FILTER(?source_class != owl:NamedIndividual && ?target_class != owl:NamedIndividual)
  FILTER(
    STRSTARTS(STR(?property), "{ML_NS}") ||
    STRSTARTS(STR(?property), "{BFO_NS}") ||
    STRSTARTS(STR(?property), "{IOF_CORE_NS}")
  )
}}
GROUP BY ?source_class ?property ?target_class
ORDER BY DESC(?count)
LIMIT 1000
"""

_OBSERVED_SCHEMA_CACHE: dict[str, ObservedSchemaGraph] = {}


def build_observed_schema_graph(rows: list[dict[str, Any]]) -> ObservedSchemaGraph:
    edges: list[SchemaEdge] = []
    for row in rows:
        source_class = row.get("source_class")
        property_iri = row.get("property")
        target_class = row.get("target_class")
        if not source_class or not property_iri or not target_class:
            continue
        try:
            count = int(float(row.get("count") or 1))
        except (TypeError, ValueError):
            count = 1
        edges.append(SchemaEdge(source_class=source_class, property_iri=property_iri, target_class=target_class, count=count))
    return ObservedSchemaGraph(edges=tuple(edges))


async def load_observed_schema_graph(graphdb_client, repo: str) -> ObservedSchemaGraph:
    if repo in _OBSERVED_SCHEMA_CACHE:
        return _OBSERVED_SCHEMA_CACHE[repo]
    rows = await graphdb_client.query(OBSERVED_SCHEMA_QUERY, repo=repo, use_inference=False, show_upper_ontology=True)
    graph = build_observed_schema_graph(rows)
    _OBSERVED_SCHEMA_CACHE[repo] = graph
    return graph


def extract_seed_terms(question: str) -> list[str]:
    focused = current_question_text(question)
    terms: list[str] = []
    for iri in re.findall(r"https?://\S+", focused):
        terms.append(iri.rstrip(".,)"))
    for term in re.findall(r"\b[A-Z][A-Za-z0-9_:-]*\d+\b|\b[A-Z][A-Za-z0-9_:-]{3,}\b", focused):
        if term not in {"Which", "What", "Show", "Find", "Trace"} and term not in terms:
            terms.append(term)
    return terms


def seed_classes_from_question(question: str) -> set[str]:
    lowered = current_question_text(question).lower()
    classes: set[str] = set()
    has_specific_dataset_role = False
    if "test dataset" in lowered or "test data" in lowered:
        classes.add(_iri("TestDataSet"))
        has_specific_dataset_role = True
    if "training dataset" in lowered or "training data" in lowered:
        classes.add(_iri("TrainingDataSet"))
        has_specific_dataset_role = True
    if "model output" in lowered:
        classes.add(_iri("ModelOutputDataset"))
        has_specific_dataset_role = True
    if not has_specific_dataset_role and ("dataset" in lowered or "data set" in lowered):
        classes.add(_iri("MachineLearningDataSet"))
    if "model execution" in lowered:
        classes.add(_iri("ModelExecution"))
    return classes


def target_classes_from_question(question: str) -> set[str]:
    lowered = current_question_text(question).lower()
    classes: set[str] = set()
    if "model" in lowered:
        classes.add(_iri("MachineLearningModel"))
    if "pipeline" in lowered:
        classes.add(_iri("DataProcessingPipeline"))
        classes.add(_iri("MachineLearningModelDevelopmentPipeline"))
    if "evaluation" in lowered:
        classes.add(_iri("ModelEvaluation"))
        classes.add(_iri("ModelPerformanceAssessment"))
    if "model output" in lowered:
        classes.add(_iri("ModelOutputDataset"))
    if ("dataset" in lowered or "data set" in lowered) and "test dataset" not in lowered and "training dataset" not in lowered:
        classes.add(_iri("MachineLearningDataSet"))
    return classes


def is_performance_bridge_question(question: str) -> bool:
    lowered = current_question_text(question).lower()
    performance_words = ("performance", "perform", "accuracy", "score", "metric", "best", "top", "highest", "lowest", "worst")
    return "model" in lowered and any(word in lowered for word in performance_words)


def _path_hint(path: tuple[SchemaPathStep, ...], *, question: str) -> SchemaBridgePath | None:
    if not path:
        return None
    score = _score_path(path, question)
    readable_path = tuple(
        f"{_local_name(step.source_class)} {'<-' if step.reversed else '->'}{step.edge.property_local}-> {_local_name(step.target_class)}"
        for step in path
    )
    return SchemaBridgePath(
        score=score,
        start_class=path[0].source_class,
        target_class=path[-1].target_class,
        path=readable_path,
    )


def _score_path(path: tuple[SchemaPathStep, ...], question: str) -> float:
    lowered = current_question_text(question).lower()
    score = 20.0 - len(path)
    path_text = " ".join(
        " ".join(
            [
                _local_name(step.source_class),
                _local_name(step.edge.property_iri),
                _local_name(step.target_class),
            ]
        )
        for step in path
    ).lower()
    keyword_pairs = {
        "model": ("machinelearningmodel", "executes", "bfo_0000057"),
        "dataset": ("dataset", "hasdatainput", "hasdataoutput"),
        "pipeline": ("pipeline",),
        "evaluation": ("evaluation", "assessment"),
        "performance": ("performance", "evaluation", "assessment", "metric", "hasdatainput", "hasdataoutput"),
        "perform": ("performance", "evaluation", "assessment", "metric", "hasdatainput", "hasdataoutput"),
        "score": ("performance", "evaluation", "metric", "hasdatainput", "hasdataoutput"),
    }
    for word, boosts in keyword_pairs.items():
        if word in lowered and any(boost in path_text for boost in boosts):
            score += 5
    score += min(sum(step.edge.count for step in path), 100) / 100
    return score


async def resolve_seed_terms(question: str, graphdb_client, repo: str) -> list[ResolvedSeed]:
    terms = extract_seed_terms(question)
    if not terms:
        return []
    values = " ".join(f'"{term.replace(chr(34), chr(92) + chr(34))}"' for term in terms)
    query = f"""
PREFIX rdf: <{RDF_NS}>
PREFIX rdfs: <{RDFS_NS}>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?term ?node ?label ?class WHERE {{
  VALUES ?term {{ {values} }}
  {{
    ?node ?p ?o .
    FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE(?term))
  }}
  UNION
  {{
    ?node rdfs:label ?label .
    FILTER(LCASE(STR(?label)) = LCASE(?term))
  }}
  OPTIONAL {{ ?node rdfs:label ?label }}
  OPTIONAL {{
    ?node rdf:type/rdfs:subClassOf* ?class .
    FILTER(?class != owl:NamedIndividual)
  }}
}}
LIMIT 100
"""
    rows = await graphdb_client.query(query, repo=repo, use_inference=False, show_upper_ontology=True)
    by_node: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        term = row.get("term")
        node = row.get("node")
        if not term or not node:
            continue
        bucket = by_node.setdefault((term, node), {"term": term, "node": node, "label": row.get("label"), "classes": []})
        if row.get("class") and row["class"] not in bucket["classes"]:
            bucket["classes"].append(row["class"])
    return [
        ResolvedSeed(term=item["term"], iri=item["node"], label=item.get("label"), classes=tuple(item.get("classes") or ()))
        for item in by_node.values()
    ]


async def schema_bridge_grounding(question: str, graphdb_client, repo: str) -> dict[str, Any]:
    focused = current_question_text(question)
    try:
        graph = await load_observed_schema_graph(graphdb_client, repo)
    except Exception:
        return {}
    if not graph.edges:
        return {}

    seed_classes = seed_classes_from_question(focused)
    try:
        resolved_seeds = await resolve_seed_terms(focused, graphdb_client, repo)
    except Exception:
            resolved_seeds = []
    for seed in resolved_seeds:
        seed_classes.update(cls for cls in seed.classes if cls in graph.class_iris)

    target_classes = target_classes_from_question(focused)
    if is_performance_bridge_question(focused):
        target_classes.update(
            {
                _iri("MachineLearningModel"),
                _iri("ModelEvaluation"),
                _iri("ModelPerformanceAssessment"),
                _iri("ModelPerformanceResult"),
                _iri("PerformanceMetric"),
                _iri("ClassificationAccuracy"),
            }
        )

    path_hints: list[SchemaBridgePath] = []
    if seed_classes and target_classes:
        for path in graph.find_paths(seed_classes, target_classes, max_hops=5, limit=12):
            hint = _path_hint(path, question=focused)
            if hint:
                path_hints.append(hint)

    edge_keywords = {
        "model": ("MachineLearningModel", "ModelExecution", "executes", "BFO_0000057"),
        "performance": ("ModelPerformanceAssessment", "PerformanceMetric", "hasSimpleExpressionValue"),
        "perform": ("ModelPerformanceAssessment", "PerformanceMetric", "hasSimpleExpressionValue"),
        "score": ("ModelPerformanceAssessment", "PerformanceMetric", "hasSimpleExpressionValue"),
        "accuracy": ("ModelPerformanceAssessment", "PerformanceMetric", "ClassificationAccuracy"),
        "dataset": ("DataSet", "TestDataSet", "TrainingDataSet", "hasDataInput", "hasDataOutput"),
        "pipeline": ("Pipeline", "hasDataInput", "hasDataOutput"),
        "evaluation": ("ModelEvaluation", "ModelPerformanceAssessment"),
    }
    lowered = focused.lower()
    relevant_edge_rows: list[dict[str, Any]] = []
    for edge in sorted(graph.edges, key=lambda item: item.count, reverse=True):
        edge_text = " ".join([edge.source_local, edge.property_local, edge.target_local])
        if any(word in lowered and any(token.lower() in edge_text.lower() for token in tokens) for word, tokens in edge_keywords.items()):
            relevant_edge_rows.append(
                {
                    "source_class": edge.source_local,
                    "property": edge.property_local,
                    "target_class": edge.target_local,
                    "count": edge.count,
                }
            )
        if len(relevant_edge_rows) >= 20:
            break

    unique_paths: dict[tuple[str, ...], SchemaBridgePath] = {}
    for hint in sorted(path_hints, key=lambda item: item.score, reverse=True):
        unique_paths.setdefault(hint.path, hint)
    return {
        "seed_terms": [
            {
                "term": seed.term,
                "iri": seed.iri,
                "label": seed.label,
                "classes": [_local_name(cls) for cls in seed.classes],
            }
            for seed in resolved_seeds
        ],
        "seed_classes": [_local_name(cls) for cls in sorted(seed_classes)],
        "target_classes": [_local_name(cls) for cls in sorted(target_classes)],
        "candidate_class_paths": [
            {
                "score": hint.score,
                "start_class": _local_name(hint.start_class),
                "target_class": _local_name(hint.target_class),
                "path": list(hint.path),
            }
            for hint in list(unique_paths.values())[:8]
        ],
        "relevant_observed_edges": relevant_edge_rows,
        "instruction": (
            "Use these observed class-level paths and edges as grounding evidence. "
            "Generate the SPARQL yourself from the shown classes/properties; do not assume a direct individual link if the evidence shows a process-mediated bridge."
        ),
    }
