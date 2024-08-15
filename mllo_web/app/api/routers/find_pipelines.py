import math
from fastapi import APIRouter, Request, Query

router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])

QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
SELECT
    DISTINCT (STRAFTER(STR(?pipeline), "#") AS ?pipeline_name)
    ?pipeline_type ?pipeline_components
    (STRAFTER(STR(?pipeline_data_input_iri), "#") AS ?pipeline_data_input)
    (STRAFTER(STR(?pipeline_associated_model_iri), "#") AS ?pipeline_associated_model)
WHERE {
    {
        SELECT
            ?pipeline
            ?pipeline_type
            (GROUP_CONCAT(?pipeline_component_label;separator=" ; ") AS ?pipeline_components)
        WHERE {
            ?pipeline rdf:type ?pipeline_type_iri.
            {?pipeline_type_iri rdfs:subClassOf+ ml:DataProcessingPipeline.
            ?pipeline_type_iri rdfs:label ?pipeline_type
        } 
        UNION 
        { 
            VALUES ?pipeline_type_iri { ml:MachineLearningModelDevelopmentPipeline }
            ?pipeline rdf:type ?pipeline_type_iri.
            ?pipeline_type_iri rdfs:label ?pipeline_type
        }
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
    }
}
"""


@router.get("/")  # Define a GET endpoint for "/pipelines"
async def get_pipelines(request: Request,
                        page: int = Query(default=1, description="Page number"),
                        items_per_page: int = Query(default=10, description="Number of pipelines to return per page")):
    app = request.app
    pipelines = app.sparql_client.query(QUERY)

    # Calculate total pages based on results and page size
    total_pages = math.ceil(len(pipelines) / items_per_page)

    # Slice data based on page and results per page
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    displayed_datasets = pipelines[start_index:end_index]

    return {
        "data": displayed_datasets,
        "total_pages": total_pages,
    }
