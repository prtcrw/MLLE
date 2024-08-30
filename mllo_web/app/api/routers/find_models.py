import math
from typing import Optional, List

from fastapi import APIRouter, Request, Query
from fastapi.responses import Response, JSONResponse, StreamingResponse

from mllo_web.app.api.routers.utilities import (
    generate_csv_response,
    to_order_by_string,
    dataset_role_filter,
    parse_option_params,
)
from mllo_web.app.api.services.sparql_client import (
    QueryBuilder,
    TotalRecordsQueryBuilder,
    PaginationQueryBuilder,
)
from .query_iri import execute_iri_query

router = APIRouter(prefix="/v1/models", tags=["models"])

FIND_MODELS_QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT 
    (STRAFTER(STR(?model), "#") AS ?model_name) 
    ?model_type
    ?model_performance_metric
    ?model_performance_value
    ?model_objective
    ?data_preprocessing_pipeline
    ?ml_input_timestamp
    ?dataset_used_as 
WHERE {
    #DATASETTYPE_CONSTRAINT
    ?dataset rdf:type ?dataset_type.
    ?dataset_type rdfs:label ?dataset_used_as.
    #DATASET_FILTER
    ?ml_process ml:hasDataInput ?dataset.
    ?ml_process bfo:BFO_0000063*/(bfo:BFO_0000057 | ml:executes) ?model.
    
    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
    }
    
    #DATEFILTER

    ?model rdf:type ?model_type_iri.
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
    ?model_type_iri rdfs:label ?model_type.
    
    #MODEL_TYPE_FILTER

    OPTIONAL {
        ?model bfo:BFO_0000178 ?model_objective.
        ?model_objective rdf:type/rdfs:subClassOf* iof-core:ObjectiveSpecification.
    }
    OPTIONAL {
        ?ml_process ml:hasDataOutput+/^ml:hasDataInput ?model_performance_assessment.
        ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri.
        ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment.
        ?model_performance_metric_iri rdf:type ?model_performance_metric_type.
        ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric.
        ?model_performance_metric_type rdfs:label ?model_performance_metric.
        ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value
    }
    OPTIONAL {
        ?data_preprocessing_pipeline ml:hasDataOutput ?dataset.
        ?data_preprocessing_pipeline rdf:type ml:MachineLearningDataPreparationPipeline
    }
}

