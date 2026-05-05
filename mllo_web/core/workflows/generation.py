from __future__ import annotations

import json
import re

from fastapi import HTTPException

from mllo_web.core.llm import LLMServiceError
from mllo_web.core.workflows.lineage import current_question_text
from mllo_web.core.workflows.ontology import build_relevant_subgraph, load_ontology_context, ontology_context_to_text
from mllo_web.core.workflows.shared import active_provider_config

PURE_SYSTEM_MESSAGE = (
    "You generate SPARQL for a selected RDF repository.\n"
    "Use only the provided ontology schema and graph observations as evidence.\n\n"
    "IMPORTANT RULES:\n"
    "- Do not invent classes, properties, individuals, or IRIs.\n"
    "- Use only the listed prefixes and vocabulary.\n"
    "- Always include LIMIT 100 unless the user explicitly asks for all results.\n"
    "- If the question cannot be answered from the provided context, return exactly: CANNOT_ANSWER_WITH_ONTOLOGY\n"
    "- Return ONLY the SPARQL query, with no markdown fences."
)

ENHANCED_SYSTEM_MESSAGE = (
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

# Backwards-compatible alias for older call sites. Enhanced mode is the only
# path that should use the historical prompt with examples and MLLO patterns.
SYSTEM_MESSAGE = ENHANCED_SYSTEM_MESSAGE

REPAIR_MESSAGE = (
    "The previous SPARQL was invalid for this ontology or could not be parsed. "
    "Fix it strictly using the provided ontology vocabulary and return ONLY corrected SPARQL."
)

EXAMPLE_QUERIES = """
=== EXAMPLE QUERIES ===

Models above an accuracy threshold, with the exact execution process and test dataset:
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?model_name ?ml_process ?test_dataset ?pipeline ?model_performance_value WHERE {
  ?ml_process (ml:executes|bfo:BFO_0000057) ?model_name .
  BIND(?ml_process AS ?pipeline)
  ?model_name rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
  ?ml_process ml:hasDataInput ?test_dataset .
  ?test_dataset rdf:type/rdfs:subClassOf* ml:TestDataSet .
  ?model_performance_assessment ml:hasDataInput ?model_output .
  ?ml_process ml:hasDataOutput ?model_output .
  ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment .
  ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
  ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
  ?model_performance_metric_type rdfs:subClassOf* ml:PerformanceMetric .
  ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
  FILTER(xsd:decimal(?model_performance_value) > 0.9)
}
LIMIT 100

When the user asks for the pipeline of a model execution/performance row, use BIND(?ml_process AS ?pipeline) unless they explicitly ask for a containing parent pipeline. Do not require ?pipeline rdf:type ml:MachineLearningModelDevelopmentPipeline for execution-level results.

Models and pipelines that share the same dataset:
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model ?pipeline ?dataset WHERE {
  ?model_process (ml:executes|bfo:BFO_0000057) ?model .
  ?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
  ?model_process ml:hasDataInput ?dataset .
  ?pipeline ml:hasDataInput|ml:hasDataOutput ?dataset .
  ?pipeline rdf:type/rdfs:subClassOf* ml:DataProcessingPipeline .
}
LIMIT 100

Pipelines associated with a model:
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?pipeline WHERE {
  ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model .
  ?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
  FILTER(STRAFTER(STR(?model), "#") = "MLModel1")
}
LIMIT 100

Downstream artifacts from a named dataset:
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?downstream_dataset ?downstream_process WHERE {
  ?start_dataset rdf:type/rdfs:subClassOf* ?start_type .
  FILTER(LCASE(STRAFTER(STR(?start_dataset), "#")) = LCASE("MnistG16"))
  ?downstream_process ml:hasDataInput ?start_dataset .
  ?downstream_process ml:hasDataOutput ?downstream_dataset .
}
LIMIT 100

Upstream inputs that produced a named dataset:
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?upstream_dataset ?upstream_process WHERE {
  ?target_dataset rdf:type/rdfs:subClassOf* ?target_type .
  FILTER(LCASE(STRAFTER(STR(?target_dataset), "#")) = LCASE("PreprocessedDataset1"))
  ?upstream_process ml:hasDataOutput ?target_dataset .
  ?upstream_process ml:hasDataInput ?upstream_dataset .
}
LIMIT 100

Pipeline or process that produced a named dataset:
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?pipeline ?dataset WHERE {
  ?dataset rdf:type/rdfs:subClassOf* ?dataset_type .
  FILTER(LCASE(STRAFTER(STR(?dataset), "#")) = LCASE("PreprocessedDataset1"))
  ?process ml:hasDataOutput ?dataset .
  BIND(?process AS ?pipeline)
}
LIMIT 100
"""


def sparql_system_message(enhanced_prompt: bool = False) -> str:
    return ENHANCED_SYSTEM_MESSAGE if enhanced_prompt else PURE_SYSTEM_MESSAGE


def _is_enhanced_prompt(enhanced_prompt: bool, grounding_context: dict | None = None) -> bool:
    if enhanced_prompt:
        return True
    prompt_mode = (grounding_context or {}).get("prompt_mode")
    return prompt_mode in {"enhanced", "enhanced_schema_grounding"}


def _format_grounding_context(grounding_context: dict | None) -> str:
    if not grounding_context:
        return ""
    compact = json.dumps(grounding_context, ensure_ascii=False, separators=(",", ":"))
    return f"\n\nGraph observations:\n{compact}"


def _enhanced_prompt_rules() -> str:
    return (
        "Name matching rule: named instances in this graph often have no rdfs:label. "
        "When matching a named artifact such as MnistG16 or PreprocessedDataset1, use "
        'FILTER(LCASE(STRAFTER(STR(?node), "#")) = LCASE("Name")) or a full IRI; do not rely only on rdfs:label.\n\n'
        "Dataset type rule: raw datasets, preprocessed datasets, and ML datasets may be siblings. "
        "For lineage/data-flow questions about a named dataset, bind the named node with "
        "?dataset rdf:type/rdfs:subClassOf* ?dataset_type and avoid narrowing it to ml:MachineLearningDataSet unless the user explicitly asks for that class.\n\n"
        "Schema grounding rule: if graph observations include schema_bridge_grounding, use its observed class paths and edges as evidence for how to connect classes. "
        "You still must generate the SPARQL yourself; the grounding is not a final answer. Prefer process-mediated bridges shown there over guessing direct links.\n\n"
        f"{EXAMPLE_QUERIES}\n\n"
    )


def build_sparql_generation_messages(
    focused_question: str,
    ontology_text: str,
    grounding_context: dict | None = None,
    *,
    enhanced_prompt: bool = False,
) -> list[dict[str, str]]:
    enhanced_prompt = _is_enhanced_prompt(enhanced_prompt, grounding_context)
    grounding_text = _format_grounding_context(grounding_context)
    if enhanced_prompt:
        mode_specific_prompt = _enhanced_prompt_rules()
        final_instruction = "Use ONLY the listed classes, properties, individuals, and prefixes."
    else:
        mode_specific_prompt = (
            "Pure node-hop mode: use the provided ontology schema and graph observations directly. "
            "Base every class, property, and named node on text shown in this prompt. "
            "If observed_bridge_patterns are present, treat them as condensed evidence discovered from node hops and use them before raw rows: "
            "literal_value is the measured literal, shared_neighbor is the bridge artifact, bridge_node is the connected process, "
            "and bridge_out_neighbor values are candidate answer nodes. "
            "If observed_join_skeletons are present, prefer those exact observed paths over inferred direct links.\n\n"
        )
        final_instruction = "Use ONLY the listed ontology vocabulary, prefixes, and observed graph hops."
    return [
        {"role": "system", "content": sparql_system_message(enhanced_prompt)},
        {
            "role": "user",
            "content": (
                f"User question: {focused_question}\n\n"
                f"Ontology schema:\n{ontology_text}\n\n"
                f"{mode_specific_prompt}"
                f"{grounding_text}\n\n"
                "Generate a SPARQL SELECT query to answer the question. "
                f"{final_instruction}"
            ),
        },
    ]


def build_empty_result_repair_messages(
    question: str,
    sparql: str,
    ctx: dict,
    grounding_context: dict | None = None,
    *,
    enhanced_prompt: bool = False,
) -> list[dict[str, str]]:
    focused_question = current_question_text(question)
    enhanced_prompt = _is_enhanced_prompt(enhanced_prompt, grounding_context)
    prompt_ctx = build_relevant_subgraph(ctx, focused_question)
    ontology_text = ontology_context_to_text(prompt_ctx)
    grounding_text = _format_grounding_context(grounding_context)
    if enhanced_prompt:
        repair_guidance = (
            f"{_enhanced_prompt_rules()}"
            "The SPARQL below executed successfully but returned zero rows. "
            "Revise it using the same ontology vocabulary. Prefer local-name matching with STRAFTER(STR(?iri), \"#\") "
            "for named artifacts instead of requiring rdfs:label. Keep the answer as SELECT SPARQL only."
        )
    else:
        repair_guidance = (
            "The SPARQL below executed successfully but returned zero rows or semantically invalid rows. "
            "Revise it using only the ontology schema and graph observations in this prompt. "
            "Do not add classes, properties, individuals, or IRIs that are not present here. "
            "If answer_semantic_debug is present, the selected columns did not satisfy the user's requested answer slots; "
            "add or replace selected variables so model, performance value, dataset, and pipeline slots are bound to the requested graph nodes. "
            "If performance_value is missing and answer_semantic_debug lists numeric_filter_variables, include the relevant numeric variable in SELECT. "
            "If model is missing, look for observed bridge_out_property or pivot_property edges that point to model-like neighbors and bind/select that neighbor. "
            "If observed_bridge_patterns are present, use them as compact route evidence discovered from node hops: "
            "the bridge_node may be the requested process/pipeline, and bridge_out_neighbor values may be the requested model or dataset. "
            "If sparql_empty_result_debug is present, inspect join_route_debug first: "
            "replace the first_zero_join clause/filter or any route segment whose cumulative_count collapses to zero. "
            "If numeric_filter_cast_candidate or join_route_debug_after_numeric_cast is present, use xsd:decimal(...) for numeric literal comparisons. "
            "Use variable_samples_at_collapse, variable_neighborhoods_at_collapse, and pivot_contexts_at_collapse to identify actual classes/types, bridge nodes, and neighboring nodes. "
            "If a variable bound earlier has a different actual type than a later class constraint, treat that variable as a bridge and find the requested class through observed neighboring nodes instead of forcing the wrong type. "
            "Remove or replace zero-support predicates/classes unless an observed join skeleton supports them. "
            "Keep the answer as SELECT SPARQL only."
        )
    return [
        {"role": "system", "content": sparql_system_message(enhanced_prompt)},
        {
            "role": "user",
            "content": (
                f"Question: {focused_question}\n\n"
                f"Ontology schema:\n{ontology_text}"
                f"{grounding_text}\n\n"
                f"{repair_guidance}\n\n"
                f"Previous SPARQL:\n{sparql}"
            ),
        },
    ]


def build_execution_repair_messages(sparql: str, error: Exception | str, *, enhanced_prompt: bool = False) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": sparql_system_message(enhanced_prompt)},
        {"role": "assistant", "content": sparql},
        {"role": "user", "content": f"{REPAIR_MESSAGE}\n\nExecution error:\n{error}"},
    ]


