import math
from typing import Optional, List
import json

from fastapi import APIRouter, Request, Query
from fastapi.responses import Response, JSONResponse, StreamingResponse

from mllo_web.app.api.routers.utilities import generate_csv_response, to_order_by_string, dataset_role_filter
from mllo_web.app.api.services.sparql_client import QueryBuilder, TotalRecordsQueryBuilder, PaginationQueryBuilder


router = APIRouter(prefix="/v1/models", tags=["models"])

QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
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

    def __init__(self,
                 search_term: str,
                 dataset_role: str,
                 specific_IRI: Optional[str],
                 sort: Optional[List[str]] = None):
        self.dataset_name = search_term.strip() if len(search_term) > 0 else None
        self.specific_IRI = specific_IRI
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.dataset_role = json.loads(dataset_role)

    def build_query(self) -> str:
        query = QUERY

        replacement_string = dataset_role_filter(training_data = self.dataset_role["training_data"],
                                                 test_data = self.dataset_role["test_data"],
                                                 validation_data = self.dataset_role["validation_data"], 
                                                 production_data = self.dataset_role["production_data"],
                                                 raw_data = self.dataset_role["raw_data"])
        query = query.replace("#DATASETTYPE_CONSTRAINT",
                              f"VALUES ?dataset_type {{{replacement_string}}}" if replacement_string else '')

        if not self.dataset_name:
            query = query.replace("#DATASET_FILTER", "")
        elif self.specific_IRI:
            query = query.replace("#DATASET_FILTER", f"VALUES ?dataset {{{self.specific_IRI}{self.dataset_name}}}")
        else:
            dataset_name = f"\"{self.dataset_name}\")"
            query = query.replace("#DATASET_FILTER", f"FILTER(STRAFTER(STR(?dataset),\"#\")={dataset_name}")

        if self.sort_string:
            query += self.sort_string

        print(query)
        return query

@router.get("/")  # Define a GET endpoint for "/models"
async def get_models(request: Request,
                     search_term: str = Query(default=None, description="Search term"),
                     dataset_role: str = Query(default="{}", description="Dataset roles as JSON string"),
                     specific_IRI = Query(default=None, description="Specific IRI"),
                     page: int = Query(default=1, description="Page number"),
                     items_per_page: int = Query(default=10, description="Number of models to return per page"),
                     sort: Optional[List[str]] = Query(default=None,
                                                       description="Sort criteria (e.g., [dataset_name,asc,dataset_used_as,desc])"),
                     format: str = Query(default="json", description="Output format (json or csv)")) -> Response:
    app = request.app
    query_builder = FindModelsQueryBuilder(search_term = search_term, dataset_role = dataset_role, specific_IRI=specific_IRI, sort=sort)

    if format == 'json':
        total_records = int(
            app.sparql_client.query(TotalRecordsQueryBuilder(query_builder).build_query())[0]['total_records'])

        # Calculate total pages based on results and page size
        total_pages = math.ceil(total_records / items_per_page) if total_records > 0 else 0
        models = app.sparql_client.query(
            PaginationQueryBuilder(query_builder, page=page, items_per_page=items_per_page).build_query())

        return JSONResponse({
            "data": models,
            "total_pages": total_pages,
        })
    elif format == 'csv':
        models = app.sparql_client.query(query_builder.build_query())

        return StreamingResponse(
            generate_csv_response(
                header=['model_name', 'model_type', 'model_performance_metric', 'model_performance_value',
                        'model_objective', 'data_preprocessing_pipeline', 'ml_input_timestamp', 'dataset_used_as'],
                values=[x.values() for x in models]),
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename=find_models.csv'}
        )
    else:
        return Response(content="Unsupported format", status_code=400)
