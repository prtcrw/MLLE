import math
from typing import Optional, List

from fastapi import APIRouter, Request, Query
from fastapi.responses import Response, JSONResponse, StreamingResponse

from mllo_web.app.api.routers.utilities import generate_csv_response
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
    ?dataset rdf:type/rdfs:subClassOf* <http://purl.obolibrary.org/obo/IAO_0000100>;
    rdf:type/rdfs:label ?dataset_used_as.
    VALUES ?dataset {#target_dataset_iri}
    ?ml_process ml:hasDataInput ?dataset.
    ?ml_process ml:executes ?model.
    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
    }
    ?model rdf:type ?model_type_iri.
    ?model bfo:BFO_0000178 ?model_objective.
    ?model_objective rdf:type/rdfs:subClassOf+ iof-core:ObjectiveSpecification.
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
    ?model_type_iri rdfs:label ?model_type.
    OPTIONAL {
        ?ml_process (ml:hasDataOutput/^ml:hasDataInput)+ ?model_performance_assessment.
        ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri.
        ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment.
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

    def __init__(self,
                 search_term: str,
                 specific_IRI=None):

        self.search_term = search_term
        self.specific_IRI = specific_IRI

    def build_query(self) -> str:
        query = QUERY

        if not self.search_term:
            query = query.replace("VALUES ?dataset {#target_dataset_iri}", "")

        else:
            if self.specific_IRI != None:
                query = query.replace("#target_dataset_iri", self.specific_IRI + self.search_term)
            else:
                self.search_term = "\"" + self.search_term + "\")"
                query = query.replace("VALUES ?dataset {#target_dataset_iri}",
                                      f"FILTER(STRAFTER(STR(?dataset),\"#\")={self.search_term}")

        return query


@router.get("/")  # Define a GET endpoint for "/models"
async def get_models(request: Request,
                     search_term: str = Query(default=None, description="Search term"),
                     specific_IRI: str = Query(default=None, description="Specific IRI"),
                     page: int = Query(default=1, description="Page number"),
                     items_per_page: int = Query(default=10, description="Number of models to return per page"),
                     sort: Optional[List[str]] = Query(default=None,
                                                       description="Sort criteria (e.g., [dataset_name,asc,dataset_used_as,desc])"),
                     format: str = Query(default="json", description="Output format (json or csv)")) -> Response:
    app = request.app
    query_builder = FindModelsQueryBuilder(search_term, specific_IRI=specific_IRI)

    if format == 'json':
        total_records = int(
            app.sparql_client.query(TotalRecordsQueryBuilder(query_builder).build_query())[0]['total_records'])

        # Calculate total pages based on results and page size
        total_pages = math.ceil(total_records / items_per_page) if total_records > 0 else 0
        models = app.sparql_client.query(
            PaginationQueryBuilder(query_builder, page=page, items_per_page=items_per_page, sort=sort).build_query())

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