"""


class FindModelsQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Model Name": "model_name",
        "Model Type": "model_type",
        "Model Performance Metric": "model_performance_metric",
        "Model Performance Value": "model_performance_value",
        "Model Objective": "model_objective",
        "Data Preprocessing": "data_preprocessing_pipeline",
        "ML Input Timestamp": "ml_input_timestamp",
        "Dataset Used For": "dataset_used_as",
    }

    def __init__(
        self,
        search_term: str,
        dataset_role: Optional[List[str]] = None,
        specific_IRI: Optional[str] = None,
        model_types: Optional[List[str]] = None,
        sort: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_blank_date: Optional[bool] = False,
    ):

        self.dataset_name = (
            search_term.strip() if search_term and len(search_term) > 0 else None
        )
        self.specific_IRI = (
            specific_IRI.strip() if specific_IRI and len(specific_IRI) > 0 else None
        )
        self.model_types = model_types
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.dataset_role = parse_option_params(dataset_role)
        self.start_date = start_date
        self.end_date = end_date
        self.include_blank_date = include_blank_date

    def build_query(self) -> str:
        query = FIND_MODELS_QUERY

        # Handle dataset role filtering
        replacement_string = dataset_role_filter(
            training_data=self.dataset_role.get("training_data", False),
            test_data=self.dataset_role.get("test_data", False),
            validation_data=self.dataset_role.get("validation_data", False),
            production_data=self.dataset_role.get("production_data", False),
            raw_data=self.dataset_role.get("raw_data", False),
        )
        query = query.replace(
            "#DATASETTYPE_CONSTRAINT",
            (
                f"VALUES ?dataset_type {{{replacement_string}}}"
                if replacement_string
                else ""
            ),
        )

        # Handle dataset name or specific IRI filtering
        if not self.dataset_name:
            query = query.replace("#DATASET_FILTER", "")
        elif self.specific_IRI:
            query = query.replace(
                "#DATASET_FILTER",
                f"VALUES ?dataset {{{self.specific_IRI}{self.dataset_name}}}",
            )
        else:
            dataset_name = f'"{self.dataset_name}")'
            query = query.replace(
                "#DATASET_FILTER", f'FILTER(STRAFTER(STR(?dataset),"#")={dataset_name}'
            )

        # Handle model type filtering
        if self.model_types:
            model_types_str = " ".join([f'"{mtype}"' for mtype in self.model_types])
            query = query.replace(
                "#MODEL_TYPE_FILTER", f" FILTER(?model_type IN ({model_types_str}))"
            )

        # Handle date range filtering
        date_filter = f"""FILTER(
                (?ml_input_timestamp >= \"{self.start_date}\"^^xsd:dateTime && 
                ?ml_input_timestamp <= \"{self.end_date}\"^^xsd:dateTime)"""

        if self.include_blank_date:
            date_filter += " || !BOUND(?ml_input_timestamp)"

        date_filter += ")"

        query = query.replace("#DATEFILTER", date_filter)

        # Add sorting
        if self.sort_string:
            query += self.sort_string

        return query


@router.get("/")  # Define a GET endpoint for "/models"
async def get_models(
    request: Request,
    search_term: str = Query(default=None, description="Search term"),
    dataset_role: Optional[List[str]] = Query(
        default=None, description="Dataset roles as JSON string"
    ),
    specific_IRI=Query(default=None, description="Specific IRI"),
    start_date: Optional[str] = Query(
        default=None, description="Start date in YYYY-MM-DD format"
    ),
    end_date: Optional[str] = Query(
        default=None, description="End date in YYYY-MM-DD format"
    ),
    include_blank_date: bool = Query(
        default=False, description="Include entries with blank date"
    ),
    model_types: Optional[List[str]] = Query(
        default=None, description="Model types"
    ),  # Add model_types parameter
    page: int = Query(default=1, description="Page number"),
    items_per_page: int = Query(
        default=10, description="Number of models to return per page"
    ),
    sort: Optional[List[str]] = Query(
        default=None,
        description="Sort criteria (e.g., [dataset_name,asc,dataset_used_as,desc])",
    ),
    format: str = Query(default="json", description="Output format (json or csv)"),
) -> Response:
    app = request.app
    query_builder = FindModelsQueryBuilder(
        search_term=search_term,
        dataset_role=dataset_role,
        specific_IRI=specific_IRI,
        model_types=model_types,
        sort=sort,
        start_date=start_date,
        end_date=end_date,
        include_blank_date=include_blank_date,
    )

    if format == "json":
        total_records = int(
            app.sparql_client.query(
                TotalRecordsQueryBuilder(query_builder).build_query()
            )[0]["total_records"]
        )

        # Calculate total pages based on results and page size
        total_pages = (
            math.ceil(total_records / items_per_page) if total_records > 0 else 0
        )
        models = app.sparql_client.query(
            PaginationQueryBuilder(
                query_builder, page=page, items_per_page=items_per_page
            ).build_query()
        )

        return JSONResponse(
            {
                "data": models,
                "total_pages": total_pages,
            }
        )
    elif format == "csv":
        models = app.sparql_client.query(query_builder.build_query())

        return StreamingResponse(
            generate_csv_response(
                header=[
                    "model_name",
                    "model_type",
                    "model_performance_metric",
                    "model_performance_value",
                    "model_objective",
                    "data_preprocessing_pipeline",
                    "ml_input_timestamp",
                    "dataset_used_as",
                ],
                values=[x.values() for x in models],
            ),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=find_models.csv"},
        )
    else:
        return Response(content="Unsupported format", status_code=400)


@router.get("/query-iri")
async def get_query_iri(request: Request, iri: str):
    return await execute_iri_query(request, iri)


ANALYZE_DEPLOYED_MODELS_QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    (STRAFTER(STR(?model), "#") AS ?model_name)
    ?model_deployed_on_system
    ?last_model_update
    ?model_execution_timestamp
    ?model_input_data
    ?model_output_data
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value
WHERE {
    ?dataset rdf:type ?dataset_type.
    ?dataset_type rdfs:label ?dataset_used_as.
    ?ml_process ml:hasDataInput ?dataset.
    ?ml_process bfo:BFO_0000063*/(bfo:BFO_0000057 | ml:executes) ?model.
    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
    }
    ?model rdf:type ?model_type_iri.
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
    ?model_type_iri rdfs:label ?model_type.
    OPTIONAL {
        ?model bfo:BFO_0000178 ?model_objective.
        ?model_objective rdf:type/rdfs:subClassOf* iof-core:ObjectiveSpecification.
    }
    OPTIONAL {
        ?ml_process ml:hasDataOutput+/^ml:hasDataInput ?model_performance_assessment.
        ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri.
        ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment.
        ?model_performance_metric_iri rdf:type ?model_performance_metric_type.
        ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric.
        ?model_performance_metric_type rdfs:label ?model_performance_metric.
        ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value
    }
    OPTIONAL {
        ?data_preprocessing_pipeline ml:hasDataOutput ?dataset.
    	?data_preprocessing_pipeline rdf:type ml:MachineLearningDataPreparationPipeline
    }
}    
"""


class DeployedModelsQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Model Name": "model_name",
        "Model Deployed on System": "model_deployed_on_system",
        "Last Model Update": "last_model_update",
        "Model Execution Timestamp": "model_execution_timestamp",
        "Model Input Data": "model_input_data",
        "Model Output Data": "model_output_data",
        "Model Output Utilization": "model_output_utilization",
        "Model Performance Metric": "model_performance_metric",
        "Model Performance Value": "model_performance_value",
    }

    def __init__(self, search_term: str, sort: Optional[List[str]] = None):
        self.search_term = (
            search_term.strip() if search_term and len(search_term) > 0 else None
        )
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)

    def build_query(self) -> str:
        query = ANALYZE_DEPLOYED_MODELS_QUERY

        if self.sort_string:
            query += self.sort_string

        return query


MODEL_TYPES_QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>

SELECT DISTINCT ?model_type
WHERE {
    ?model rdf:type ?model_type_iri.
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
    ?model_type_iri rdfs:label ?model_type.
}
"""


@router.get("/deployed")  # Define a GET endpoint for "/models/deployed"
async def get_deployed_models(
    request: Request,
    search_term: str = Query(default=None, description="Search term"),
    page: int = Query(default=1, description="Page number"),
    items_per_page: int = Query(
        default=10, description="Number of models to return per page"
    ),
    sort: Optional[List[str]] = Query(
        default=None,
        description="Sort criteria (e.g., [model_name,asc,last_model_update,desc])",
    ),
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

        # Calculate total pages based on results and page size
        total_pages = (
            math.ceil(total_records / items_per_page) if total_records > 0 else 0
        )
        models = app.sparql_client.query(
            PaginationQueryBuilder(
                query_builder, page=page, items_per_page=items_per_page
            ).build_query()
        )

        return JSONResponse(
            {
                "data": models,
                "total_pages": total_pages,
            }
        )
    elif format == "csv":
        models = app.sparql_client.query(query_builder.build_query())

        return StreamingResponse(
            generate_csv_response(
                header=[
                    "model_name",
                    "model_deployed_on_system",
                    "last_model_update",
                    "model_execution_timestamp",
                    "model_input_data",
                    "model_output_data",
                    "model_output_utilization",
                    "model_performance_metric",
                    "model_performance_value",
                ],
                values=[x.values() for x in models],
            ),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=deployed_models.csv"
            },
        )
    else:
        return Response(content="Unsupported format", status_code=400)


@router.get("/types")
async def get_model_types(request: Request) -> JSONResponse:
    app = request.app

    try:
        result = app.sparql_client.query(MODEL_TYPES_QUERY)
        model_type = [row["model_type"] for row in result]
        return JSONResponse(content=model_type)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


DATE_RANGE_QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>

SELECT (MIN(?ml_input_timestamp) AS ?minDate) 
       (MAX(?ml_input_timestamp) AS ?maxDate) 
       ?ml_input_timestamp
WHERE {
  ?ml_process ml:hasDataInput ?dataset.
  ?ml_process bfo:BFO_0000063*/(bfo:BFO_0000057 | ml:executes) ?model.
  OPTIONAL {
    ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
  }
} 
GROUP BY ?ml_input_timestamp
ORDER BY ?ml_input_timestamp
"""


@router.get("/date-range")
async def get_date_range(request: Request) -> JSONResponse:
    app = request.app

    try:
        result = app.sparql_client.query(DATE_RANGE_QUERY)
        min_date = result[1]["minDate"]
        max_date = result[1]["maxDate"]
        available_dates = [row["ml_input_timestamp"] for row in result]

        # to show the slidebar
        min_date = "2023-04-13T07:56:00-04:00"
        max_date = "2024-08-13T07:56:00-04:00"
        available_dates = [
            min_date,
            "2024-05-11T07:56:00-04:00",
            "2024-07-13T07:56:00-04:00",
            "2024-06-11T07:56:00-04:00",
            max_date,
        ]
        return JSONResponse(
            content={
                "min_date": min_date,
                "max_date": max_date,
                "available_dates": sorted(available_dates),
            }
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
