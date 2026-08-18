from __future__ import annotations

import re

from fastapi import HTTPException

from mllo_web.core.llm import LLMServiceError
from mllo_web.core.workflows.ontology import build_relevant_subgraph, load_ontology_context, ontology_context_to_text
from mllo_web.core.workflows.shared import active_provider_config

SYSTEM_MESSAGE = (
    "You are an expert Semantic Web engineer specialising in the MLLO (Machine Learning Lifecycle Ontology).\n"
    "Generate ONLY valid SPARQL that strictly follows the provided ontology schema and example queries.\n\n"
    "ENTITY DEFINITIONS in MLLO:\n"
    "- DATASET: an entity used as input to an ML process via ?process ml:hasDataInput ?dataset.\n"
    "- MODEL: a MachineLearningModel linked from an ML process via ?process (ml:executed | bfo:BFO_0000057) ?model.\n"
    "- PIPELINE: a DataProcessingPipeline or MachineLearningModelDevelopmentPipeline with components via bfo:BFO_0000117.\n"
    "- ML PROCESS: the central node linking models, datasets, inputs, and outputs.\n\n"
    "KEY PATTERNS:\n"
    "- ML processes link to models via: ?process (ml:executed | bfo:BFO_0000057) ?model\n"
    "- ML processes consume datasets via: ?process ml:hasDataInput ?dataset\n"
    "- ML processes produce datasets via: ?process ml:hasDataOutput ?dataset\n"
    "- Never reverse hasDataInput or hasDataOutput: the process is the subject and the dataset is the object.\n"
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

EXAMPLE_QUERIES = """=== EXAMPLE QUERIES ===

# Datasets consumed by processes that execute a model
SELECT DISTINCT ?dataset WHERE {
  ?process (ml:executed | bfo:BFO_0000057) ?model .
  ?process ml:hasDataInput ?dataset .
  ?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
}
LIMIT 100

# Datasets produced downstream from a model output
SELECT DISTINCT ?dataset WHERE {
  ?model_process ml:executed ?model ;
                 ml:hasDataOutput ?model_output .
  ?downstream_process ml:hasDataInput ?model_output ;
                      ml:hasDataOutput ?dataset .
}
LIMIT 100

# Models and pipelines that share a dataset
SELECT DISTINCT ?model ?pipeline ?dataset WHERE {
  ?model_process (ml:executed | bfo:BFO_0000057) ?model ;
                 ml:hasDataInput ?dataset .
  ?pipeline (ml:hasDataInput | ml:hasDataOutput) ?dataset .
}
LIMIT 100

# Model outputs later consumed by another process
SELECT DISTINCT ?output_dataset WHERE {
  ?model_process ml:executed ?model ;
                 ml:hasDataOutput ?output_dataset .
  ?next_process ml:hasDataInput ?output_dataset .
}
LIMIT 100"""


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


def inject_prefixes(sparql: str, ctx: dict) -> str:
    prefix_map = dict(ctx["prefixes"])
    declared = {match.group(1) for match in re.finditer(r"PREFIX\s+(\w[\w-]*):\s*<[^>]+>", sparql, re.IGNORECASE)}
    body = "\n".join(line for line in sparql.split("\n") if not line.strip().upper().startswith("PREFIX"))
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
    body = "\n".join(line for line in sparql.split("\n") if not line.strip().upper().startswith("PREFIX"))
    used_prefixes = set(re.findall(r"(\b\w[\w-]*):", body))
    used_prefixes -= {"http", "https", "urn", "mailto", "tel", "ftp"}
    for prefix in used_prefixes:
        if prefix not in declared_prefixes and prefix not in prefix_map:
            errors.append(f"Undefined prefix used: {prefix}:")
    prefixed_names = re.findall(r"(\b\w[\w-]*):(\w+)", body)
    all_known = known_class_iris | known_prop_iris | known_individual_iris
    known_local_names = {iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1] for iri in all_known}
    skip_prefixes = {"rdf", "rdfs", "owl", "xsd", "skos", "dcterms", "dc", "foaf", "sh"}
    for prefix, local in prefixed_names:
        if prefix in skip_prefixes:
            continue
        namespace = declared_prefixes.get(prefix) or prefix_map.get(prefix)
        if namespace and (namespace + local) not in all_known and local not in known_local_names:
            if not re.match(r"[A-Z]+_\d+", local):
                errors.append(f"Term not in ontology: {prefix}:{local}")
    return errors


async def generate_sparql(question: str, repo: str, settings, graphdb_client, gateway) -> tuple[str, dict]:
    ctx = await load_ontology_context(graphdb_client, repo)
    prompt_ctx = build_relevant_subgraph(ctx, question)
    ontology_text = ontology_context_to_text(prompt_ctx)
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
    if errors:
        repair_messages = messages + [
            {"role": "assistant", "content": sparql},
            {"role": "user", "content": f"{REPAIR_MESSAGE}\n\nValidation errors:\n- " + "\n- ".join(errors)},
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
        if errors:
            raise HTTPException(status_code=422, detail="Generated SPARQL could not be validated.")
    return inject_prefixes(sparql, ctx), ctx
