import math
import re
from typing import Optional, List

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from mllo_web.app.api.config import get_config
from mllo_web.app.api.routers.utilities import (
    generate_csv_response,
    to_order_by_string,
)
from mllo_web.app.api.services.sparql_client import (
    PaginationQueryBuilder,
    QueryBuilder,
    TotalRecordsQueryBuilder,
)
from .query_iri import execute_iri_query

router = APIRouter(prefix="/v1/models", tags=["models"])
config = get_config()
EXPLICIT_GRAPH = "FROM <http://www.ontotext.com/explicit>"


def _inject_explicit_graph(query: str) -> str:
    if EXPLICIT_GRAPH in query:
        return query
    return re.sub(
        r"(?is)(SELECT\s+DISTINCT\b.*?)(\bWHERE\s*\{)",
        rf"\1\n{EXPLICIT_GRAPH}\n\2",
        query,
        count=1,
    )


FIND_MODELS_QUERY = """
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT
    ?model
    ?model_type
    ?model_objective_iri
    ?model_objective
    ?model_objective_description
    ?deployment_status
    ?linked_dataset
    ?linked_dataset_type
    ?linked_pipeline
    ?deployed_on_system
    ?last_model_update
    ?last_model_execution
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value
WHERE {
    ?model rdf:type ?model_type_iri .
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel .
    ?model_type_iri rdfs:label ?model_type .
    OPTIONAL { ?model rdfs:label ?model_label . }

    OPTIONAL {
        ?model bfo:BFO_0000178 ?model_objective_iri .
        ?model_objective_iri rdf:type/rdfs:label ?model_objective .
        OPTIONAL {
            ?model_objective_iri ?objective_description_property ?model_objective_description .
            ?objective_description_property rdf:type owl:AnnotationProperty .
            ?objective_description_property rdfs:label ?objective_description_property_label .
            FILTER(LCASE(STR(?objective_description_property_label)) = "description")
        }
    }

    OPTIONAL {
        ?process (ml:executed | bfo:BFO_0000057) ?model .
        OPTIONAL {
            ?process ml:hasDataInput ?input_dataset .
            ?input_dataset ml:informationContentEntityDerivedFrom* ?linked_dataset .
            ?linked_dataset rdf:type ?linked_dataset_type_iri .
            ?linked_dataset_type_iri rdfs:subClassOf* ml:MachineLearningDataSet .
            ?linked_dataset_type_iri rdfs:label ?linked_dataset_type .
        }
        OPTIONAL {
            ?linked_pipeline bfo:BFO_0000117* ?process .
            ?linked_pipeline rdf:type/rdfs:subClassOf* ml:MachineLearningModelDevelopmentPipeline .
        }
        OPTIONAL {
            ?process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeInstantValue ?process_timestamp .
        }
        OPTIONAL {
            ?process ml:hasDataOutput ?process_output .
            OPTIONAL {
                ?model_output_utilization ml:hasDataInput ?process_output .
            }
            OPTIONAL {
                ?model_performance_assessment ml:hasDataInput ?process_output .
                ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri .
                ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment .
                ?model_performance_metric_iri rdf:type ?model_performance_metric_type .
                ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric .
                ?model_performance_metric_type rdfs:label ?model_performance_metric .
                ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value .
            }
        }
    }

    OPTIONAL {
        ?deployed_state bfo:BFO_0000167 ?model .
        ?deployed_state bfo:BFO_0000167 ?deployed_on_system .
        ?deployed_on_system rdf:type/rdfs:subClassOf* iof-core:EngineeredSystem .
        ?deployed_state bfo:BFO_0000117 ?model_execution .
        ?model_execution rdf:type/rdfs:subClassOf* ml:ModelExecution .
        OPTIONAL {
            ?model_execution bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeInstantValue ?execution_timestamp .
        }
        OPTIONAL {
            ?ml_training ^bfo:BFO_0000117*/bfo:BFO_0000063 ?model_execution .
            ?ml_training rdf:type/rdfs:subClassOf* ml:MachineLearningTraining .
            OPTIONAL {
                ?ml_training bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeInstantValue ?training_timestamp .
            }
        }
    }

    BIND(IF(BOUND(?deployed_on_system), "Deployed", "Undeployed") AS ?deployment_status)
    BIND(COALESCE(?training_timestamp, ?process_timestamp) AS ?last_model_update)
    BIND(?execution_timestamp AS ?last_model_execution)

    #SEARCH_FILTER
    #MODEL_TYPE_FILTER
    #DEPLOYMENT_STATUS_FILTER
}
"""


