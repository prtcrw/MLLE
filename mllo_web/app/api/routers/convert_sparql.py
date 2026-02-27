"""Thin /convert-sparql endpoint.

Accepts { "input": "<natural language>" } and returns { "sparql": "..." }.
Delegates to the NLQ pipeline in natural_language_query.py (ontology fetch from
the live triplestore -> LLM generation -> validation/repair) but skips query
execution and NL-answer generation so the response stays fast.
"""

import logging
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from mllo_web.app.api.routers.natural_language_query import (
    ONTOLOGY_SCHEMA_QUERY,
    PREFIX_QUERY,
    SAMPLE_TRIPLES_QUERY,
    EXAMPLE_QUERIES,
    SYSTEM_MESSAGE,
    REPAIR_MESSAGE,
    MAX_REPAIR_ATTEMPTS,
    _build_ontology_context,
    _ontology_context_to_text,
    _call_llm,
    _extract_sparql,
    _inject_prefixes,
    _validate_sparql,
)

logger = logging.getLogger(__name__)

router = APIRouter()

EXPLICIT_GRAPH = ""#FROM <http://www.ontotext.com/explicit>"


def _add_explicit_graph(sparql: str) -> str:
    """Insert FROM <http://www.ontotext.com/explicit> before WHERE { to
    prevent GraphDB from returning inferred triples."""
    if EXPLICIT_GRAPH in sparql:
        return sparql  # already present
    # Insert before the first top-level WHERE {
    return re.sub(
        r"(?i)\bWHERE\s*\{",
        f"{EXPLICIT_GRAPH}\nWHERE {{",
        sparql,
        count=1,
    )


class ConvertRequest(BaseModel):
    input: str


@router.post("/convert-sparql")
async def convert_sparql(request: Request, body: ConvertRequest):
    """Convert a natural-language description to SPARQL (no execution)."""
    text = body.input.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty input")

    app = request.app

    # -- Fetch ontology schema from the live triplestore ---------------
    try:
        schema_rows = app.sparql_client.query(ONTOLOGY_SCHEMA_QUERY)
        prefix_rows = app.sparql_client.query(PREFIX_QUERY)
        sample_rows = app.sparql_client.query(SAMPLE_TRIPLES_QUERY)
    except Exception as e:
        logger.error("Failed to fetch ontology schema: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch ontology schema: {e}",
        )

    ctx = _build_ontology_context(schema_rows, prefix_rows, sample_rows)
    ontology_text = _ontology_context_to_text(ctx)

    if not ctx["classes"] and not ctx["object_properties"]:
        raise HTTPException(
            status_code=500,
            detail="Ontology schema is empty. Ensure the ontology is loaded in the triplestore.",
        )

    # -- Generate SPARQL via LLM ---------------------------------------
    user_prompt = (
        f"User question: {text}\n\n"
        f"Ontology schema:\n{ontology_text}\n\n"
        f"{EXAMPLE_QUERIES}\n\n"
        "Generate a SPARQL SELECT query to answer the question. "
        "Follow the patterns shown in the examples above. "
        "Use ONLY the classes, properties, and prefixes listed."
    )

    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": user_prompt},
    ]
    print(f"=== LLM PROMPT (system) ===\n{SYSTEM_MESSAGE}")
    print(f"=== LLM PROMPT (user, {len(user_prompt)} chars) ===\n{user_prompt[:15000]}")
    # logger.info("=== LLM PROMPT (system) ===\n%s", SYSTEM_MESSAGE)
    # logger.info("=== LLM PROMPT (user, %d chars) ===\n%s", len(user_prompt), user_prompt[:2000])

    try:
        raw_sparql = await _call_llm(messages)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    if "CANNOT_ANSWER_WITH_ONTOLOGY" in raw_sparql:
        raise HTTPException(
            status_code=422,
            detail="The question cannot be answered using the available ontology.",
        )

    sparql = _extract_sparql(raw_sparql)

    # -- Validate + repair loop ----------------------------------------
    for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
        errors = _validate_sparql(sparql, ctx)
        if not errors:
            break

        logger.warning(
            "SPARQL validation failed (attempt %d): %s", attempt + 1, errors
        )

        if attempt < MAX_REPAIR_ATTEMPTS:
            messages.append({"role": "assistant", "content": sparql})
            error_lines = "\n".join(f"- {e}" for e in errors)
            messages.append({
                "role": "user",
                "content": (
                    f"{REPAIR_MESSAGE}\n\n"
                    f"Validation errors:\n{error_lines}\n\n"
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
        joined = "; ".join(errors)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Generated SPARQL could not be validated after "
                f"{MAX_REPAIR_ATTEMPTS} repair attempts. Last errors: {joined}"
            ),
        )

    # -- Inject missing PREFIX declarations -----------------------------
    sparql = _inject_prefixes(sparql, ctx)

    # -- Add FROM <explicit> to prevent inferred results (GraphDB) ------
    #sparql = _add_explicit_graph(sparql)

    logger.info("=== FINAL SPARQL (sent to triplestore) ===\n%s", sparql)

    # -- Execute the generated SPARQL (with repair on failure) ----------
    MAX_EXEC_REPAIRS = 3
    results = []
    exec_error = None

    for exec_attempt in range(MAX_EXEC_REPAIRS + 1):
        try:
            results = app.sparql_client.query(sparql)
            exec_error = None
            break
        except Exception as e:
            exec_error = str(e)
            logger.warning(
                "SPARQL execution failed (attempt %d/%d): %s",
                exec_attempt + 1, MAX_EXEC_REPAIRS + 1, e,
            )

            if exec_attempt < MAX_EXEC_REPAIRS:
                # Feed the triplestore error back to the LLM for repair
                messages.append({"role": "assistant", "content": sparql})
                messages.append({
                    "role": "user",
                    "content": (
                        "The triplestore rejected the query with the following error:\n"
                        f"{exec_error}\n\n"
                        "Fix the SPARQL query to resolve this error. "
                        "Return ONLY the corrected SPARQL query — no explanation."
                    ),
                })
                try:
                    raw_sparql = await _call_llm(messages)
                    sparql = _extract_sparql(raw_sparql)
                    sparql = _inject_prefixes(sparql, ctx)
                    #sparql = _add_explicit_graph(sparql)
                except Exception as llm_err:
                    logger.error("LLM exec-repair call failed: %s", llm_err)
                    break

    return {
        "sparql": sparql,
        "results": results,
        "error": exec_error,
    }
