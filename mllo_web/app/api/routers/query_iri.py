from fastapi import Request, Response
from starlette.responses import JSONResponse

from mllo_web.app.api.services.sparql_client import QueryBuilder

QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT (GROUP_CONCAT(?datap_pair; separator="\\n") AS ?dataproperty_value_pairs) 
                (GROUP_CONCAT(?annotp_pair; separator="\\n") AS ?annotationproperty_value_pairs) 
                (GROUP_CONCAT(?type; separator="\\n") AS ?types)
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
        query = QUERY
        query = query.replace("#iri", self.iri)
        return query


async def execute_iri_query(request: Request, iri: str) -> Response:
    if not iri:
        return Response(content="No IRI provided", status_code=400)

    query_builder = IriQueryBuilder(iri)
    query = query_builder.build_query()

    app = request.app
    result = app.sparql_client.query(query)
    return JSONResponse(result)
