import logging
import re

import httpx

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Configuration – adjust these or pull from app.state / env vars
# ──────────────────────────────────────────────────────────────────────
LLM_BASE_URL = "http://localhost:1234/v1"          # LM Studio OpenAI-compat endpoint
LLM_MODEL    = "openai/gpt-oss-120b"                 # model name loaded in LM Studio
MAX_REPAIR_ATTEMPTS = 10                             # how many times to retry invalid SPARQL

# Named graph that holds the ontology in GraphDB / Mobi
ONTOLOGY_GRAPH = "http://www.semanticweb.org/mnd14/ml/"

# ──────────────────────────────────────────────────────────────────────
# 1. Fetch ontology schema from GraphDB
# ──────────────────────────────────────────────────────────────────────
ONTOLOGY_SCHEMA_QUERY = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT
    ?type           # 'Class' | 'ObjectProperty' | 'DatatypeProperty' | 'AnnotationProperty'
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
        OPTIONAL { ?entity rdfs:subClassOf ?domain }   # reuse column for superclass
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

PREFIX_QUERY = """
PREFIX sh: <http://www.w3.org/ns/shacl#>
SELECT DISTINCT ?prefix ?namespace
WHERE {
    {
        # Try to get declared prefixes from SHACL or owl:Ontology
        ?ont a owl:Ontology .
        ?ont sh:declare ?decl .
        ?decl sh:prefix ?prefix .
        ?decl sh:namespace ?namespace .
    }
    UNION
    {
        # Fallback: extract namespaces from entity IRIs
        ?entity rdf:type ?t .
        FILTER(?t IN (owl:Class, owl:ObjectProperty, owl:DatatypeProperty))
        BIND(REPLACE(STR(?entity), "[^/#]*$", "") AS ?namespace)
        BIND(REPLACE(STR(?entity), "^.*[/#]", "") AS ?localname)
        # We cannot auto-derive prefix names in pure SPARQL, so leave blank
        BIND("" AS ?prefix)
    }
}
"""


def _build_ontology_context(schema_rows: list, prefix_rows: list, sample_rows: list) -> dict:
    """Organise raw SPARQL results into a structured ontology context dict."""

    def _is_valid_iri(iri: str) -> bool:
        """Reject Mobi's opaque hash IDs and other non-HTTP identifiers."""
        return bool(iri) and (iri.startswith("http://") or iri.startswith("https://"))

    classes = []
    object_properties = []
    datatype_properties = []
    annotation_properties = []

    for row in schema_rows:
        iri = row.get("entity") or ""
        if not _is_valid_iri(iri):
            continue  # skip Mobi hash IDs like "26cee95e9edf402b..."
        entry = {
            "iri": iri,
            "label": row.get("label") or "",
        }
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

    # Deduplicate namespaces and build prefix map
    ns_set: dict[str, str] = {}
    # Well-known prefixes always available
    well_known = {
        "rdf":      "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs":     "http://www.w3.org/2000/01/rdf-schema#",
        "owl":      "http://www.w3.org/2002/07/owl#",
        "xsd":      "http://www.w3.org/2001/XMLSchema#",
        "ml":       "http://www.semanticweb.org/mnd14/ml/",
        "bfo":      "http://purl.obolibrary.org/obo/",
        "iof-core": "https://spec.industrialontologies.org/ontology/core/Core/",
    }
    ns_set.update(well_known)
    for row in prefix_rows:
        p = (row.get("prefix") or "").strip()
        n = (row.get("namespace") or "").strip()
        if n and p:
            ns_set[p] = n

    sample_triples = []
    for row in sample_rows:
        sample_triples.append(f'{row.get("s","")}  {row.get("p","")}  {row.get("o","")}')

    return {
        "prefixes": ns_set,
        "classes": classes,
        "object_properties": object_properties,
        "datatype_properties": datatype_properties,
        "annotation_properties": annotation_properties,
        "sample_triples": sample_triples,
    }


def _compact_iri(iri: str, prefix_map: dict[str, str]) -> str:
    """Shorten a full IRI to prefixed form (e.g. ml:Pipeline) if possible."""
    for prefix, ns in prefix_map.items():
        if iri.startswith(ns):
            return f"{prefix}:{iri[len(ns):]}"
    # Fallback: just the local name after the last / or #
    for sep in ("#", "/"):
        if sep in iri:
            return iri.rsplit(sep, 1)[-1]
    return iri


