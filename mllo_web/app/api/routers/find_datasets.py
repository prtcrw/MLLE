import json
import re
import math
from collections import defaultdict
from contextlib import closing
from typing import Optional, List
import os
import pandas as pd

import numpy as np
from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse, Response, JSONResponse
from sklearn.decomposition import PCA

from mllo_web.app.api.config import get_config
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

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])
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
QUERY = """
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT 
    #variables
WHERE {
    {
        ?ml_process ml:executes | bfo:BFO_0000057 ?model.
        OPTIONAL { ?dataset rdfs:label ?dataset_label }
        #DATASET_SEARCH_FILTER
        ?model rdf:type ?model_type_iri.
        ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
        ?model_type_iri rdfs:label ?model_type.
        #MODEL_TYPE_FILTER
        ?model bfo:BFO_0000178 ?model_objective.
        ?model_objective rdf:type/rdfs:label ?objective_type.
        #OBJECTIVE_TYPE_FILTER
        ?ml_process ml:hasDataInput ?dataset.
        #DATASETTYPE_CONSTRAINT
        ?dataset rdf:type ?dataset_type.
        OPTIONAL {
            ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeValue ?ml_input_timestamp
        }
        OPTIONAL {
            ?dataset ml:informationContentEntityDerivedFrom ?dataset_source
        }
        OPTIONAL {
            ?ml_process ml:hasDataOutput ?model_output
            OPTIONAL {
                ?utilization_process ml:hasDataInput ?model_output.
                ?utilization_process rdf:type/rdfs:label ?model_output_utilization
            }
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
    }
    UNION
    {
        ?dataset rdf:type ?dataset_type.
        #UNLINKED_DATASETTYPE_CONSTRAINT
        ?dataset_type rdfs:subClassOf* ml:MachineLearningDataSet.
        FILTER NOT EXISTS { ?ml_process ml:hasDataInput ?dataset. }

        OPTIONAL {
            ?dataset ml:informationContentEntityDerivedFrom ?dataset_source
        }

        OPTIONAL { ?dataset rdfs:label ?dataset_label }

        #UNLINKED_DATASET_FILTER
        #UNLINKED_MODEL_TYPE_FILTER

        BIND("Unlinked dataset" AS ?model)
        BIND("Unlinked dataset" AS ?model_type)
        BIND("Not linked to an ML workflow" AS ?model_objective)
        BIND("" AS ?ml_input_timestamp)
        BIND("" AS ?model_output)
        BIND("Standalone dataset" AS ?model_output_utilization)
    }
}
"""


class FindDatasetsQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Model Input": "dataset",
        "Model": "model",
        "ML Input Timestamp": "ml_input_timestamp",
        "Model Objective": "model_objective",
        "Model Type": "model_type",
        "Model Output": "model_output",
        "Raw Data": "raw_data",
        "Model Output Utilization": "model_output_utilization",
    }

    def __init__(
        self,
        query_variables: List[str],
        search_term: Optional[str] = None,
        type_query: bool = False,
        dataset_role: Optional[List[str]] = None,
        sort: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        model_types: Optional[List[str]] = None,
        include_blank_date: Optional[bool] = False,
    ):
        self.query_variables = query_variables
        self.model_input = re.sub(re.compile(r'\s+'), '', search_term) if search_term and len(search_term) > 0 else None
        self.type_query = type_query
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.dataset_role = parse_option_params(dataset_role)
        self.start_date = start_date
        self.end_date = end_date
        self.include_blank_date = include_blank_date
        self.model_types = model_types

    def build_query(self) -> str:
        query = QUERY
        query = query.replace("#variables", "\n\t".join(self.query_variables))

        # Apply sort based on the mapping
        if self.dataset_role:
            replacement_string = dataset_role_filter(
                training_data=self.dataset_role.get("training_data", False),
                test_data=self.dataset_role.get("test_data", False),
                validation_data=self.dataset_role.get("validation_data", False),
                production_data=self.dataset_role.get("production_data", False),
                raw_data=False,
            )
            query = query.replace(
                "#DATASETTYPE_CONSTRAINT",
                (
                    f"VALUES ?dataset_type {{{replacement_string}}}"
                    if replacement_string
                    else ""
                ),
            )
            query = query.replace(
                "#UNLINKED_DATASETTYPE_CONSTRAINT",
                (
                    f"VALUES ?dataset_type {{{replacement_string}}}"
                    if replacement_string
                    else ""
                ),
            )
        else:
            query = query.replace("#DATASETTYPE_CONSTRAINT", "")
            query = query.replace("#UNLINKED_DATASETTYPE_CONSTRAINT", "")

        if self.model_input:
            if self.type_query:
                query = query.replace(
                    "#OBJECTIVE_TYPE_FILTER",
                    'FILTER(CONTAINS(STR(?objective_type),'+ '"'+ self.model_input + '"))'
                )
                query = query.replace(
                    "#UNLINKED_DATASET_FILTER",
                    (
                        'FILTER('
                        f'CONTAINS(LCASE(COALESCE(?dataset_label, "")), LCASE("{self.model_input}")) '
                        f'|| CONTAINS(LCASE(STR(?dataset)), LCASE("{self.model_input}"))'
                        ')'
                    )
                )
            else:
                query = query.replace(
                    "#DATASET_SEARCH_FILTER",
                    (
                        'FILTER('
                        f'CONTAINS(LCASE(COALESCE(?dataset_label, "")), LCASE("{self.model_input}")) '
                        f'|| CONTAINS(LCASE(STR(?dataset)), LCASE("{self.model_input}"))'
                        ')'
                    )
                )
                query = query.replace(
                    "#UNLINKED_DATASET_FILTER",
                    (
                        'FILTER('
                        f'CONTAINS(LCASE(COALESCE(?dataset_label, "")), LCASE("{self.model_input}")) '
                        f'|| CONTAINS(LCASE(STR(?dataset)), LCASE("{self.model_input}"))'
                        ')'
                    )
                )
        if self.model_types:
            model_types_str = ",".join([f'"{mtype}"' for mtype in self.model_types])
            query = query.replace(
                "#MODEL_TYPE_FILTER", f" FILTER(?model_type IN ({model_types_str}))"
            )
            query = query.replace("#UNLINKED_MODEL_TYPE_FILTER", "FILTER(false)")

        query = query.replace("#DATASET_SEARCH_FILTER", "")
        query = query.replace("#OBJECTIVE_TYPE_FILTER", "")
        query = query.replace("#MODEL_TYPE_FILTER", "")
        query = query.replace("#UNLINKED_DATASET_FILTER", "")
        query = query.replace("#UNLINKED_MODEL_TYPE_FILTER", "")

        # Apply sort based on the mapping
        if self.sort_string:
            query += self.sort_string

        if config.sparql_backend == "graphdb":
            query = _inject_explicit_graph(query)

        return query


