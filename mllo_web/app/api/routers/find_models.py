from typing import Optional, List

import math
from fastapi import APIRouter, Request, Query

from mllo_web.app.api.routers.utilities import parse_sort_params
from mllo_web.app.api.services.sparql_client import QueryBuilder

router = APIRouter(prefix="/v1/models", tags=["models"])

QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
select 
    (STRAFTER(STR(?model), "#" ) AS ?model_name) 
    ?model_type 
    ?model_performance_metric 
    ?model_performance_value 
    ?model_objective 
    ?data_preprocessing_pipeline 
    ?ml_input_timestamp ?dataset_used_as where { 
    ?dataset rdf:type/rdfs:subClassOf* <http://purl.obolibrary.org/obo/IAO_0000100>;
     rdf:type/rdfs:label ?dataset_used_as.
    VALUES ?dataset {#target_dataset_iri}
    ?ml_process ml:hasDataInput ?dataset.
    ?ml_process ml:executes ?model.
    OPTIONAL{?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp}
    ?model rdf:type ?model_type_iri.
    ?model bfo:BFO_0000178 ?model_objective.
    ?model_objective rdf:type/rdfs:subClassOf+ iof-core:ObjectiveSpecification.
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
    ?model_type_iri rdfs:label ?model_type.
    OPTIONAL{?ml_process (ml:hasDataOutput/^ml:hasDataInput)+ ?model_performance_assesment.
     ?model_performance_assesment bfo:BFO_0000059 ?model_performance_metric_iri.
     ?model_performance_assesment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment.
	?model_performance_metric_iri rdf:type ?model_performance_metric_type.
    ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric.
    ?model_performance_metric_type rdfs:label ?model_performance_metric.
    ?model_performance_assesment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value}
    OPTIONAL{?data_preprocessing_pipeline ml:hasDataOutput ?dataset.
    		?data_preprocessing_pipeline rdf:type ml:MachineLearningDataPreparationPipeline}
}
"""


class FindModelsQueryBuilder(QueryBuilder):

    def __init__(self, search_term: str, page: int, items_per_page: int, sort: Optional[List[str]], specific_IRI: str):
        self.search_term = search_term
        self.page = page
        self.items_per_page = items_per_page
        self.sort = parse_sort_params(sort)
        self.specific_IRI = specific_IRI

    def build_query(self) -> str:
        #default value for figma.rdf
        # if not self.search_term:
        #     self.search_term = "TestDataSet1"
        if self.specific_IRI:
            query = QUERY.replace("#target_dataset_iri", self.specific_IRI + self.search_term)
        else:
            self.search_term = "\"" + self.search_term + "\")"
            query = QUERY.replace("VALUES ?dataset {#target_dataset_iri}", f"FILTER(STRAFTER(STR(?dataset),\"#\")={self.search_term}")
        return query


@router.get("/")  # Define a GET endpoint for "/models"
async def get_models(request: Request,
                     search_term: str = Query(default=None, description="Search term"),
                     specific_IRI: str = Query(default= None, description="Specific IRI"),
                     page: int = Query(default=1, description="Page number"),
                     items_per_page: int = Query(default=10, description="Number of models to return per page"),
                     sort: Optional[List[str]] = Query(default=None,
                                                       description="Sort criteria (e.g., [dataset_name,asc,dataset_used_as,desc])")) -> dict:
    app = request.app
    print("++++++",specific_IRI, type(specific_IRI))
    models = app.sparql_client.query(
        FindModelsQueryBuilder(search_term, 
                               page=page, 
                               items_per_page=items_per_page, 
                               sort=sort, 
                               specific_IRI=specific_IRI).build_query())

    # Calculate total pages based on results and page size
    total_pages = math.ceil(len(models) / items_per_page) if len(models) > 0 else 0

    # Slice data based on page and results per page
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    displayed_datasets = models[start_index:end_index]

    return {
        "data": displayed_datasets,
        "total_pages": total_pages,
    }
