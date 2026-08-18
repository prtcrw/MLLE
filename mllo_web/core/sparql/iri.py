from __future__ import annotations

from mllo_web.core.sparql.common import QueryBuilder, config, inject_explicit_graph


QUERY = """
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT (GROUP_CONCAT(DISTINCT ?datap_pair; separator="\\n") AS ?dataproperty_value_pairs)
                (GROUP_CONCAT(DISTINCT ?annotp_pair; separator="\\n") AS ?annotationproperty_value_pairs)
                (GROUP_CONCAT(DISTINCT ?type; separator="\\n") AS ?types)
WHERE {
    VALUES ?entity {<#iri>}
    ?entity rdf:type/rdfs:label ?type.
    OPTIONAL {
        ?entity ?data_property ?data_property_value.
        ?data_property rdf:type owl:DatatypeProperty.
        ?data_property rdfs:label ?data_property_name.
        BIND(CONCAT(?data_property_name, ": ", STR(?data_property_value)) AS ?datap_pair)
    }
    OPTIONAL {
        ?entity ?annotation_property ?annotation_property_value.
        ?annotation_property rdf:type owl:AnnotationProperty.
        ?annotation_property rdfs:label ?annotation_property_name.
        BIND(CONCAT(?annotation_property_name, ": ", STR(?annotation_property_value)) AS ?annotp_pair)
    }
}
"""


class IriQueryBuilder(QueryBuilder):
    def __init__(self, iri: str):
        self.iri = iri

    def build_query(self) -> str:
        query = QUERY.replace("#iri", self.iri)
        if config.sparql_backend == "graphdb":
            query = inject_explicit_graph(query)
        return query

