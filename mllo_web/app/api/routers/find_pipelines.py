import math
from typing import Optional, List

from fastapi import APIRouter, Request, Query
from fastapi.responses import Response, JSONResponse, StreamingResponse

from mllo_web.app.api.routers.utilities import generate_csv_response, to_order_by_string
from mllo_web.app.api.services.sparql_client import (
    QueryBuilder,
    TotalRecordsQueryBuilder,
    PaginationQueryBuilder,
)

router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])

QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT DISTINCT 
    (STRAFTER(STR(?pipeline), "#") AS ?pipeline_name)
    ?pipeline_type
    ?pipeline_components
    (STRAFTER(STR(?pipeline_data_input_iri), "#") AS ?pipeline_data_input)
    (STRAFTER(STR(?pipeline_associated_model_iri), "#") AS ?pipeline_associated_model) 
WHERE { 
    ?pipeline rdf:type ?pipeline_type_iri.
    ?pipeline_type_iri rdfs:label ?pipeline_type .
    #pipeline_type_filter
    
    {
        SELECT 
            ?pipeline 
            ?pipeline_type 
            (GROUP_CONCAT(?pipeline_component_label; separator=";") AS ?pipeline_components)
        WHERE {
	        ?pipeline rdf:type ?pipeline_type_iri.
            {
                ?pipeline_type_iri rdfs:subClassOf+ ml:DataProcessingPipeline.
                ?pipeline_type_iri rdfs:label ?pipeline_type
            }
            UNION
            {
                VALUES ?pipeline_type_iri { ml:MachineLearningModelDevelopmentPipeline }
                ?pipeline rdf:type ?pipeline_type_iri.
                ?pipeline_type_iri rdfs:label ?pipeline_type
            }
            #dataset_or_ml_filter                       
            OPTIONAL {
                ?pipeline bfo:BFO_0000117 ?pipeline_component.
                ?pipeline_component rdf:type ?pipeline_component_type.
                ?pipeline_component_type rdfs:subClassOf+ iof-core:PlannedProcess.
                ?pipeline_component_type rdfs:label ?pipeline_component_label
            }
        }
        GROUP BY
            ?pipeline ?pipeline_type
    }
    OPTIONAL {
        ?pipeline ml:hasDataInput ?pipeline_data_input_iri
    }
    OPTIONAL {
        {
            ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }
        UNION
        {
            ?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }
	?pipeline_associated_model_iri rdf:type/rdfs:subClassOf* ml:MachineLearningModel
    }
}
"""


class FindPipelinesQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Pipeline Name": "pipeline_name",
        "Pipeline Type": "pipeline_type",
        "Pipeline Components": "pipeline_components",
        "Pipeline Data Input": "pipeline_data_input",
        "Pipeline Associated Model": "pipeline_associated_model",
    }

    def __init__(
        self,
        search_term: Optional[str] = None,
        toggle_constraint: Optional[bool] = False,
        sort: Optional[List[str]] = None,
        pipeline_types: Optional[List[str]] = None,
    ):

        self.search_term = (
            search_term.strip() if search_term and len(search_term) > 0 else None
        )
        self.pipeline_constraint = self.search_term
        self.toggle_constraint = toggle_constraint
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.pipeline_types = pipeline_types

    def build_query(self) -> str:
        query = QUERY
        # pipeline type filter
        if self.pipeline_types:
            pipeline_filter = "FILTER(?pipeline_type IN ({}))".format(
                ", ".join(f'"{ptype}"' for ptype in self.pipeline_types)
            )
            query = query.replace("#pipeline_type_filter", pipeline_filter)

        if self.toggle_constraint:
            replacement_string_for_dataset_association = (
                "FILTER EXISTS{?pipeline ml:hasDataInput| ml:hasDataOutput ?dataset}\n"
            )
            replacement_string_for_specific_dataset = "?dataset rdf:type/rdfs:subClassOf* <http://purl.obolibrary.org/obo/IAO_0000100>.\n"

            if (
                self.pipeline_constraint is not None
                and len(self.pipeline_constraint) > 0
            ):
                replacement_string_for_specific_dataset += (
                    'FILTER(STRAFTER(STR(?dataset),"#")='
                    + '"'
                    + self.pipeline_constraint
                    + '")\n'
                )

            query = query.replace(
                "#dataset_or_ml_filter",
                replacement_string_for_specific_dataset
                + replacement_string_for_dataset_association,
            )

        else:
            replacement_string_for_model_association = "FILTER EXISTS{{?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model}\nUNION\n{?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?model}}\n"
            replacement_string_for_specific_model = (
                "?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel.\n"
            )

            if (
                self.pipeline_constraint is not None
                and len(self.pipeline_constraint) > 0
            ):
                replacement_string_for_specific_model += (
                    'FILTER(STRAFTER(STR(?model),"#")='
                    + '"'
                    + self.pipeline_constraint
                    + '")\n'
                )

            query = query.replace(
                "#dataset_or_ml_filter",
                replacement_string_for_specific_model
                + replacement_string_for_model_association,
            )

        # Apply sort based on the mapping
        if self.sort_string:
            query += self.sort_string

        return query


@router.get("/")  # Define a GET endpoint for "/pipelines"
async def get_pipelines(
        request: Request,
        search_term: str = Query(default=None, description="Search term"),
        toggle_constraint: bool = Query(description="Model constraint or Data constraint"),
        page: int = Query(default=1, description="Page number"),
        items_per_page: int = Query(
            default=10, description="Number of pipelines to return per page"
        ),
        sort: Optional[List[str]] = Query(
            default=None,
            description="Sort criteria (e.g., [dataset_name,asc,dataset_used_as,desc])",
        ),
        format: str = Query(default="json", description="Output format (json or csv)"),
        pipeline_types: Optional[List[str]] = Query(
            default=None,
            description="Pipeline types filter",
        ),
    ) -> Response:
    app = request.app
    query_builder = FindPipelinesQueryBuilder(
        search_term, toggle_constraint=toggle_constraint, sort=sort, pipeline_types=pipeline_types
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
        pipelines = app.sparql_client.query(
            PaginationQueryBuilder(
                query_builder, page=page, items_per_page=items_per_page
            ).build_query()
        )

        # Process data for JSON response
        for pipeline in pipelines:
            # Split pipeline_components by semicolon, remove leading/trailing whitespaces
            if len(pipeline["pipeline_components"]) > 0:
                pipeline["pipeline_components"] = [
                    component.strip()
                    for component in pipeline["pipeline_components"].split(";")
                ]

        return JSONResponse(
            {
                "data": pipelines,
                "total_pages": total_pages,
            }
        )
    elif format == "csv":
        pipelines = app.sparql_client.query(query_builder.build_query())

        return StreamingResponse(
            generate_csv_response(
                header=[
                    "pipeline_name",
                    "pipeline_type",
                    "pipeline_components",
                    "pipeline_data_input",
                    "pipeline_associated_model",
                ],
                values=[x.values() for x in pipelines],
            ),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=find_pipelines.csv"},
        )
    else:
        return Response(content="Unsupported format", status_code=400)


@router.get("/types")
async def get_pipeline_types(request: Request) -> JSONResponse:
    app = request.app
    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>

    SELECT DISTINCT ?pipeline_type
    WHERE {
        ?pipeline rdf:type ?pipeline_type_iri .
        {
            ?pipeline_type_iri rdfs:subClassOf+ ml:DataProcessingPipeline .
            ?pipeline_type_iri rdfs:label ?pipeline_type .
        }
        UNION
        {
            VALUES ?pipeline_type_iri { ml:MachineLearningModelDevelopmentPipeline }
            ?pipeline_type_iri rdfs:label ?pipeline_type .
        }
    }
    ORDER BY ?pipeline_type

    """

    try:
        result = app.sparql_client.query(query)
        pipeline_types = [row['pipeline_type'] for row in result]
        print(pipeline_types)
        return JSONResponse(content=pipeline_types)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
