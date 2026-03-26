from __future__ import annotations

from typing import Any

HIDDEN_IRIS = {
    "http://www.w3.org/2002/07/owl#Thing",
    "http://www.w3.org/2000/01/rdf-schema#Resource",
    "http://www.w3.org/2002/07/owl#NamedIndividual",
}

HIDDEN_NAMESPACES = (
    "http://purl.obolibrary.org/obo/BFO_",
    "https://spec.industrialontologies.org/ontology/core/Core/",
)

ALWAYS_KEEP_NAMESPACES = (
    "http://www.semanticweb.org/mnd14/ml/",
    "http://purl.org/dc/terms/",
    "http://www.w3.org/ns/prov#",
)


def _is_hidden_iri(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not (value.startswith("http://") or value.startswith("https://")):
        return False
    if any(value.startswith(namespace) for namespace in ALWAYS_KEEP_NAMESPACES):
        return False
    if value in HIDDEN_IRIS:
        return True
    return any(value.startswith(namespace) for namespace in HIDDEN_NAMESPACES)


def filter_results(results: list[dict], show_upper_ontology: bool = False) -> list[dict]:
    if show_upper_ontology:
        return results

    filtered_results: list[dict] = []
    for row in results:
        hidden_values_removed = False
        filtered_row = {
            key: value for key, value in row.items() if not _is_hidden_iri(value)
        }
        if len(filtered_row) != len(row):
            hidden_values_removed = True
        if hidden_values_removed:
            has_visible_iri = any(
                isinstance(value, str) and (value.startswith("http://") or value.startswith("https://"))
                for value in filtered_row.values()
            )
            if not has_visible_iri:
                continue
        if filtered_row:
            filtered_results.append(filtered_row)
    return filtered_results