def extract_sparql(raw: str) -> str:
    match = re.search(r"```(?:sparql)?\s*(.+?)```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    for keyword in ("SELECT", "ASK", "CONSTRUCT", "DESCRIBE", "PREFIX"):
        idx = raw.upper().find(keyword)
        if idx != -1:
            return raw[idx:].strip()
    return raw.strip()


def contains_cannot_answer(text: str) -> bool:
    return "CANNOT_ANSWER_WITH_ONTOLOGY" in (text or "").upper()


def strip_sparql_comments(sparql: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in sparql.splitlines())


def inject_prefixes(sparql: str, ctx: dict) -> str:
    prefix_map = dict(ctx["prefixes"])
    declared = {match.group(1) for match in re.finditer(r"PREFIX\s+(\w[\w-]*):\s*<[^>]+>", sparql, re.IGNORECASE)}
    body = strip_sparql_comments("\n".join(line for line in sparql.split("\n") if not line.strip().upper().startswith("PREFIX")))
    used = set(re.findall(r"(\b\w[\w-]*):", body))
    used -= {"http", "https", "urn", "mailto", "tel", "ftp"}
    missing = [f"PREFIX {prefix}: <{prefix_map[prefix]}>" for prefix in sorted(used) if prefix not in declared and prefix in prefix_map]
    return ("\n".join(missing) + "\n" + sparql) if missing else sparql


def validate_sparql(sparql: str, ctx: dict) -> list[str]:
    errors = []
    known_class_iris = {item["iri"] for item in ctx["classes"]}
    known_individual_iris = {item["iri"] for item in ctx.get("individuals", [])}
    known_prop_iris = {
        item["iri"]
        for collection in (ctx["object_properties"], ctx["datatype_properties"], ctx["annotation_properties"])
        for item in collection
    }
    prefix_map = dict(ctx["prefixes"])
    declared_prefixes = {match.group(1): match.group(2) for match in re.finditer(r"PREFIX\s+(\w[\w-]*):\s*<([^>]+)>", sparql, re.IGNORECASE)}
    body = strip_sparql_comments("\n".join(line for line in sparql.split("\n") if not line.strip().upper().startswith("PREFIX")))
    used_prefixes = set(re.findall(r"(\b\w[\w-]*):", body))
    used_prefixes -= {"http", "https", "urn", "mailto", "tel", "ftp"}
    for prefix in used_prefixes:
        if prefix not in declared_prefixes and prefix not in prefix_map:
            errors.append(f"Undefined prefix used: {prefix}:")
    all_known = known_class_iris | known_prop_iris | known_individual_iris
    known_local_names = {iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1] for iri in all_known}
    class_local_names = {iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1] for iri in known_class_iris}
    prop_local_names = {iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1] for iri in known_prop_iris}
    skip_prefixes = {"rdf", "rdfs", "owl", "xsd", "skos", "dcterms", "dc", "foaf", "sh", "bfo", "iof-core"}

    def is_unknown_term(prefix: str, local: str) -> bool:
        if prefix in skip_prefixes:
            return False
        namespace = declared_prefixes.get(prefix) or prefix_map.get(prefix)
        if not namespace:
            return False
        return (namespace + local) not in all_known and local not in known_local_names and not re.match(r"[A-Z]+_\d+", local)

    # Unknown prefixed terms are acceptable as named individuals in subject/object
    # position, but not as classes or properties.
    for prefix, local in re.findall(r"(?:\ba\s+|\brdf:type(?:/rdfs:subClassOf[*+]?)?\s+)(\w[\w-]*):(\w+)", body):
        if is_unknown_term(prefix, local):
            errors.append(f"Class term not in ontology: {prefix}:{local}")
    for prefix, local in re.findall(r"(?:^|[;{.]\s*|\]\s*)\??[\w-]+\s+(\w[\w-]*):(\w+)\s+", body):
        if is_unknown_term(prefix, local):
            errors.append(f"Property term not in ontology: {prefix}:{local}")
    for prefix, local in re.findall(r"[/|^]\s*(\w[\w-]*):(\w+)", body):
        if prefix not in skip_prefixes and local in class_local_names:
            errors.append(f"Class used as property-path predicate: {prefix}:{local}")
        elif is_unknown_term(prefix, local) and local not in prop_local_names:
            errors.append(f"Property-path term not in ontology: {prefix}:{local}")
    return errors


