import math
import re
from typing import Optional, List

from fastapi import APIRouter, Request, Query
from fastapi.responses import Response, JSONResponse, StreamingResponse

from mllo_web.app.api.config import get_config
from mllo_web.app.api.routers.utilities import (
    generate_csv_response,
    to_order_by_string,
    parse_option_params,
)
from mllo_web.app.api.services.sparql_client import (
    QueryBuilder,
    TotalRecordsQueryBuilder,
    PaginationQueryBuilder,
)
from .query_iri import execute_iri_query

router = APIRouter(prefix="/v1/models", tags=["models"])
config = get_config()
EXPLICIT_GRAPH = "FROM <http://www.ontotext.com/explicit>"
DATASET_ROLE_CLASS_MAP = {
    "training_data": "ml:TrainingDataSet",
    "test_data": "ml:TestDataSet",
    "validation_data": "ml:ValidationDataSet",
    "production_data": "ml:ProductionMachineLearningDataSet",
    "raw_data": "ml:RawDataSet",
}


def _inject_explicit_graph(query: str) -> str:
    if EXPLICIT_GRAPH in query:
        return query
    return re.sub(
        r"(?is)(SELECT\s+DISTINCT\b.*?)(\bWHERE\s*\{)",
        rf"\1\n{EXPLICIT_GRAPH}\n\2",
        query,
        count=1,
    )


def _build_dataset_role_constraint(dataset_role: dict[str, bool]) -> str:
    selected_classes = [
        class_iri
        for role_name, class_iri in DATASET_ROLE_CLASS_MAP.items()
        if dataset_role.get(role_name, False)
    ]
    if not selected_classes:
        return ""

    return "\n".join([
        "FILTER EXISTS {",
        "  ?dataset rdf:type ?dataset_role_type .",
        f"  VALUES ?dataset_role_filter {{{' '.join(selected_classes)}}}",
        "  ?dataset_role_type rdfs:subClassOf* ?dataset_role_filter .",
        "}",
    ])


FIND_MODELS_QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT 
    ?dataset
    ?dataset_used_as 
    ?dataset_used_for
    ?dataset_characteristics
    ?ml_input_timestamp
    ?model_name 
    ?model_performance_metric
    ?model_performance_value
