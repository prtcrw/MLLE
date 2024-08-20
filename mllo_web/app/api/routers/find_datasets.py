import math
from typing import Optional, List

from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse, Response, JSONResponse

from mllo_web.app.api.routers.utilities import generate_csv_response, to_order_by_string
from mllo_web.app.api.services.sparql_client import QueryBuilder, TotalRecordsQueryBuilder, PaginationQueryBuilder

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])

QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT
    (STRAFTER(STR(?dataset), "#") AS ?dataset_name)
    ?dataset_used_as
    ?ml_input_timestamp
    ?dataset_shape
    ?dataset_characteristics
    ?dataset_source
    ?model_type
    ?model_output
    ?model_output_utilization
    ?model_performance_metric
    ?model_performance_value
WHERE { 
    {
        SELECT 
            ?dataset
            ?model
            ?ml_process
            (GROUP_CONCAT(?dataset_characteristic; separator=";") AS ?dataset_characteristics)
        WHERE {
            ?model rdf:type/rdfs:subClassOf ml:ArtificialNeuralNetwork.
            ?ml_process ml:hasDataInput ?dataset.
            ?ml_process ml:executes | bfo:BFO_0000057 ?model.
            OPTIONAL {
                ?dataset ml:hasInformationContentEntityCharacteristic ?dataset_characteristic
            }
        }
        GROUP BY
            ?dataset ?model ?ml_process
    }
    ?model rdf:type/rdfs:label ?model_type.
    ?dataset rdf:type/rdfs:label ?dataset_used_as.
    ?dataset ml:specifiesDimensionShape ?dataset_shape.
    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
    }
    OPTIONAL {
        ?dataset ml:informationContentEntityDerivedFrom ?dataset_source
    }
    OPTIONAL {
        ?ml_process ml:executes ?model.
        ?ml_process ml:hasDataInput ?dataset.
        ?ml_process ml:hasDataOutput ?model_output
        OPTIONAL { 
            ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri.
            ?model_performance_assessment ml:hasDataInput ?model_output.
            ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment.
            ?model_performance_metric_iri rdf:type ?model_performance_metric_type.
            ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric.
            ?model_performance_metric_type rdfs:label ?model_performance_metric.
            ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value
        }
        OPTIONAL {
            ?utilization_process ml:hasDataInput ?model_output.
            ?utilization_process rdf:type/rdfs:label ?model_output_utilization
        }
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


class FindDatasetsQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Dataset Name": "dataset_name",
        "Dataset Used As": "dataset_used_as",
        "ML Input Timestamp": "ml_input_timestamp",
        "Dataset Shape": "dataset_shape",
        "Dataset Characteristics": "dataset_characteristics",
        "Dataset Source": "dataset_source",
        "Model Type": "model_type",
        "Model Output": "model_output",
        "Model Output Utilization": "model_output_utilization",
        "Model Performance Metric": "model_performance_metric",
        "Model Performance Value": "model_performance_value",
    }

    def __init__(self, search_term: str,
                 sort: Optional[List[str]]):
        self.search_term = search_term
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)

    def build_query(self) -> str:
        query = QUERY
        # TODO: Handle 'search_term'

        # Apply sort based on the mapping
        if self.sort_string:
            query += self.sort_string

        return query


@router.get("/")  # Define a GET endpoint for "/datasets"
async def get_datasets(request: Request,
                       search_term: str = Query(default=None, description="Search term"),
                       page: int = Query(default=1, description="Page number"),
                       items_per_page: int = Query(default=10, description="Number of datasets to return per page"),
                       sort: Optional[List[str]] = Query(default=None,
                                                         description="Sort criteria (e.g., [dataset_name,asc,dataset_used_as,desc])"),
                       format: str = Query(default="json", description="Output format (json or csv)")) -> Response:
    app = request.app
    query_builder = FindDatasetsQueryBuilder(search_term, sort=sort)

    if format == 'json':
        total_records = int(
            app.sparql_client.query(TotalRecordsQueryBuilder(query_builder).build_query())[0]['total_records'])

        # Calculate total pages based on results and page size
        total_pages = math.ceil(total_records / items_per_page) if total_records > 0 else 0
        datasets = app.sparql_client.query(
            PaginationQueryBuilder(query_builder, page=page, items_per_page=items_per_page).build_query())

        # Process data for JSON response
        for dataset in datasets:
            # Split dataset_characteristics by semicolon, remove leading/trailing whitespaces
            if len(dataset['dataset_characteristics']) > 0:
                dataset['dataset_characteristics'] = [component.strip() for component in
                                                      dataset['dataset_characteristics'].split(';')]

        return JSONResponse({
            "data": datasets,
            "total_pages": total_pages,
        })
    elif format == 'csv':
        datasets = app.sparql_client.query(query_builder.build_query())

        return StreamingResponse(
            generate_csv_response(header=['dataset_name', 'dataset_used_as', 'ml_input_timestamp', 'dataset_shape',
                                          'dataset_characteristics', 'dataset_source', 'model_type', 'model_output',
                                          'model_output_utilization', 'model_performance_metric',
                                          'model_performance_value'],
                                  values=[x.values() for x in datasets]),
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename=find_datasets.csv'}
        )
    else:
        return Response(content="Unsupported format", status_code=400)
