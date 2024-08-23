from fastapi import Request, Response
from mllo_web.app.api.services.sparql_client import QueryBuilder

QUERY = """
    PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX bfo: <http://purl.obolibrary.org/obo/>
    PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT DISTINCT (GROUP_CONCAT(?datap_pair;separator="\\n") as ?dataproperty_value_pairs) 
                    (GROUP_CONCAT(?annotp_pair;separator="\\n") as ?annotationproperty_value_pairs) 
                    (GROUP_CONCAT(?type;separator="\\n") as ?types)
    WHERE {{
        VALUES ?entity {<#iri>}
        ?entity rdf:type/rdfs:label ?type.
        OPTIONAL {{
            ?entity ?data_property ?data_property_value.
            ?data_property rdf:type owl:DatatypeProperty.
            ?data_property rdfs:label ?data_property_name.
            BIND(CONCAT(?data_property_name, ": ", STR(?data_property_value)) as ?datap_pair)
        }}
        OPTIONAL {{
            ?entity ?annotation_property ?annotation_property_value.
            ?annotation_property rdf:type owl:AnnotationProperty.
            ?annotation_property rdfs:label ?annotation_property_name.
            BIND(CONCAT(?annotation_property_name, ": ", STR(?annotation_property_value)) as ?annotp_pair)
        }}
    }}
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
    try:
        result = app.sparql_client.query(query)

        # Generalized formatting of the result
        formatted_result = ""
        if result:
            for item in result:
                for key, value in item.items():
                    if value:
                        formatted_key = key.replace('_', ' ').title()
                        formatted_result += f"{formatted_key}:{value}\n"
        else:
            formatted_result += "No data available."

        return Response(content=formatted_result.strip(), media_type="text/plain")
    except Exception as e:
        return Response(content=f"An error occurred: {str(e)}", status_code=500)