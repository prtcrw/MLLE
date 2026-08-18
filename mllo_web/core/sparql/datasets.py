from __future__ import annotations

import re
from typing import List, Optional

from mllo_web.core.sparql.common import (
    QueryBuilder,
    config,
    dataset_role_filter,
    inject_explicit_graph,
    parse_option_params,
    to_order_by_string,
)


QUERY = """
PREFIX ml: <https://spec.industrialontologies.org/ontology/construct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bfo: <http://purl.obolibrary.org/obo/>
PREFIX iof-core: <https://spec.industrialontologies.org/ontology/construct/>
SELECT DISTINCT
    #variables
WHERE {
    {
        ?ml_process bfo:BFO_0000057 ?model.
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
            ?ml_process bfo:BFO_0000222/iof-core:hasValueExpressionAtAllTimes/iof-core:hasDateTimeInstantValue ?ml_input_timestamp
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
        self.model_input = re.sub(re.compile(r"\s+"), "", search_term) if search_term else None
        self.type_query = type_query
        self.sort_string = to_order_by_string(sort, self.SORT_KEY_MAPPING)
        self.dataset_role = parse_option_params(dataset_role)
        self.start_date = start_date
        self.end_date = end_date
        self.include_blank_date = include_blank_date
        self.model_types = model_types

    def build_query(self) -> str:
        query = QUERY.replace("#variables", "\n\t".join(self.query_variables))
        if self.dataset_role:
            replacement_string = dataset_role_filter(
                training_data=self.dataset_role.get("training_data", False),
                test_data=self.dataset_role.get("test_data", False),
                validation_data=self.dataset_role.get("validation_data", False),
                production_data=self.dataset_role.get("production_data", False),
                raw_data=False,
            )
            values = f"VALUES ?dataset_type {{{replacement_string}}}" if replacement_string else ""
            query = query.replace("#DATASETTYPE_CONSTRAINT", values)
            query = query.replace("#UNLINKED_DATASETTYPE_CONSTRAINT", values)
        else:
            query = query.replace("#DATASETTYPE_CONSTRAINT", "")
            query = query.replace("#UNLINKED_DATASETTYPE_CONSTRAINT", "")

        if self.model_input:
            if self.type_query:
                query = query.replace(
                    "#OBJECTIVE_TYPE_FILTER",
                    f'FILTER(CONTAINS(STR(?objective_type),"{self.model_input}"))',
                )
                query = query.replace(
                    "#UNLINKED_DATASET_FILTER",
                    'FILTER('
                    f'CONTAINS(LCASE(COALESCE(?dataset_label, "")), LCASE("{self.model_input}")) '
                    f'|| CONTAINS(LCASE(STR(?dataset)), LCASE("{self.model_input}"))'
                    ')',
                )
            else:
                dataset_filter = (
                    'FILTER('
                    f'CONTAINS(LCASE(COALESCE(?dataset_label, "")), LCASE("{self.model_input}")) '
                    f'|| CONTAINS(LCASE(STR(?dataset)), LCASE("{self.model_input}"))'
                    ')'
                )
                query = query.replace("#DATASET_SEARCH_FILTER", dataset_filter)
                query = query.replace("#UNLINKED_DATASET_FILTER", dataset_filter)
        if self.model_types:
            model_types_str = ",".join([f'"{mtype}"' for mtype in self.model_types])
            query = query.replace("#MODEL_TYPE_FILTER", f" FILTER(?model_type IN ({model_types_str}))")
            query = query.replace("#UNLINKED_MODEL_TYPE_FILTER", "")
        else:
            query = query.replace("#MODEL_TYPE_FILTER", "")
            query = query.replace("#UNLINKED_MODEL_TYPE_FILTER", "")

        if self.start_date:
            query += (
                "\nFILTER("
                f'?ml_input_timestamp >= "{self.start_date}"^^xsd:dateTime'
                + (" || !BOUND(?ml_input_timestamp)" if self.include_blank_date else "")
                + ")"
            )
        if self.end_date:
            query += (
                "\nFILTER("
                f'?ml_input_timestamp <= "{self.end_date}"^^xsd:dateTime'
                + (" || !BOUND(?ml_input_timestamp)" if self.include_blank_date else "")
                + ")"
            )
        for marker in ("#DATASET_SEARCH_FILTER", "#OBJECTIVE_TYPE_FILTER"):
            query = query.replace(marker, "")
        if self.sort_string:
            query += self.sort_string
        if config.sparql_backend == "graphdb":
            query = inject_explicit_graph(query)
        return query

