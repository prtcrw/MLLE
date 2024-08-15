import math
from fastapi import APIRouter, Request, Query

router = APIRouter(prefix="/v1/models", tags=["models"])

QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT 
    (STRAFTER(STR(?model), "#" ) AS ?model_name) 
    ?model_type
    ?model_performance_metric
    ?model_performance_value
    ?model_objective
    ?data_preprocessing_pipeline
    ?ml_input_timestamp
    ?dataset_used_as
WHERE { 
    VALUES ?dataset {
        <http://www.semanticweb.org/milos/ontologies/2024/6/untitled-ontology-707#TestDataSet1>
    }
    ?ml_process ml:hasDataInput ?dataset.
    ?ml_process ml:executes ?model.
    ?dataset rdf:type/rdfs:label ?dataset_used_as.
    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
    }
    OPTIONAL {
        ?model rdf:type ?model_type_iri.
        ?model bfo:BFO_0000178 ?model_objective.
        ?model_objective rdf:type/rdfs:subClassOf+ iof-core:ObjectiveSpecification.
        ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
        ?model_type_iri rdfs:label ?model_type
    }
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


@router.get("/")  # Define a GET endpoint for "/models"
async def get_models(request: Request,
                     page: int = Query(default=1, description="Page number"),
                     items_per_page: int = Query(default=10, description="Number of models to return per page")):
    app = request.app
    models = app.sparql_client.query(QUERY)

    # Calculate total pages based on results and page size
    total_pages = math.ceil(len(models) / items_per_page)

    # Slice data based on page and results per page
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    displayed_datasets = models[start_index:end_index]

    return {
        "data": displayed_datasets,
        "total_pages": total_pages,
    }
