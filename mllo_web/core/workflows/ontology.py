from __future__ import annotations

import logging
import re

from fastapi import HTTPException

logger = logging.getLogger(__name__)

ONTOLOGY_UNAVAILABLE_USER_MESSAGE = "Can't access ontology data source."
_ONTOLOGY_CONTEXT_CACHE: dict[str, dict] = {}


def build_ontology_context(
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
        individuals.append({"iri": ind, "label": row.get("label") or "", "type": row.get("type") or ""})

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

    sample_triples = [f'{row.get("s", "")}  {row.get("p", "")}  {row.get("o", "")}' for row in sample_rows]
    return {
        "prefixes": ns_set,
        "classes": classes,
        "object_properties": object_properties,
        "datatype_properties": datatype_properties,
        "annotation_properties": annotation_properties,
        "individuals": individuals,
        "sample_triples": sample_triples,
    }


def compact_iri(iri: str, prefix_map: dict[str, str]) -> str:
    for prefix, namespace in prefix_map.items():
        if iri.startswith(namespace):
            return f"{prefix}:{iri[len(namespace):]}"
    return f"<{iri}>"


def tokenize_query(text: str) -> set[str]:
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "get",
        "how", "in", "is", "it", "list", "me", "of", "on", "or", "show", "that",
        "the", "their", "to", "use", "used", "using", "what", "which", "with",
        "all", "find", "give", "return",
    }
    raw = re.findall(r"[A-Za-z0-9_]+", text.lower())
    return {token for token in raw if len(token) > 2 and token not in stopwords}


def extract_terms(label: str, iri: str) -> set[str]:
    terms: set[str] = set()
    if label:
        terms.update(re.findall(r"[A-Za-z0-9_]+", label.lower()))
    local = iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1]
    local = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", local).lower()
    terms.update(re.findall(r"[A-Za-z0-9_]+", local))
    return {term for term in terms if len(term) > 2}


def build_relevant_subgraph(
    ctx: dict,
    user_question: str,
    max_classes: int = 80,
    max_object_properties: int = 120,
    max_datatype_properties: int = 80,
) -> dict:
    query_tokens = tokenize_query(user_question)
    if not query_tokens:
        return ctx
    classes = ctx["classes"]
    object_properties = ctx["object_properties"]
    datatype_properties = ctx["datatype_properties"]
    individuals = ctx.get("individuals", [])
    class_by_iri = {item["iri"]: item for item in classes}

    scored_classes = []
    for item in classes:
        score = len(query_tokens & extract_terms(item.get("label", ""), item["iri"]))
        if score > 0:
            scored_classes.append((score, item))
    scored_classes.sort(key=lambda value: value[0], reverse=True)
    selected_class_iris = {item["iri"] for _, item in scored_classes[:max_classes]}

    scored_object_properties = []
    for item in object_properties:
        score = len(query_tokens & extract_terms(item.get("label", ""), item["iri"]))
        if item.get("domain") in selected_class_iris or item.get("range") in selected_class_iris:
            score += 1
        if score > 0:
            scored_object_properties.append((score, item))
    scored_object_properties.sort(key=lambda value: value[0], reverse=True)
    selected_object_properties = [item for _, item in scored_object_properties[:max_object_properties]]

    scored_datatype_properties = []
    for item in datatype_properties:
        score = len(query_tokens & extract_terms(item.get("label", ""), item["iri"]))
        if item.get("domain") in selected_class_iris:
            score += 1
        if score > 0:
            scored_datatype_properties.append((score, item))
    scored_datatype_properties.sort(key=lambda value: value[0], reverse=True)
    selected_datatype_properties = [item for _, item in scored_datatype_properties[:max_datatype_properties]]

    scored_individuals = []
    for item in individuals:
        score = len(query_tokens & extract_terms(item.get("label", ""), item["iri"]))
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


def ontology_context_to_text(ctx: dict, max_chars: int = 8000) -> str:
    prefixes = ctx["prefixes"]
    lines = ["=== PREFIXES ==="]
    for prefix, namespace in prefixes.items():
        lines.append(f"PREFIX {prefix}: <{namespace}>")
    lines.append("\n=== CLASSES ===")
    for item in ctx["classes"]:
        label_suffix = f'  # {item["label"]}' if item.get("label") else ""
        lines.append(f'  {compact_iri(item["iri"], prefixes)}{label_suffix}')
    lines.append("\n=== OBJECT PROPERTIES ===")
    for item in ctx["object_properties"]:
        parts = [compact_iri(item["iri"], prefixes)]
        if item.get("domain"):
            parts.append(f'domain={compact_iri(item["domain"], prefixes)}')
        if item.get("range"):
            parts.append(f'range={compact_iri(item["range"], prefixes)}')
        lines.append(f'  {" ".join(parts)}')
    lines.append("\n=== DATATYPE PROPERTIES ===")
    for item in ctx["datatype_properties"]:
        parts = [compact_iri(item["iri"], prefixes)]
        if item.get("domain"):
            parts.append(f'domain={compact_iri(item["domain"], prefixes)}')
        if item.get("range"):
            parts.append(f'range={compact_iri(item["range"], prefixes)}')
        lines.append(f'  {" ".join(parts)}')
    lines.append("\n=== NAMED INDIVIDUALS ===")
    for item in ctx.get("individuals", []):
        parts = [compact_iri(item["iri"], prefixes)]
        if item.get("type"):
            parts.append(f'type={compact_iri(item["type"], prefixes)}')
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


async def load_ontology_context(client, repo: str) -> dict:
    if repo in _ONTOLOGY_CONTEXT_CACHE:
        return _ONTOLOGY_CONTEXT_CACHE[repo]
    try:
        schema_rows = await client.get_ontology_schema(repo)
        prefix_rows = await client.get_prefixes(repo)
        sample_rows = await client.get_sample_triples(repo)
        individual_rows = await client.get_named_individuals(repo)
    except Exception as exc:
        logger.error("Failed to fetch ontology schema: %s", exc)
        raise HTTPException(status_code=500, detail=ONTOLOGY_UNAVAILABLE_USER_MESSAGE) from exc
    ctx = build_ontology_context(schema_rows, prefix_rows, sample_rows, individual_rows)
    _ONTOLOGY_CONTEXT_CACHE[repo] = ctx
    return ctx