def fatal_validation_errors(errors: list[str]) -> list[str]:
    fatal_prefixes = (
        "Undefined prefix used:",
        "Class used as property-path predicate:",
        "Property-path term not in ontology:",
    )
    return [error for error in errors if error.startswith(fatal_prefixes)]


def empty_result_fallback_candidates(sparql: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []

    def add(reason: str, candidate: str) -> None:
        normalized = candidate.strip()
        if normalized and normalized != sparql.strip() and all(existing != normalized for _, existing in candidates):
            candidates.append((reason, normalized))

    # Many failed custom queries are valid SPARQL but over-constrain a named
    # artifact with rdfs:label even though MLLE instance names live in IRI
    # local names. Convert common typed-label blocks into local-name matching.
    def replace_typed_label_block(match: re.Match[str]) -> str:
        var_name, label = match.groups()
        return (
            f"{var_name} rdf:type/rdfs:subClassOf* ?{var_name.lstrip('?')}_type .\n"
            f'  FILTER(LCASE(STRAFTER(STR({var_name}), "#")) = LCASE("{label}"))'
        )

    label_relaxed = re.sub(
        r"(\?\w+)\s+a\s+[\w-]+:\w+\s*;\s*\n\s*rdfs:label\s+\"([^\"]+)\"\s*\.",
        replace_typed_label_block,
        sparql,
        flags=re.IGNORECASE,
    )
    label_relaxed = re.sub(
        r"(\?\w+)\s+rdfs:label\s+\"([^\"]+)\"\s*\.",
        lambda match: f'FILTER(LCASE(STRAFTER(STR({match.group(1)}), "#")) = LCASE("{match.group(2)}"))',
        label_relaxed,
        flags=re.IGNORECASE,
    )
    add("replace_label_constraints_with_iri_local_name_matching", label_relaxed)

    # If a query returns no rows, class restrictions on variables are often the
    # brittle part. Keep data-flow/property joins and local-name filters intact,
    # but remove simple rdf:type constraints on variables.
    type_relaxed = re.sub(
        r"(?m)^\s*\?\w+\s+(?:a|rdf:type)(?:/rdfs:subClassOf[*+]?)?\s+[\w-]+:\w+\s*\.\s*\n?",
        "",
        sparql,
    )
    type_relaxed = re.sub(
        r"(?m)^\s*\?\w+\s+rdf:type\s+\?\w+\s*\.\s*\n?",
        "",
        type_relaxed,
    )
    type_relaxed = re.sub(
        r"(?m)^\s*\?\w+\s+rdf:type/rdfs:subClassOf[*+]?\s+\?\w+\s*\.\s*\n?",
        "",
        type_relaxed,
    )
    add("remove_simple_variable_type_constraints", type_relaxed)

    label_and_type_relaxed = re.sub(
        r"(?m)^\s*\?\w+\s+(?:a|rdf:type)(?:/rdfs:subClassOf[*+]?)?\s+[\w-]+:\w+\s*\.\s*\n?",
        "",
        label_relaxed,
    )
    label_and_type_relaxed = re.sub(
        r"(?m)^\s*\?\w+\s+rdf:type\s+\?\w+\s*\.\s*\n?",
        "",
        label_and_type_relaxed,
    )
    label_and_type_relaxed = re.sub(
        r"(?m)^\s*\?\w+\s+rdf:type/rdfs:subClassOf[*+]?\s+\?\w+\s*\.\s*\n?",
        "",
        label_and_type_relaxed,
    )
    add("replace_labels_and_remove_type_constraints", label_and_type_relaxed)
    return candidates


def relationship_fallback_candidates(question: str) -> list[tuple[str, str]]:
    focused_question = current_question_text(question)
    lowered = focused_question.lower()
    candidates: list[tuple[str, str]] = []

    def add(reason: str, candidate: str) -> None:
        normalized = candidate.strip()
        if normalized and all(existing != normalized for _, existing in candidates):
            candidates.append((reason, normalized))

    if "model output" in lowered and ("later" in lowered or "input" in lowered or "another process" in lowered):
        add(
            "model_output_reused_as_downstream_input",
            """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?output_dataset ?downstream_process WHERE {
  ?upstream_process (ml:executes|bfo:BFO_0000057) ?model .
  ?upstream_process ml:hasDataOutput ?output_dataset .
  ?downstream_process ml:hasDataInput ?output_dataset .
  FILTER(?downstream_process != ?upstream_process)
}
LIMIT 100
""",
        )

    if "produced" in lowered and "process" in lowered and "use" in lowered and "model output" in lowered:
        add(
            "datasets_produced_by_processes_using_model_output",
            """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?dataset ?process ?input_artifact WHERE {
  ?producer_process (ml:executes|bfo:BFO_0000057) ?model .
  ?producer_process ml:hasDataOutput ?input_artifact .
  ?process ml:hasDataInput ?input_artifact .
  ?process ml:hasDataOutput ?dataset .
  FILTER(?dataset != ?input_artifact)
}
LIMIT 100
""",
        )

    if "share" in lowered and "dataset" in lowered and "model" in lowered and "pipeline" in lowered:
        add(
            "models_and_pipelines_sharing_dataset",
            """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?model ?pipeline ?dataset WHERE {
  ?model_process (ml:executes|bfo:BFO_0000057) ?model .
  ?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
  ?model_process ml:hasDataInput ?dataset .
  ?pipeline ml:hasDataInput|ml:hasDataOutput ?dataset .
  ?pipeline rdf:type/rdfs:subClassOf* ml:DataProcessingPipeline .
}
LIMIT 100
""",
        )

    return candidates


async def generate_sparql(
    question: str,
    repo: str,
    settings,
    graphdb_client,
    gateway,
    grounding_context: dict | None = None,
    *,
    enhanced_prompt: bool = False,
) -> tuple[str, dict]:
    focused_question = current_question_text(question)
    ctx = await load_ontology_context(graphdb_client, repo)
    prompt_ctx = build_relevant_subgraph(ctx, focused_question)
    ontology_text = ontology_context_to_text(prompt_ctx)
    enhanced_prompt = _is_enhanced_prompt(enhanced_prompt, grounding_context)
    messages = build_sparql_generation_messages(focused_question, ontology_text, grounding_context, enhanced_prompt=enhanced_prompt)
    provider_config = active_provider_config(settings)
    try:
        raw_sparql = await gateway.chat_completion(messages, provider_config, purpose="sparql_generation")
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if contains_cannot_answer(raw_sparql):
        raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
    sparql = extract_sparql(raw_sparql)
    if contains_cannot_answer(sparql):
        raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
    errors = validate_sparql(sparql, ctx)
    fatal_errors = fatal_validation_errors(errors)
    if fatal_errors:
        repair_messages = messages + [
            {"role": "assistant", "content": sparql},
            {"role": "user", "content": f"{REPAIR_MESSAGE}\n\nValidation errors:\n- " + "\n- ".join(fatal_errors)},
        ]
        try:
            repaired = await gateway.chat_completion(repair_messages, provider_config, purpose="sparql_repair_validation")
            if contains_cannot_answer(repaired):
                raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
            sparql = extract_sparql(repaired)
            if contains_cannot_answer(sparql):
                raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
        except LLMServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        errors = validate_sparql(sparql, ctx)
        fatal_errors = fatal_validation_errors(errors)
        if fatal_errors:
            raise HTTPException(status_code=422, detail="Generated SPARQL could not be validated.")
    return inject_prefixes(sparql, ctx), ctx
