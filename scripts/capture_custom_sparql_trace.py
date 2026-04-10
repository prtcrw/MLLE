from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mllo_web.app.api.routers.natural_language_query import (
    EXAMPLE_QUERIES,
    REPAIR_MESSAGE,
    SYSTEM_MESSAGE,
    _active_provider_config,
    _build_ontology_context,
    _build_relevant_subgraph,
    _contains_cannot_answer,
    _extract_sparql,
    _inject_prefixes,
    _ontology_context_to_text,
    _validate_sparql,
)
from mllo_web.app.api.services.graphdb_client import GraphDBClient
from mllo_web.app.api.services.llm_gateway import LLMGateway
from mllo_web.app.api.services.settings_model import load_settings


async def main() -> None:
    settings = load_settings()
    question = os.environ.get(
        "QUESTION",
        "Which datasets are consumed by processes that execute a machine learning model?",
    )
    repo = os.environ.get("REPO", settings.graphdb_default_repo)

    provider_config = _active_provider_config(settings)
    client = GraphDBClient(
        base_url=settings.graphdb_url,
        default_repo=settings.graphdb_default_repo,
        repo_allowlist=settings.graphdb_repo_allowlist,
    )
    gateway = LLMGateway()

    trace: dict[str, Any] = {
        "question": question,
        "repo": repo,
        "provider": provider_config,
    }

    schema_rows = await client.get_ontology_schema(repo)
    prefix_rows = await client.get_prefixes(repo)
    sample_rows = await client.get_sample_triples(repo)
    individual_rows = await client.get_named_individuals(repo)

    trace["schema_fetch"] = {
        "schema_row_count": len(schema_rows),
        "prefix_row_count": len(prefix_rows),
        "sample_row_count": len(sample_rows),
        "individual_row_count": len(individual_rows),
        "schema_rows_preview": schema_rows[:5],
        "prefix_rows_preview": prefix_rows[:5],
        "sample_rows_preview": sample_rows[:5],
        "individual_rows_preview": individual_rows[:5],
    }

    ctx = _build_ontology_context(schema_rows, prefix_rows, sample_rows, individual_rows)
    trace["ontology_context_summary"] = {
        "prefix_count": len(ctx["prefixes"]),
        "class_count": len(ctx["classes"]),
        "object_property_count": len(ctx["object_properties"]),
        "datatype_property_count": len(ctx["datatype_properties"]),
        "annotation_property_count": len(ctx["annotation_properties"]),
        "individual_count": len(ctx["individuals"]),
        "sample_triple_count": len(ctx["sample_triples"]),
    }

    prompt_ctx = _build_relevant_subgraph(ctx, question)
    trace["relevant_subgraph_summary"] = {
        "prefix_count": len(prompt_ctx["prefixes"]),
        "class_count": len(prompt_ctx["classes"]),
        "object_property_count": len(prompt_ctx["object_properties"]),
        "datatype_property_count": len(prompt_ctx["datatype_properties"]),
        "annotation_property_count": len(prompt_ctx["annotation_properties"]),
        "individual_count": len(prompt_ctx["individuals"]),
    }

    ontology_text = _ontology_context_to_text(prompt_ctx)
    trace["ontology_text"] = ontology_text

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
    trace["initial_messages"] = messages

    raw_sparql = await gateway.chat_completion(messages, provider_config)
    trace["raw_llm_output"] = raw_sparql
    trace["raw_contains_cannot_answer"] = _contains_cannot_answer(raw_sparql)

    sparql = _extract_sparql(raw_sparql)
    trace["extracted_sparql"] = sparql

    errors = _validate_sparql(sparql, ctx)
    trace["validation_errors"] = errors

    repair_trace: dict[str, Any] | None = None
    if errors:
        repair_messages = messages + [
            {"role": "assistant", "content": sparql},
            {"role": "user", "content": f"{REPAIR_MESSAGE}\n\nValidation errors:\n- " + "\n- ".join(errors)},
        ]
        repaired_raw = await gateway.chat_completion(repair_messages, provider_config)
        repaired_sparql = _extract_sparql(repaired_raw)
        repaired_errors = _validate_sparql(repaired_sparql, ctx)
        repair_trace = {
            "repair_messages": repair_messages,
            "repaired_raw_output": repaired_raw,
            "repaired_sparql": repaired_sparql,
            "repaired_validation_errors": repaired_errors,
        }
        sparql = repaired_sparql
        errors = repaired_errors

    trace["repair_trace"] = repair_trace
    trace["final_validation_errors"] = errors
    trace["final_sparql_with_injected_prefixes"] = _inject_prefixes(sparql, ctx)

    path = Path(os.environ.get("OUTPUT_PATH", str(ROOT / "tmp" / "custom_sparql_trace.json")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    asyncio.run(main())