@router.get("/")  # Define a GET endpoint for "/datasets"
async def get_datasets(
    request: Request,
    search_term: str = Query(default=None, description="Search term"),
    dataset_role: Optional[List[str]] = Query(
        default=None, description="Dataset roles"
    ),
    type_query: bool = Query(
        default=True, description="Toggle for Model Name <-> Model Type"
    ),
    direct_type: bool = Query(default=False, description="Direct Type constraint"),
    model_types: Optional[List[str]] = Query(
        default=None, description="Model types"
    ),
    start_date: Optional[str] = Query(
        default=None, description="Start date in YYYY-MM-DD format"
    ),
    end_date: Optional[str] = Query(
        default=None, description="End date in YYYY-MM-DD format"
    ),
    include_blank_date: bool = Query(
        default=False, description="Include entries with blank date"
    ),
    page: int = Query(default=1, description="Page number"),
    items_per_page: int = Query(
        default=10, description="Number of datasets to return per page"
    ),
    sort: Optional[List[str]] = Query(
        default=None,
        description="Sort criteria (e.g., [dataset_name,asc,dataset_used_as,desc])",
    ),
    format: str = Query(default="json", description="Output format (json or csv)"),
) -> Response:
    app = request.app
    query_builder = FindDatasetsQueryBuilder(
        query_variables=[
            "?model",
            "?model_type",
            "?model_objective",
            "?dataset",
            "?ml_input_timestamp",
            "?model_output",
            "?model_output_utilization",
        ],
        search_term=search_term,
        dataset_role=dataset_role,
        type_query=type_query,
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
        datasets = app.sparql_client.query(
            PaginationQueryBuilder(
                query_builder, page=page, items_per_page=items_per_page
            ).build_query()
        )

        return JSONResponse(
            {
                "data": datasets,
                "total_pages": total_pages,
            }
        )
    elif format == "csv":
        datasets = app.sparql_client.query(query_builder.build_query())

        return StreamingResponse(
            generate_csv_response(
                header=[
                    "model",
                    "model_type",
                    "model_objective",
                    "model_input",
                    "ml_input_timestamp",
                    "model_output",
                    "model_output_utilization",
                ],
                values=[x.values() for x in datasets],
            ),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=find_datasets.csv"},
        )
    else:
        return Response(content="Unsupported format", status_code=400)


@router.get("/query-iri")
async def get_query_iri(request: Request, iri: str):
    return await execute_iri_query(request, iri)


@router.get("/performances")  # Define a GET endpoint for "/datasets/performances"
@router.get("/performances/")  # Accept trailing slash for frontend compatibility
async def get_datasets_performances(
    request: Request,
    search_term: str = Query(default=None, description="Search term"),
    dataset_role: str = Query(default=None, description="Dataset roles"),
    type_query: bool = Query(default=True, description="Toggle for Model Name <-> Model Type")
) -> Response:
    app = request.app
    query_builder = FindDatasetsQueryBuilder(
        query_variables=[
            '(STRAFTER(STR(?dataset), "#") AS ?dataset_name)',
            '(STRAFTER(STR(?model), "#") AS ?model_name)',
            '?model_type',
            '(STRAFTER(STR(?dataset_source), "#") AS ?raw_data)',
            "?model_performance_metric",
            "?model_performance_value",
        ],
        search_term=search_term,
        dataset_role=dataset_role,
        type_query=type_query,
        sort=["Dataset Name, asc"],
    )
    datasets = app.sparql_client.query(query_builder.build_query())

    datasets_group_by_model_performance_metric = defaultdict(list)
    for entry in datasets:
        metric = entry.pop(
            "model_performance_metric"
        )  # Remove the metric key and get its value
        if metric:
            datasets_group_by_model_performance_metric[metric].append(entry)

    # Sort each group by 'dataset_name'
    for metric in datasets_group_by_model_performance_metric:
        datasets_group_by_model_performance_metric[metric].sort(
            key=lambda x: x["dataset_name"]
        )

    return JSONResponse(
        {"model_performance_metric": dict(datasets_group_by_model_performance_metric)}
    )

@router.get("/model-pca")
async def get_model_pca(
    request: Request,
    input_dataset_name: str = Query(None, description="Name of the input dataset"),
    output_dataset_name: str = Query(None, description="Name of the output dataset")
) -> Response:

    input_dataset_dir = os.path.join('datasets', 'input_datasets', input_dataset_name)
    output_dataset_dir = os.path.join('datasets', 'output_datasets', output_dataset_name)

    # Load the input dataset (e.g., MNIST dataset)
    input_data = np.load(input_dataset_dir)
    data = input_data.reshape(input_data.shape[0], 28*28)

    # Apply PCA with 2 components for 2D plot
    n_components = 2
    pca = PCA(n_components=n_components)
    pca.fit(data)
    pca_data = pca.transform(data)

    # Load the output dataset (e.g., classification labels)
    output_data = np.genfromtxt(output_dataset_dir, delimiter=',')
    labels = output_data.tolist()
    unique_labels = list(set(labels))

    # Prepare the results for the frontend
    results = {
        "metadata": {
            "algorithm": "PCA",
            "n_components": n_components,
            "method": "classification",
            "labels": sorted(unique_labels),
        },
        "data": [
            {"label": label, "x": x, "y": y}
            for label, x, y in zip(
                labels, pca_data[:, 0].tolist(), pca_data[:, 1].tolist()
            )
        ],
    }

    return JSONResponse({"results": results})

@router.get("/model-input-list")
async def list_model_inputs(request: Request) -> Response:
    dataset_dir = os.path.join('datasets', 'input_datasets')

    # Get the list of all .npy files in the directory
    datasets = [f for f in os.listdir(dataset_dir) if f.endswith('.npy')]
    datasets.sort()
    return JSONResponse({"datasets": datasets})

@router.get("/model-output-list")
async def list_model_outputs(request: Request) -> Response:
    dataset_dir = os.path.join('datasets', 'output_datasets')

    # Get the list of all CSV files in the directory
    datasets = [f for f in os.listdir(dataset_dir) if f.endswith('.csv')]
    datasets.sort()
    return JSONResponse({"datasets": datasets})

@router.get("/model-output")
async def get_model_output(request: Request, dataset_names: List[str] = Query(None, description="List of dataset names", delimiter=",")) -> JSONResponse:
    if not dataset_names:
        return JSONResponse({"error": "No dataset names provided"}, status_code=400)

    # Load the MNIST dataset (do this only once)
    true_classes = np.genfromtxt(os.path.join('datasets', 'y_test.csv'), delimiter= ',')

    all_results = []
    for dataset_name in dataset_names:
        file_path = os.path.join('datasets', 'output_datasets', dataset_name)
        if not os.path.exists(file_path):
            return JSONResponse({"error": f"Dataset not found: {dataset_name}"}, status_code=404)

        predicted_classes = np.genfromtxt(file_path, delimiter=',')
        
        # Ensure predicted_classes has the same length as true_classes
        if len(predicted_classes) != len(true_classes):
            return JSONResponse({"error": f"Mismatch in data length for dataset: {dataset_name}"}, status_code=400)

        # Create a list of dictionaries with true and predicted labels
        results = [
            {"true_label": int(true), "predicted_label": int(pred)}
            for true, pred in zip(true_classes, predicted_classes)
        ]

        all_results.append({"dataset": dataset_name, "results": results})

    return JSONResponse({"results": all_results})