ANALYZE_DEPLOYED_MODELS_QUERY = """
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/construct/>
SELECT DISTINCT
    ?model_name
    ?model_deployed_on_system
    (MAX(?model_training_timestamp) AS ?last_model_update)
    ?model_execution_timestamp
    ?model_input
    ?model_output
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value
WHERE {
    ?deployed_state bfo:BFO_0000167 ?model_name.
    ?deployed_state bfo:BFO_0000167 ?model_deployed_on_system.

    ?model_deployed_on_system rdf:type/rdfs:subClassOf* iof-core:EngineeredSystem.
    ?model_name rdf:type/rdfs:subClassOf+ ml:MachineLearningModel.

    OPTIONAL {
        ?deployed_state bfo:BFO_0000117 ?model_execution.
        ?model_execution rdf:type/rdfs:subClassOf* ml:ModelExecution.
        ?model_execution (ml:executed | bfo:BFO_0000057) ?model_name.
        OPTIONAL { ?model_execution ml:hasDataInput ?model_input. }
        OPTIONAL {
            ?model_execution ml:hasDataOutput ?model_output.
            OPTIONAL {
                ?model_output_utilization ml:hasDataInput ?model_output.
            }
            OPTIONAL {
                ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri.
                ?model_performance_assessment ml:hasDataInput ?model_output.
                ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment.

                ?model_performance_metric_iri rdf:type ?model_performance_metric_type.
                ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric.
                ?model_performance_metric_type rdfs:label ?model_performance_metric.

                ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value.
            }
        }
        OPTIONAL {
            ?model_execution bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeInstantValue ?model_execution_timestamp.
        }
        OPTIONAL {
            ?ml_training ^bfo:BFO_0000117*/bfo:BFO_0000063 ?model_execution.
            ?ml_training rdf:type/rdfs:subClassOf* ml:MachineLearningTraining.
            OPTIONAL {
                ?ml_training bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeInstantValue ?model_training_timestamp.
            }
        }
    }
}
GROUP BY
    ?model_name
    ?model_deployed_on_system
    ?model_execution_timestamp
    ?model_input
    ?model_output
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value
"""


MODEL_TYPES_QUERY = """
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?model_type
WHERE {
    ?model rdf:type ?model_type_iri.
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
    ?model_type_iri rdfs:label ?model_type.
}
"""


class FindModelsQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Model": "model",
        "Model Type": "model_type",
        "Objective": "model_objective",
        "Objective Description": "model_objective_description",
        "Deployment Status": "deployment_status",
        "Linked Dataset": "linked_dataset",
        "Linked Dataset Type": "linked_dataset_type",
        "Linked Pipeline": "linked_pipeline",
        "Deployed On System": "deployed_on_system",
        "Last Model Update": "last_model_update",
        "Last Model Execution": "last_model_execution",
        "Output Utilization": "model_output_utilization",
        "Performance Metric": "model_performance_metric",
        "Performance Value": "model_performance_value",
    }

    def __init__(
        self,
        search_term: str,
        model_types: Optional[List[str]] = None,
        deployment_status: Optional[List[str]] = None,
        sort: Optional[List[str]] = None,
    ):
        self.search_term = search_term.strip() if search_term and len(search_term) > 0 else None
        self.model_types = model_types
        self.deployment_status = deployment_status or []
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)

    def build_query(self) -> str:
        query = FIND_MODELS_QUERY

        if self.search_term:
            normalized = self.search_term.replace(" ", "")
            query = query.replace(
                "#SEARCH_FILTER",
                "\n".join([
                    "FILTER(",
                    f'    CONTAINS(LCASE(COALESCE(?model_label, "")), LCASE("{self.search_term}")) ||',
                    f'    CONTAINS(LCASE(STRAFTER(STR(?model), "#")), LCASE("{normalized}")) ||',
                    f'    CONTAINS(LCASE(COALESCE(?model_objective, "")), LCASE("{self.search_term}")) ||',
                    f'    CONTAINS(LCASE(COALESCE(?model_objective_description, "")), LCASE("{self.search_term}")) ||',
                    f'    CONTAINS(LCASE(COALESCE(STRAFTER(STR(?linked_dataset), "#"), "")), LCASE("{normalized}")) ||',
                    f'    CONTAINS(LCASE(COALESCE(STRAFTER(STR(?linked_pipeline), "#"), "")), LCASE("{normalized}"))',
                    ")",
                ]),
            )
        else:
            query = query.replace("#SEARCH_FILTER", "")

        if self.model_types:
            model_types_str = ",".join([f'"{mtype}"' for mtype in self.model_types])
            query = query.replace(
                "#MODEL_TYPE_FILTER",
                f"FILTER(?model_type IN ({model_types_str}))",
            )
        else:
            query = query.replace("#MODEL_TYPE_FILTER", "")

        if self.deployment_status:
            statuses = set(self.deployment_status)
            if statuses == {"Deployed"}:
                query = query.replace(
                    "#DEPLOYMENT_STATUS_FILTER",
                    'FILTER(?deployment_status = "Deployed")',
                )
            elif statuses == {"Undeployed"}:
                query = query.replace(
                    "#DEPLOYMENT_STATUS_FILTER",
                    'FILTER(?deployment_status = "Undeployed")',
                )
            else:
                query = query.replace("#DEPLOYMENT_STATUS_FILTER", "")
        else:
            query = query.replace("#DEPLOYMENT_STATUS_FILTER", "")

        if self.sort_string:
            query += self.sort_string

        if config.sparql_backend == "graphdb":
            query = _inject_explicit_graph(query)

        return query


class DeployedModelsQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Model Name": "model_name",
        "Model Deployed on System": "model_deployed_on_system",
        "Last Model Update": "last_model_update",
        "Model Execution Timestamp": "model_execution_timestamp",
        "Model Input": "model_input",
        "Model Output": "model_output",
        "Model Output Utilization": "model_output_utilization",
        "Model Performance Metric": "model_performance_metric",
        "Model Performance Value": "model_performance_value",
    }

    def __init__(self, search_term: str, sort: Optional[List[str]] = None):
        self.search_term = search_term.strip() if search_term and len(search_term) > 0 else None
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)

    def build_query(self) -> str:
        query = ANALYZE_DEPLOYED_MODELS_QUERY

        if self.sort_string:
            query += self.sort_string

        if config.sparql_backend == "graphdb":
            query = _inject_explicit_graph(query)

        return query


@router.get("/")
async def get_models(
    request: Request,
    search_term: str = Query(default=None, description="Search term"),
    model_types: Optional[List[str]] = Query(default=None, description="Model types"),
    deployment_status: Optional[List[str]] = Query(default=None, description="Deployment status"),
    page: int = Query(default=1, description="Page number"),
    items_per_page: int = Query(default=10, description="Number of models to return per page"),
    sort: Optional[List[str]] = Query(
        default=None,
        description="Sort criteria",
    ),
    format: str = Query(default="json", description="Output format (json or csv)"),
) -> Response:
    app = request.app
    query_builder = FindModelsQueryBuilder(
        search_term=search_term,
        model_types=model_types,
        deployment_status=deployment_status,
        sort=sort,
    )

    if format == "json":
        total_records = int(
            app.sparql_client.query(
                TotalRecordsQueryBuilder(query_builder).build_query()
            )[0]["total_records"]
        )
        total_pages = math.ceil(total_records / items_per_page) if total_records > 0 else 0
        models = app.sparql_client.query(
            PaginationQueryBuilder(
                query_builder, page=page, items_per_page=items_per_page
            ).build_query()
        )
        return JSONResponse({"data": models, "total_pages": total_pages})

    if format == "csv":
        models = app.sparql_client.query(query_builder.build_query())
        return StreamingResponse(
            generate_csv_response(
                header=[
                    "model",
                    "model_type",
                    "model_objective_iri",
                    "model_objective",
                    "model_objective_description",
                    "deployment_status",
                    "linked_dataset",
                    "linked_dataset_type",
                    "linked_pipeline",
                    "deployed_on_system",
                    "last_model_update",
                    "last_model_execution",
                    "model_output_utilization",
                    "model_performance_metric",
                    "model_performance_value",
                ],
                values=[x.values() for x in models],
            ),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=find_models.csv"},
        )

    return Response(content="Unsupported format", status_code=400)


@router.get("/query-iri")
async def get_query_iri(request: Request, iri: str):
    return await execute_iri_query(request, iri)


@router.get("/deployed")
async def get_deployed_models(
    request: Request,
    search_term: str = Query(default=None, description="Search term"),
    page: int = Query(default=1, description="Page number"),
    items_per_page: int = Query(default=10, description="Number of models to return per page"),
    sort: Optional[List[str]] = Query(default=None, description="Sort criteria"),
    format: str = Query(default="json", description="Output format (json or csv)"),
) -> Response:
    app = request.app
    query_builder = DeployedModelsQueryBuilder(search_term=search_term, sort=sort)

    if format == "json":
        total_records = int(
            app.sparql_client.query(
                TotalRecordsQueryBuilder(query_builder).build_query()
            )[0]["total_records"]
        )
        total_pages = math.ceil(total_records / items_per_page) if total_records > 0 else 0
        models = app.sparql_client.query(
            PaginationQueryBuilder(
                query_builder, page=page, items_per_page=items_per_page
            ).build_query()
        )
        return JSONResponse({"data": models, "total_pages": total_pages})

    if format == "csv":
        models = app.sparql_client.query(query_builder.build_query())
        return StreamingResponse(
            generate_csv_response(
                header=[
                    "model_name",
                    "model_deployed_on_system",
                    "last_model_update",
                    "model_execution_timestamp",
                    "model_input",
                    "model_output",
                    "model_output_utilization",
                    "model_performance_metric",
                    "model_performance_value",
                ],
                values=[x.values() for x in models],
            ),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=deployed_models.csv"
            },
        )

    return Response(content="Unsupported format", status_code=400)


@router.get("/types")
async def get_model_types(request: Request) -> JSONResponse:
    app = request.app
    query = MODEL_TYPES_QUERY
    if config.sparql_backend == "graphdb":
        query = _inject_explicit_graph(query)
    return JSONResponse(app.sparql_client.query(query))