def _ontology_context_to_text(ctx: dict, max_chars: int = 8000) -> str:
    """Render the ontology context as a compact text block for the LLM prompt.

    Uses prefixed names instead of full IRIs to keep the text short, and
    progressively drops less-important sections to stay within *max_chars*.
    """
    pfx = ctx["prefixes"]
    lines = []

    # Prefix declarations (the LLM needs these to write valid SPARQL)
    lines.append("=== PREFIXES ===")
    for p, ns in pfx.items():
        lines.append(f"PREFIX {p}: <{ns}>")

    # Classes – just list prefixed names with optional label
    lines.append("\n=== CLASSES ===")
    for c in ctx["classes"]:
        name = _compact_iri(c["iri"], pfx)
        lbl = f'  # {c["label"]}' if c.get("label") else ""
        lines.append(f"  {name}{lbl}")

    # Object properties
    lines.append("\n=== OBJECT PROPERTIES ===")
    for p in ctx["object_properties"]:
        name = _compact_iri(p["iri"], pfx)
        parts = [name]
        if p.get("domain"):
            parts.append(f"domain={_compact_iri(p['domain'], pfx)}")
        if p.get("range"):
            parts.append(f"range={_compact_iri(p['range'], pfx)}")
        lines.append(f"  {' '.join(parts)}")

    # Datatype properties
    lines.append("\n=== DATATYPE PROPERTIES ===")
    for p in ctx["datatype_properties"]:
        name = _compact_iri(p["iri"], pfx)
        parts = [name]
        if p.get("domain"):
            parts.append(f"domain={_compact_iri(p['domain'], pfx)}")
        if p.get("range"):
            parts.append(f"range={_compact_iri(p['range'], pfx)}")
        lines.append(f"  {' '.join(parts)}")

    text = "\n".join(lines)

    # Progressively drop sections if the text is too long
    if len(text) > max_chars:
        # Drop datatype properties section
        idx = text.find("\n=== DATATYPE PROPERTIES")
        if idx != -1:
            text = text[:idx]

    if len(text) > max_chars:
        # Hard truncate with a notice
        text = text[:max_chars] + "\n... (truncated to fit context window)"

    return text


# ──────────────────────────────────────────────────────────────────────
# 2. LLM interaction helpers
# ──────────────────────────────────────────────────────────────────────

