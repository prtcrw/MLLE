import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mllo_web.app.api.config import get_config

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])
config = get_config()
EXPLICIT_GRAPH = "FROM <http://www.ontotext.com/explicit>"


def _inject_explicit_graph(query: str) -> str:
    if EXPLICIT_GRAPH in query:
        return query
    return re.sub(
        r"(?is)(SELECT\b.*?)(\bWHERE\s*\{)",
        rf"\1\n{EXPLICIT_GRAPH}\n\2",
        query,
        count=1,
    )


def _count_query(prefixes: str, where_body: str) -> str:
    query = (
        f"{prefixes.strip()}\n"
        f"SELECT (COUNT(DISTINCT ?item) AS ?count)\n"
        f"WHERE {{\n{where_body.strip()}\n}}"
    )
    if config.sparql_backend == "graphdb":
        query = _inject_explicit_graph(query)
    return query


MODEL_COUNT_QUERY = _count_query("""
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
""", """
?item rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
""")

DATASET_COUNT_QUERY = _count_query("""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
""", """
?item rdf:type/rdfs:subClassOf* <http://purl.obolibrary.org/obo/IAO_0000100> .
""")

PIPELINE_COUNT_QUERY = _count_query("""
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
""", """
?item rdf:type ?pipeline_type_iri .
{
    ?pipeline_type_iri rdfs:subClassOf+ ml:DataProcessingPipeline .
}
UNION
{
    VALUES ?pipeline_type_iri { ml:MachineLearningModelDevelopmentPipeline }
}
""")

DEPLOYED_MODEL_COUNT_QUERY = _count_query("""
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
""", """
?deployment_state bfo:BFO_0000167 ?item .
?item rdf:type/rdfs:subClassOf* ml:MachineLearningModel .
""")


@router.get("/summary")
async def get_dashboard_summary(request: Request) -> JSONResponse:
    client = request.app.sparql_client

    def fetch_count(query: str) -> int:
        result = client.query(query)
        if not result:
            return 0
        return int(result[0].get("count", 0))

    return JSONResponse({
        "models": fetch_count(MODEL_COUNT_QUERY),
        "datasets": fetch_count(DATASET_COUNT_QUERY),
        "pipelines": fetch_count(PIPELINE_COUNT_QUERY),
        "deployed_models": fetch_count(DEPLOYED_MODEL_COUNT_QUERY),
    })
