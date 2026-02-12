import logging
import re
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/nlq", tags=["natural-language-query"])


# ──────────────────────────────────────────────────────────────────────
# Configuration – adjust these or pull from app.state / env vars
# ──────────────────────────────────────────────────────────────────────
LLM_BASE_URL = "http://localhost:1234/v1"          # LM Studio OpenAI-compat endpoint
LLM_MODEL    = "local-model"                        # model name loaded in LM Studio
MAX_REPAIR_ATTEMPTS = 2                             # how many times to retry invalid SPARQL

# Named graph that holds the ontology in GraphDB / Mobi
ONTOLOGY_GRAPH = "http://www.semanticweb.org/mnd14/ml/"


# ──────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────────────────────────────
class NLQueryRequest(BaseModel):
    question: str


class NLQueryResponse(BaseModel):
    sparql: str
    results: list
    answer: str


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

    classes = []
    object_properties = []
    datatype_properties = []
    annotation_properties = []

    for row in schema_rows:
        entry = {
            "iri": row.get("entity", ""),
            "label": row.get("label", ""),
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
        p = row.get("prefix", "").strip()
        n = row.get("namespace", "").strip()
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


def _ontology_context_to_text(ctx: dict) -> str:
    """Render the ontology context as a compact text block for the LLM prompt."""
    lines = []

    lines.append("=== PREFIXES ===")
    for p, ns in ctx["prefixes"].items():
        lines.append(f"PREFIX {p}: <{ns}>")

    lines.append("\n=== CLASSES ===")
    for c in ctx["classes"]:
        lbl = f' (label: "{c["label"]}")' if c.get("label") else ""
        sup = f" rdfs:subClassOf {c['superclass']}" if c.get("superclass") else ""
        lines.append(f"  {c['iri']}{lbl}{sup}")

    lines.append("\n=== OBJECT PROPERTIES ===")
    for p in ctx["object_properties"]:
        lbl = f' (label: "{p["label"]}")' if p.get("label") else ""
        dom = f" domain={p['domain']}" if p.get("domain") else ""
        rng = f" range={p['range']}" if p.get("range") else ""
        lines.append(f"  {p['iri']}{lbl}{dom}{rng}")

    lines.append("\n=== DATATYPE PROPERTIES ===")
    for p in ctx["datatype_properties"]:
        lbl = f' (label: "{p["label"]}")' if p.get("label") else ""
        dom = f" domain={p['domain']}" if p.get("domain") else ""
        rng = f" range={p['range']}" if p.get("range") else ""
        lines.append(f"  {p['iri']}{lbl}{dom}{rng}")

    lines.append("\n=== ANNOTATION PROPERTIES ===")
    for p in ctx["annotation_properties"]:
        lbl = f' (label: "{p["label"]}")' if p.get("label") else ""
        lines.append(f"  {p['iri']}{lbl}")

    if ctx["sample_triples"]:
        lines.append("\n=== SAMPLE TRIPLES (for context) ===")
        for t in ctx["sample_triples"]:
            lines.append(f"  {t}")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# 2. LLM interaction helpers
# ──────────────────────────────────────────────────────────────────────
SYSTEM_MESSAGE = (
    "You are an expert Semantic Web engineer.\n"
    "Generate ONLY valid SPARQL that strictly follows the provided ontology.\n"
    "Do not invent classes, properties, or IRIs.\n"
    "Use only the prefixes and vocabulary listed.\n"
    "If the question cannot be answered with the ontology, return exactly: CANNOT_ANSWER_WITH_ONTOLOGY\n"
    "Return ONLY the SPARQL query — no explanation, no markdown fences."
)

REPAIR_MESSAGE = (
    "The previous SPARQL used terms not defined in the ontology. "
    "Fix the query strictly using the provided ontology vocabulary. "
    "Return ONLY the corrected SPARQL query — no explanation."
)


async def _call_llm(messages: list[dict]) -> str:
    """Call LM Studio chat completions endpoint."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 2048,
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


# ──────────────────────────────────────────────────────────────────────
# 4. Natural language answer generation
# ──────────────────────────────────────────────────────────────────────
async def _generate_nl_answer(question: str, sparql: str, results: list) -> str:
    """Ask the LLM to summarise the SPARQL results in natural language."""
    if not results:
        return "The query returned no results."

    # Truncate results for prompt size
    results_text = str(results[:50])

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. Given a user question, the SPARQL query that was run, "
                "and the query results, provide a clear natural language answer. Be concise."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                f"SPARQL Query:\n{sparql}\n\n"
                f"Results:\n{results_text}\n\n"
                "Please summarise the results in plain English."
            ),
        },
    ]
    try:
        return await _call_llm(messages)
    except Exception as e:
        logger.warning("Failed to generate NL answer: %s", e)
        return f"Query returned {len(results)} result(s). (NL summary unavailable)"


# ──────────────────────────────────────────────────────────────────────
# 5. Main endpoint
# ──────────────────────────────────────────────────────────────────────
@router.post("/query")
async def natural_language_query(request: Request, body: NLQueryRequest) -> JSONResponse:
    """
    Accept a natural language question, generate ontology-compliant SPARQL,
    execute it on GraphDB, and return SPARQL + results + NL answer.
    """
    app = request.app
    question = body.question.strip()

    if not question:
        return JSONResponse({"error": "Question cannot be empty."}, status_code=400)

    # ── Step 2: Fetch ontology schema ────────────────────────────────
    try:
        schema_rows = app.sparql_client.query(ONTOLOGY_SCHEMA_QUERY)
        prefix_rows = app.sparql_client.query(PREFIX_QUERY)
        sample_rows = app.sparql_client.query(SAMPLE_TRIPLES_QUERY)
    except Exception as e:
        logger.error("Failed to fetch ontology schema: %s", e)
        return JSONResponse(
            {"error": f"Failed to fetch ontology schema: {str(e)}"},
            status_code=500,
        )

    ctx = _build_ontology_context(schema_rows, prefix_rows, sample_rows)
    ontology_text = _ontology_context_to_text(ctx)

    if not ctx["classes"] and not ctx["object_properties"]:
        return JSONResponse(
            {"error": "Ontology schema is empty. Ensure the ontology is loaded in GraphDB."},
            status_code=500,
        )

    # ── Step 3-4: Generate SPARQL via LLM ────────────────────────────
    user_prompt = (
        f"User question: {question}\n\n"
        f"Ontology schema:\n{ontology_text}\n\n"
        "Generate a SPARQL SELECT query to answer the question. "
        "Use ONLY the classes, properties, and prefixes listed above."
    )

    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw_sparql = await _call_llm(messages)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return JSONResponse(
            {"error": f"LLM call failed: {str(e)}"},
            status_code=502,
        )

    # Check if LLM says it cannot answer
    if "CANNOT_ANSWER_WITH_ONTOLOGY" in raw_sparql:
        return JSONResponse({
            "sparql": "",
            "results": [],
            "answer": (
                "The question cannot be answered using the available ontology. "
                "Please rephrase or ask about concepts defined in the knowledge graph."
            ),
        })

    sparql = _extract_sparql(raw_sparql)

    # ── Step 5: Validate + repair loop ───────────────────────────────
    validation_log = []
    for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
        errors = _validate_sparql(sparql, ctx)
        if not errors:
            break

        validation_log.append({"attempt": attempt + 1, "errors": errors, "sparql": sparql})
        logger.warning("SPARQL validation failed (attempt %d): %s", attempt + 1, errors)

        if attempt < MAX_REPAIR_ATTEMPTS:
            # Ask LLM to repair
            messages.append({"role": "assistant", "content": sparql})
            messages.append({
                "role": "user",
                "content": (
                    f"{REPAIR_MESSAGE}\n\n"
                    f"Validation errors:\n" + "\n".join(f"- {e}" for e in errors) + "\n\n"
                    f"Ontology schema:\n{ontology_text}"
                ),
            })
            try:
                raw_sparql = await _call_llm(messages)
                sparql = _extract_sparql(raw_sparql)
            except Exception as e:
                logger.error("LLM repair call failed: %s", e)
                break
    else:
        # All repair attempts exhausted
        return JSONResponse({
            "sparql": sparql,
            "results": [],
            "answer": (
                "Generated SPARQL could not be validated against the ontology after "
                f"{MAX_REPAIR_ATTEMPTS} repair attempts. "
                f"Last errors: {'; '.join(errors)}"
            ),
            "validation_log": validation_log,
        })

    # ── Step 6: Execute SPARQL on GraphDB ────────────────────────────
    try:
        results = app.sparql_client.query(sparql)
    except Exception as e:
        logger.error("SPARQL execution failed: %s", e)
        return JSONResponse({
            "sparql": sparql,
            "results": [],
            "answer": f"SPARQL execution failed: {str(e)}",
        })

    # ── Step 7: Generate NL answer ───────────────────────────────────
    nl_answer = await _generate_nl_answer(question, sparql, results)

    # ── Step 8: Return everything ────────────────────────────────────
    return JSONResponse({
        "sparql": sparql,
        "results": results,
        "answer": nl_answer,
    })


# ──────────────────────────────────────────────────────────────────────
# 6. Utility endpoint: get ontology summary (for debugging / frontend)
# ──────────────────────────────────────────────────────────────────────
@router.get("/ontology-summary")
async def get_ontology_summary(request: Request) -> JSONResponse:
    """Return a summary of the loaded ontology schema for debugging."""
    app = request.app
    try:
        schema_rows = app.sparql_client.query(ONTOLOGY_SCHEMA_QUERY)
        prefix_rows = app.sparql_client.query(PREFIX_QUERY)
        sample_rows = app.sparql_client.query(SAMPLE_TRIPLES_QUERY)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    ctx = _build_ontology_context(schema_rows, prefix_rows, sample_rows)
    return JSONResponse({
        "num_classes": len(ctx["classes"]),
        "num_object_properties": len(ctx["object_properties"]),
        "num_datatype_properties": len(ctx["datatype_properties"]),
        "num_annotation_properties": len(ctx["annotation_properties"]),
        "prefixes": ctx["prefixes"],
        "classes": [c["iri"] for c in ctx["classes"][:50]],
        "sample_triples": ctx["sample_triples"][:10],
    })