# Curated example queries that demonstrate correct MLLO ontology patterns.
# These are included in the LLM prompt so it learns the property-path idioms.
EXAMPLE_QUERIES = """
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
    "- DATASET: an entity used as input to an ML process via ml:hasDataInput (e.g. TrainingData, TestData, ValidationData, ProductionData, RawData)\n"
    "- MODEL: a MachineLearningModel linked from an ML process via ml:executes | bfo:BFO_0000057\n"
    "- PIPELINE: a DataProcessingPipeline or MachineLearningModelDevelopmentPipeline with components via bfo:BFO_0000117\n"
    "- ML PROCESS: the central node linking models, datasets, inputs, and outputs\n\n"
    "KEY PATTERNS:\n"
    "- ML processes link to models via: ml:executes | bfo:BFO_0000057\n"
    "- ML processes link to datasets via: ml:hasDataInput / ml:hasDataOutput\n"
    "- Dataset role (type) via: ?dataset rdf:type ?dataset_type . ?dataset_type rdfs:label ?dataset_used_as\n"
    "- Timestamps via: bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue\n"
    "- Model types via: ?model rdf:type/rdfs:label ?model_type (with rdfs:subClassOf+ ml:MachineLearningModel)\n"
    "- Pipeline components via: bfo:BFO_0000117\n"
    "- Performance metrics via: ml:ModelPerformanceAssessment with bfo:BFO_0000059 linking to metric IRIs\n"
    "- To get human-readable names use: STRAFTER(STR(?x),\"#\") or rdf:type/rdfs:label\n"
    "- Use property paths (/, ^, +, *) as shown in the examples\n\n"
    "IMPORTANT RULES:\n"
    "- NEVER use bare 'rdf:type/rdfs:label' alone to find entities. Always anchor queries through ML process relationships as shown in examples.\n"
    "- Do not invent classes, properties, or IRIs.\n"
    "- Use only the prefixes and vocabulary listed.\n"
    "- Always include LIMIT (default 100) unless the user asks for all results.\n"
    "- Prefer OPTIONAL blocks for fields that may not exist.\n"
    "- If the question cannot be answered with the ontology, return exactly: CANNOT_ANSWER_WITH_ONTOLOGY\n"
    "- Return ONLY the SPARQL query — no explanation, no markdown fences."
)

REPAIR_MESSAGE = (
    "The previous SPARQL used terms not defined in the ontology. "
    "Fix the query strictly using the provided ontology vocabulary. "
    "Return ONLY the corrected SPARQL query — no explanation."
)


async def _call_llm(messages: list[dict]) -> str:
    """Call LM Studio chat completions endpoint."""
    # Log approximate prompt size for debugging context-window issues
    total_chars = sum(len(m.get("content", "")) for m in messages)
    logger.info("LLM prompt: %d messages, ~%d chars total", len(messages), total_chars)

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


def _extract_sparql(raw: str) -> str:
    """Strip markdown fences or extra text around the SPARQL query."""
    # Remove ```sparql ... ``` wrappers
    match = re.search(r"```(?:sparql)?\s*(.+?)```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # If it starts with SELECT/ASK/CONSTRUCT/DESCRIBE or PREFIX, take as-is
    for kw in ("SELECT", "ASK", "CONSTRUCT", "DESCRIBE", "PREFIX"):
        idx = raw.upper().find(kw)
        if idx != -1:
            return raw[idx:].strip()
    return raw.strip()


def _inject_prefixes(sparql: str, ctx: dict) -> str:
    """Prepend missing PREFIX declarations so the triplestore can resolve QNames."""
    prefix_map: dict[str, str] = dict(ctx["prefixes"])

    # Collect prefixes already declared in the query
    declared = {m.group(1) for m in re.finditer(r"PREFIX\s+(\w[\w-]*):\s*<[^>]+>", sparql, re.IGNORECASE)}

    # Find prefixes used in the query body (prefix:localname)
    body_lines = [l for l in sparql.split("\n") if not l.strip().upper().startswith("PREFIX")]
    body = "\n".join(body_lines)
    used = set(re.findall(r"(\b\w[\w-]*):", body))
    used -= {"http", "https", "urn", "mailto", "tel", "ftp"}

    missing_lines = []
    for p in sorted(used):
        if p not in declared and p in prefix_map:
            missing_lines.append(f"PREFIX {p}: <{prefix_map[p]}>")

    if missing_lines:
        sparql = "\n".join(missing_lines) + "\n" + sparql
    return sparql


# ──────────────────────────────────────────────────────────────────────
# 3. SPARQL validation against ontology
# ──────────────────────────────────────────────────────────────────────
def _validate_sparql(sparql: str, ctx: dict) -> list[str]:
    """
    Validate that the generated SPARQL only uses ontology-defined terms.
    Returns a list of error messages (empty = valid).
    """
    errors = []

    # Build sets of known IRIs
    known_class_iris = {c["iri"] for c in ctx["classes"]}
    known_prop_iris = set()
    for plist in (ctx["object_properties"], ctx["datatype_properties"], ctx["annotation_properties"]):
        for p in plist:
            known_prop_iris.add(p["iri"])

    # Build prefix→namespace map
    prefix_map = dict(ctx["prefixes"])

    # Extract PREFIX declarations from the SPARQL itself
    declared_prefixes = {}
    for m in re.finditer(r"PREFIX\s+(\w[\w-]*):\s*<([^>]+)>", sparql, re.IGNORECASE):
        declared_prefixes[m.group(1)] = m.group(2)

    # Check that every PREFIX used in the query body is declared
    # Find all prefix usages like  prefix:localname
    body = sparql
    # Remove PREFIX lines for body analysis
    body_lines = [l for l in sparql.split("\n") if not l.strip().upper().startswith("PREFIX")]
    body = "\n".join(body_lines)

    used_prefixes = set(re.findall(r"(\b\w[\w-]*):", body))
    # Filter out things that aren't real prefixes (e.g., http, https, urn)
    used_prefixes -= {"http", "https", "urn", "mailto", "tel", "ftp"}

    for up in used_prefixes:
        if up not in declared_prefixes and up not in prefix_map:
            errors.append(f"Undefined prefix used: {up}:")

    # Expand prefixed names and check against ontology
    prefixed_names = re.findall(r"(\b\w[\w-]*):(\w+)", body)
    all_known = known_class_iris | known_prop_iris
    # Also build a set of local names for quick lookup
    known_local_names = set()
    for iri in all_known:
        # Extract local name after # or last /
        local = iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1]
        known_local_names.add(local)

    # Well-known vocabulary prefixes that don't need ontology validation
    skip_prefixes = {"rdf", "rdfs", "owl", "xsd", "skos", "dcterms", "dc", "foaf", "sh"}

    for prefix, local in prefixed_names:
        if prefix in skip_prefixes:
            continue
        # Expand to full IRI
        ns = declared_prefixes.get(prefix) or prefix_map.get(prefix)
        if ns:
            full_iri = ns + local
            if full_iri not in all_known and local not in known_local_names:
                # Not a hard error for BFO / IOF codes like BFO_0000057
                if not re.match(r"[A-Z]+_\d+", local):
                    errors.append(f"Term not in ontology: {prefix}:{local} ({full_iri})")

    return errors


