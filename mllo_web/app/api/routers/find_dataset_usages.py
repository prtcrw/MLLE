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

router = APIRouter(prefix="/v1/dataset-usages", tags=["dataset-usages"])
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


FIND_DATASET_USAGES_QUERY = """
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/construct/>
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
            ?ml_process (ml:executed | bfo:BFO_0000057) ?model_name.
            #DATASET_FILTER

            OPTIONAL {
                ?dataset ml:hasInformationContentEntityCharacteristic ?characteristic.
                ?characteristic rdf:type/rdfs:label ?type.
                BIND(?type AS ?characteristic_type)
            }

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

    #DATASETTYPE_CONSTRAINT
    ?dataset rdf:type ?dataset_type.
    ?dataset_type rdfs:label ?dataset_used_as.
    ?model_name rdf:type ?model_type_iri.
    ?model_type_iri rdfs:subClassOf+ ml:MachineLearningModel.
    ?model_type_iri rdfs:label ?model_type.

    #MODEL_TYPE_FILTER

    OPTIONAL {
        ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeInstantValue ?ml_input_timestamp
    }

    {
        ?ml_process ml:hasDataOutput ?model_output.
        ?utilization_process ml:hasDataInput ?model_output.
        ?utilization_process rdf:type/rdfs:label ?dataset_used_for.
    }
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

    BIND(CONCAT(
        IF(BOUND(?characteristic_types), ?characteristic_types, ""),
        IF(BOUND(?property_infos) && BOUND(?characteristic_types), ";", ""),
        IF(BOUND(?property_infos), ?property_infos, "")
    ) AS ?dataset_characteristics)
}
"""


class FindDatasetUsagesQueryBuilder(QueryBuilder):
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
        sort: Optional[List[str]] = None,
    ):
        self.dataset_name = re.sub(re.compile(r"\s+"), "", search_term) if search_term and len(search_term) > 0 else None
        self.specific_IRI = re.sub(re.compile(r"\s+"), "", specific_IRI) if specific_IRI and len(specific_IRI) > 0 else None
        self.model_types = model_types
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.dataset_role = parse_option_params(dataset_role)

    def build_query(self) -> str:
        query = FIND_DATASET_USAGES_QUERY

        query = query.replace(
            "#DATASETTYPE_CONSTRAINT",
            _build_dataset_role_constraint(self.dataset_role),
        )

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
                "#DATASET_FILTER",
                f'FILTER(CONTAINS(STRAFTER(STR(?dataset),"#"),{dataset_name})',
            )

        if self.model_types:
            model_types_str = ",".join([f'"{mtype}"' for mtype in self.model_types])
            query = query.replace(
                "#MODEL_TYPE_FILTER",
                f" FILTER(?model_type IN ({model_types_str}))",
            )
        else:
            query = query.replace("#MODEL_TYPE_FILTER", "")

        if self.sort_string:
            query += self.sort_string

        if config.sparql_backend == "graphdb":
            query = _inject_explicit_graph(query)

        return query


@router.get("/")
async def get_dataset_usages(
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
        default=10, description="Number of rows to return per page"
    ),
    sort: Optional[List[str]] = Query(
        default=None,
        description="Sort criteria (e.g., [dataset_name,asc,dataset_used_as,desc])",
    ),
    format: str = Query(default="json", description="Output format (json or csv)"),
) -> Response:
    app = request.app
    query_builder = FindDatasetUsagesQueryBuilder(
        search_term=search_term,
        dataset_role=dataset_role,
        specific_IRI=specific_IRI,
        model_types=model_types,
        sort=sort,
    )

    if format == "json":
        total_records = int(
            app.sparql_client.query(
                TotalRecordsQueryBuilder(query_builder).build_query()
            )[0]["total_records"]
        )

        total_pages = (
            math.ceil(total_records / items_per_page) if total_records > 0 else 0
        )
        usages = app.sparql_client.query(
            PaginationQueryBuilder(
                query_builder, page=page, items_per_page=items_per_page
            ).build_query()
        )

        for dataset in usages:
            if dataset.get("dataset_characteristics") and len(dataset["dataset_characteristics"]) > 0:
                characteristics = [
                    item.strip()
                    for item in dataset["dataset_characteristics"].split(";")
                    if item.strip()
                ]
                type_to_props = {}

                for char in characteristics:
                    if "," in char:
                        type_name = char.split(",", 1)[0].strip()
                        type_to_props[type_name] = char
                    else:
                        if char not in type_to_props:
                            type_to_props[char] = char

                dataset["dataset_characteristics"] = list(type_to_props.values())
            else:
                dataset["dataset_characteristics"] = []

        return JSONResponse(
            {
                "data": usages,
                "total_pages": total_pages,
            }
        )

    if format == "csv":
        usages = app.sparql_client.query(query_builder.build_query())

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
                values=[x.values() for x in usages],
            ),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=find_dataset_usages.csv"},
        )

    return Response(content="Unsupported format", status_code=400)


@router.get("/query-iri")
async def get_query_iri(request: Request, iri: str):
    return await execute_iri_query(request, iri)


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


@router.get("/types")
async def get_model_types(request: Request) -> JSONResponse:
    app = request.app
    query = MODEL_TYPES_QUERY
    if config.sparql_backend == "graphdb":
        query = _inject_explicit_graph(query)

    return JSONResponse(app.sparql_client.query(query))
