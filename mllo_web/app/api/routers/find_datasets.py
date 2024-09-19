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
from sklearn.datasets import fetch_openml
from sklearn.decomposition import PCA

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
        SELECT 
            ?dataset
            ?model
            ?ml_process
            (GROUP_CONCAT(?dataset_characteristic; separator=";") as ?dataset_characteristics)
        WHERE {
            ?ml_process ml:executes | bfo:BFO_0000057 ?model.
            ?ml_process ml:hasDataInput ?dataset.
            ?model rdf:type/rdfs:subClassOf#ml_input_constraint.
            OPTIONAL {
                ?dataset ml:hasInformationContentEntityCharacteristic ?dataset_characteristic
            }
        }
        GROUP BY
            ?dataset ?model ?ml_process
    }
    ?model rdf:type/rdfs:label ?model_type.
    #DATASETTYPE_CONSTRAINT
    ?dataset rdf:type ?dataset_type.
    ?dataset_type rdfs:label ?dataset_used_as.
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
        ?data_preprocessing_pipeline bfo:BFO_0000063*/ml:hasDataOutput ?dataset.
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
    }

    def __init__(
        self,
        query_variables: List[str],
        search_term: Optional[str] = None,
        type_query: bool = True,
        direct_type: bool = False,
        dataset_role: Optional[List[str]] = None,
        sort: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_blank_date: Optional[bool] = False,
    ):
        self.query_variables = query_variables
        self.model_input = re.sub(re.compile(r'\s+'), '', search_term) if search_term and len(search_term) > 0 else None
        self.type_query = type_query
        self.direct_type = direct_type
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.dataset_role = parse_option_params(dataset_role)
        self.start_date = start_date
        self.end_date = end_date
        self.include_blank_date = include_blank_date

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

        if not self.model_input:
            query = query.replace("#ml_input_constraint", "+ ml:MachineLearningModel")
        else:
            if self.type_query:
                if self.direct_type:
                    query = query.replace(
                        "#ml_input_constraint", " ml:" + self.model_input
                    )
                else:
                    query = query.replace(
                        "#ml_input_constraint", "* ml:" + self.model_input
                    )
            else:
                query = query.replace(
                    "?model rdf:type/rdfs:subClassOf#ml_input_constraint.",
                    'FILTER(CONTAINS(STRAFTER(STR(?model),"#"),'+ '"'+ self.model_input + '"))'
                )

        # Apply sort based on the mapping
        if self.sort_string:
            query += self.sort_string

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
            '(STRAFTER(STR(?dataset), "#") AS ?dataset_name)',
            "?dataset_used_as" "?ml_input_timestamp",
            "?dataset_shape",
            "?dataset_characteristics",
            "?dataset_source",
            "?model_type",
            "?model_output",
            "?model_output_utilization",
        ],
        search_term=search_term,
        dataset_role=dataset_role,
        type_query=type_query,
        direct_type=direct_type,
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

        # Process data for JSON response
        for dataset in datasets:
            # Split dataset_characteristics by semicolon, remove leading/trailing whitespaces
            if len(dataset["dataset_characteristics"]) > 0:
                dataset["dataset_characteristics"] = [
                    component.strip()
                    for component in dataset["dataset_characteristics"].split(";")
                ]

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
                    "dataset_name",
                    "dataset_used_as",
                    "ml_input_timestamp",
                    "dataset_shape",
                    "dataset_characteristics",
                    "dataset_source",
                    "model_type",
                    "model_output",
                    "model_output_utilization",
                    "model_performance_metric",
                    "model_performance_value",
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
    (_, _), (_, y_test) = mnist.load_data()
    y_test = to_categorical(y_test)
    true_classes = np.argmax(y_test, axis=1)

    all_results = []
    print(dataset_names)
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