WHERE {
    {
        SELECT 
            ?dataset
            ?model_name
            ?ml_process
            (GROUP_CONCAT(DISTINCT ?characteristic_type; separator=";") AS ?characteristic_types)
            (GROUP_CONCAT(DISTINCT ?property_info; separator=";") AS ?property_infos)
        WHERE {
            ?ml_process ml:hasDataInput/ml:informationContentEntityDerivedFrom* ?dataset.
            ?ml_process (bfo:BFO_0000057 | ml:executes) ?model_name.
            #DATASET_FILTER
            
            # Get the types of all characteristics
            OPTIONAL {
                ?dataset ml:hasInformationContentEntityCharacteristic ?characteristic.
                ?characteristic rdf:type/rdfs:label ?type.
                BIND(?type AS ?characteristic_type)
            }
            
            # Get property information separately
            OPTIONAL {
                ?dataset ml:hasInformationContentEntityCharacteristic ?characteristic.
                ?characteristic rdf:type/rdfs:label ?type.
                ?characteristic ?data_property ?data_property_value.
                ?data_property rdf:type owl:DatatypeProperty.
                ?data_property rdfs:label ?data_property_name.
                BIND(CONCAT(?type, ", ", ?data_property_name, ": ", STR(?data_property_value)) AS ?property_info)
            }
        }
        GROUP BY
            ?dataset ?model_name ?ml_process
    }
    
    # Combine types and property info in the backend

    #DATASETTYPE_CONSTRAINT
    ?dataset rdf:type ?dataset_type.
    ?dataset_type rdfs:label ?dataset_used_as.
    ?model_name rdf:type ?model_type_iri.
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
    ?model_type_iri rdfs:label ?model_type.
    
    #MODEL_TYPE_FILTER

    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
    }
        
    {?ml_process ml:hasDataOutput ?model_output.
    ?utilization_process ml:hasDataInput ?model_output.
    ?utilization_process rdf:type/rdfs:label ?dataset_used_for.}
    UNION
    {
    ?ml_process rdf:type/rdfs:subClassOf* ml:MachineLearningTraining.
    ?ml_process rdfs:label ?dataset_used_for.
    }

    OPTIONAL {
        ?model_performance_assessment ml:hasDataInput ?model_output.
        ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri.
        ?model_performance_assessment rdf:type/rdfs:subClassOf* ml:ModelPerformanceAssessment.
        ?model_performance_metric_iri rdf:type ?model_performance_metric_type.
        ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric.
        ?model_performance_metric_type rdfs:label ?model_performance_metric.
        ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value.
    }
    
    # Process the combined result
    BIND(CONCAT(
        IF(BOUND(?characteristic_types), ?characteristic_types, ""),
        IF(BOUND(?property_infos) && BOUND(?characteristic_types), ";", ""),
        IF(BOUND(?property_infos), ?property_infos, "")
    ) AS ?dataset_characteristics)
}
"""


class FindModelsQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Dataset Name": "dataset",
        "Dataset Used As": "dataset_used_as",
        "Dataset Used For": "dataset_used_for",
        "Dataset Characteristics": "dataset_characteristics",
        "ML Input Timestamp": "ml_input_timestamp",
        "Model Name": "model_name",
        "Model Performance Metric": "model_performance_metric",
        "Model Performance Value": "model_performance_value",
    }

    def __init__(
        self,
        search_term: str,
        dataset_role: Optional[List[str]] = None,
        specific_IRI: Optional[str] = None,
        model_types: Optional[List[str]] = None,
        sort: Optional[List[str]] = None
    ):

        self.dataset_name = re.sub(re.compile(r'\s+'), '', search_term) if search_term and len(search_term) > 0 else None
        self.specific_IRI = re.sub(re.compile(r'\s+'), '', specific_IRI) if specific_IRI and len(specific_IRI) > 0 else None
        self.model_types = model_types
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.dataset_role = parse_option_params(dataset_role)

    def build_query(self) -> str:
        query = FIND_MODELS_QUERY

        # Handle dataset role filtering
        query = query.replace(
            "#DATASETTYPE_CONSTRAINT",
            _build_dataset_role_constraint(self.dataset_role),
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
                "#DATASET_FILTER", f'FILTER(CONTAINS(STRAFTER(STR(?dataset),"#"),{dataset_name})'
            )

        # Handle model type filtering
        if self.model_types:
            model_types_str = ",".join([f'"{mtype}"' for mtype in self.model_types])
            query = query.replace(
                "#MODEL_TYPE_FILTER", f" FILTER(?model_type IN ({model_types_str}))"
            )

        # Add sorting
        if self.sort_string:
            query += self.sort_string

        if config.sparql_backend == "graphdb":
            query = _inject_explicit_graph(query)

        return query


@router.get("/")  # Define a GET endpoint for "/models"
async def get_models(
    request: Request,
    search_term: str = Query(default=None, description="Search term"),
    dataset_role: Optional[List[str]] = Query(
        default=None, description="Dataset roles as JSON string"
    ),
    specific_IRI=Query(default=None, description="Specific IRI"),
    model_types: Optional[List[str]] = Query(
        default=None, description="Model types"
    ),
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
        sort=sort
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
    # Process data for JSON response
        for dataset in models:
            # Process dataset_characteristics by splitting on semicolon
            if dataset.get("dataset_characteristics") and len(dataset["dataset_characteristics"]) > 0:
                # Split into individual items
                characteristics = [
                    item.strip()
                    for item in dataset["dataset_characteristics"].split(";")
                    if item.strip()
                ]
                
                # Group characteristics by type
                type_to_props = {}
                
                for char in characteristics:
                    # Check if it's a type with properties
                    if "," in char:
                        # Extract the type name (before the first comma)
                        type_name = char.split(",", 1)[0].strip()
                        # Store under the type
                        type_to_props[type_name] = char
                    else:
                        # It's a standalone type, only store if we don't have properties for it
                        if char not in type_to_props:
                            type_to_props[char] = char
                
                # Get the final list of unique characteristics
                dataset["dataset_characteristics"] = list(type_to_props.values())
            else:
                dataset["dataset_characteristics"] = []

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
                    "dataset_name",
                    "dataset_used_as",
                    "dataset_used_for",
                    "ml_input_timestamp",
                    "model_name",
                    "model_performance_metric",
                    "model_performance_value",
                    "dataset_characteristics",
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
    
    ?deployed_state bfo:BFO_0000117 ?model_execution.
    ?model_execution rdf:type/rdfs:subClassOf* ml:ModelExecution.
    ?model_execution ml:hasDataInput ?model_input.
    ?model_execution ml:hasDataOutput ?model_output.
    
    ?ml_training ^bfo:BFO_0000117*/bfo:BFO_0000063 ?model_execution.
    ?ml_training rdf:type/rdfs:subClassOf* ml:MachineLearningTraining.
    
    ?model_execution bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?model_execution_timestamp.
    ?ml_training bfo:BFO_0000224/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?model_training_timestamp.
    
    OPTIONAL { 
        ?model_performance_assessment bfo:BFO_0000059 ?model_performance_metric_iri.
        ?model_performance_assessment ml:hasDataInput ?model_output.
        ?model_performance_assessment rdf:type/rdfs:subClassOf+ ml:ModelPerformanceAssessment.
        
        ?model_performance_metric_iri rdf:type ?model_performance_metric_type.
        ?model_performance_metric_type rdfs:subClassOf+ ml:PerformanceMetric.
        ?model_performance_metric_type rdfs:label ?model_performance_metric.
        
        ?model_performance_assessment ml:hasDataOutput/iof-core:hasSimpleExpressionValue ?model_performance_value.
    }
    
    OPTIONAL { 
        ?model_output_utilization ml:hasDataInput ?model_output.
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
        self.search_term = (
            search_term.strip() if search_term and len(search_term) > 0 else None
        )
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)

    def build_query(self) -> str:
        query = ANALYZE_DEPLOYED_MODELS_QUERY

        if self.sort_string:
            query += self.sort_string

        if config.sparql_backend == "graphdb":
            query = _inject_explicit_graph(query)

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
                "Content-Disposition": f"attachment; filename=deployed_models.csv"
            },
        )
    else:
        return Response(content="Unsupported format", status_code=400)


@router.get("/types")
async def get_model_types(request: Request) -> JSONResponse:
    app = request.app

    try:
        query = MODEL_TYPES_QUERY
        if config.sparql_backend == "graphdb":
            query = _inject_explicit_graph(query)
        result = app.sparql_client.query(query)
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
