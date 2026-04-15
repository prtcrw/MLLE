from __future__ import annotations

import re
from typing import List, Optional

from mllo_web.core.sparql.common import QueryBuilder, config, inject_explicit_graph, to_order_by_string


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
    (STRAFTER(STR(?pipeline_data_output_iri), "#") AS ?pipeline_data_output)
    (STRAFTER(STR(?pipeline_associated_model_iri), "#") AS ?pipeline_associated_model)
WHERE {
    {
        SELECT
            ?pipeline
            ?pipeline_type
            (GROUP_CONCAT(DISTINCT ?pipeline_component_label; separator=";") AS ?pipeline_components)
        WHERE {
            ?pipeline rdf:type ?pipeline_type_iri.
            ?pipeline_type_iri rdfs:label ?pipeline_type .
            #pipeline_type_filter
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
            ?pipeline bfo:BFO_0000117 ?pipeline_component.
            ?pipeline_component rdf:type ?pipeline_component_type.
            ?pipeline_component_type rdfs:subClassOf+ iof-core:PlannedProcess.
            ?pipeline_component_type rdfs:label ?pipeline_component_label
        }
        GROUP BY
            ?pipeline ?pipeline_type
    }
    OPTIONAL { ?pipeline ml:hasDataInput ?pipeline_data_input_iri }
    OPTIONAL { ?pipeline ml:hasDataOutput ?pipeline_data_output_iri }
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

COMPARE_QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/core/Core/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT
    (STRAFTER(STR(?pipeline), "#") AS ?pipeline_name)
    ?pipeline_type
    ?pipeline_components
    (STRAFTER(STR(?pipeline_data_input_iri), "#") AS ?pipeline_data_input)
    (STRAFTER(STR(?pipeline_data_output_iri), "#") AS ?pipeline_data_output)
    (STRAFTER(STR(?pipeline_associated_model_iri), "#") AS ?pipeline_associated_model)
WHERE {
    {
        SELECT ?pipeline ?pipeline_type
            (GROUP_CONCAT(DISTINCT ?pipeline_component_label; separator=";") AS ?pipeline_components)
        WHERE {
            VALUES ?pipeline_name_filter { #pipeline_name_values }
            ?pipeline rdf:type ?pipeline_type_iri .
            FILTER(?pipeline_type_iri != owl:NamedIndividual)
            ?pipeline_type_iri rdfs:label ?pipeline_type .
            FILTER(STRAFTER(STR(?pipeline), "#") = ?pipeline_name_filter)
            ?pipeline bfo:BFO_0000117 ?pipeline_component .
            ?pipeline_component rdf:type ?pipeline_component_type .
            FILTER(?pipeline_component_type != owl:NamedIndividual)
            ?pipeline_component_type rdfs:label ?pipeline_component_label
        }
        GROUP BY ?pipeline ?pipeline_type
    }
    OPTIONAL { ?pipeline ml:hasDataInput ?pipeline_data_input_iri }
    OPTIONAL { ?pipeline ml:hasDataOutput ?pipeline_data_output_iri }
    OPTIONAL {
        {
            ?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        } UNION {
            ?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?pipeline_associated_model_iri
        }
    }
}
ORDER BY ?pipeline_name
"""


def build_compare_pipelines_query(pipeline_ids: list[str]) -> str:
    escaped = " ".join(f'"{item}"' for item in pipeline_ids if item)
    query = COMPARE_QUERY.replace("#pipeline_name_values", escaped)
    if config.sparql_backend == "graphdb":
        query = inject_explicit_graph(query)
    return query


class FindPipelinesQueryBuilder(QueryBuilder):
    SORT_KEY_MAPPING = {
        "Pipeline Name": "pipeline_name",
        "Pipeline Type": "pipeline_type",
        "Pipeline Components": "pipeline_components",
        "Pipeline Data Input": "pipeline_data_input",
        "Pipeline Data Output": "pipeline_data_output",
        "Pipeline Associated Model": "pipeline_associated_model",
    }

    def __init__(
        self,
        search_term: Optional[str] = None,
        toggle_constraint: Optional[bool] = False,
        sort: Optional[List[str]] = None,
        pipeline_types: Optional[List[str]] = None,
    ):
        self.search_term = re.sub(re.compile(r"\s+"), "", search_term) if search_term else None
        self.pipeline_constraint = self.search_term
        self.toggle_constraint = toggle_constraint
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.pipeline_types = pipeline_types

    def build_query(self) -> str:
        query = QUERY
        if self.pipeline_types:
            pipeline_filter = "FILTER(?pipeline_type IN ({}))".format(", ".join(f'"{ptype}"' for ptype in self.pipeline_types))
            query = query.replace("#pipeline_type_filter", pipeline_filter)
        else:
            query = query.replace("#pipeline_type_filter", "")

        if self.toggle_constraint:
            replacement_string = "?pipeline ml:hasDataInput| ml:hasDataOutput ?dataset.\n"
            replacement_string += "?dataset rdf:type/rdfs:subClassOf* <http://purl.obolibrary.org/obo/IAO_0000100>.\n"
            if self.pipeline_constraint:
                replacement_string += f'FILTER(CONTAINS(STRAFTER(STR(?dataset),"#"),"{self.pipeline_constraint}"))\n'
            query = query.replace("#dataset_or_ml_filter", replacement_string)
        else:
            replacement_string = "{?pipeline bfo:BFO_0000117*/(bfo:BFO_0000057 | ml:executes) ?model}\nUNION\n"
            replacement_string += "{?pipeline bfo:BFO_0000063+/(bfo:BFO_0000057 | ml:executes) ?model}\n"
            replacement_string += "?model rdf:type/rdfs:subClassOf* ml:MachineLearningModel.\n"
            if self.pipeline_constraint:
                replacement_string += f'FILTER(CONTAINS(STRAFTER(STR(?model),"#"),"{self.pipeline_constraint}"))\n'
            query = query.replace("#dataset_or_ml_filter", replacement_string)

        if self.sort_string:
            query += self.sort_string
        if config.sparql_backend == "graphdb":
            query = inject_explicit_graph(query)
        return query

