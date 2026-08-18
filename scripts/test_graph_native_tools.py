from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_REPO = "mllo5"
ML_MODEL_1 = "http://example.com/MNIST#MLModel1"
ML_MODEL_2 = "http://example.com/MNIST#MLModel2"
MODEL_EXECUTION_1 = "http://example.com/MNIST#ModelExecution1"
PREPROCESSED_DATASET_1 = "http://example.com/MNIST#PreprocessedDataset1"
PIPELINE_1 = "http://example.com/MNIST#DataPreparationPipeline1"
TEST_DATASET_CLASS = "https://spec.industrialontologies.org/ontology/construct/MachineLearningDataSet"
OWL_SAME_AS = "http://www.w3.org/2002/07/owl#sameAs"
HIDDEN_TYPES = {
    "http://www.w3.org/2002/07/owl#Thing",
    "http://www.w3.org/2000/01/rdf-schema#Resource",
    "http://www.w3.org/2002/07/owl#NamedIndividual",
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _step(name: str) -> None:
    print(f"[test] {name}", flush=True)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test graph-native tools against a GraphDB repo.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GraphDB repository to test against.")
    args = parser.parse_args()

    from mllo_web.app.tools.graph_native_tools import (
        check_class_membership_tool,
        compare_nodes_tool,
        count_by_type_tool,
        count_by_property_tool,
        describe_node_tool,
        filter_by_string_tool,
        find_all_paths_tool,
        find_bridge_nodes_tool,
        find_by_external_id_tool,
        find_by_type_tool,
        find_common_neighbors_tool,
        find_cross_ontology_nodes_tool,
        find_external_links_tool,
        find_missing_properties_tool,
        find_node_by_label_tool,
        find_outliers_tool,
        find_related_classes_tool,
        find_shortest_path_tool,
        find_subgraph_tool,
        find_surrounding_nodes_tool,
        get_annotation_properties_tool,
        get_class_hierarchy_tool,
        get_class_schema_tool,
        get_namespace_summary_tool,
        get_property_distribution_tool,
        graph_traversal_tool,
        list_all_classes_tool,
        list_all_properties_tool,
        trace_lineage_tool,
    )

    repo = args.repo
    report: dict[str, dict] = {}

    _step("filter_by_string")
    result = await filter_by_string_tool("mnist", repo=repo)
    _assert(result["count"] > 0, "filter_by_string returned no results")
    _assert(any("example.com/MNIST#" in row.get("node", "") for row in result["results"]), "filter_by_string missed MNIST demo instances")
    report["filter_by_string"] = {"count": result["count"]}

    _step("find_by_type")
    result = await find_by_type_tool(TEST_DATASET_CLASS, repo=repo)
    _assert(result["count"] > 0, "find_by_type returned no dataset instances")
    _assert(any("PreprocessedDataset" in row.get("individual", "") for row in result["results"]), "find_by_type missed expected dataset instances")
    report["find_by_type"] = {"count": result["count"]}

    _step("list_all_classes")
    result = await list_all_classes_tool(repo=repo)
    classes = {row.get("class") for row in result["results"]}
    _assert("https://spec.industrialontologies.org/ontology/construct/ModelExecution" in classes, "list_all_classes missed ModelExecution")
    _assert("http://www.w3.org/2002/07/owl#Thing" not in classes, "list_all_classes still exposes owl:Thing")
    report["list_all_classes"] = {"count": result["count"]}

    _step("list_all_properties")
    result = await list_all_properties_tool(repo=repo)
    properties = {row.get("property") for row in result["results"]}
    _assert("https://spec.industrialontologies.org/ontology/construct/hasDataInput" in properties, "list_all_properties missed ml:hasDataInput")
    _assert("http://www.w3.org/2000/01/rdf-schema#subClassOf" not in properties, "list_all_properties still exposes rdfs:subClassOf")
    report["list_all_properties"] = {"count": result["count"]}

    _step("find_surrounding_nodes")
    result = await find_surrounding_nodes_tool(ML_MODEL_1, repo=repo)
    _assert(result["count"] > 0, "find_surrounding_nodes returned no neighbors")
    _assert(any("ModelExecution1" in row.get("neighbor", "") or "ModelTraining1" in row.get("neighbor", "") for row in result["results"]), "find_surrounding_nodes missed expected lifecycle neighbors")
    _assert(not any(row.get("neighborType") in HIDDEN_TYPES for row in result["results"]), "find_surrounding_nodes still prefers hidden neighbor types")
    report["find_surrounding_nodes"] = {"count": result["count"]}

    _step("describe_node")
    result = await describe_node_tool(ML_MODEL_1, repo=repo)
    _assert("http://www.w3.org/1999/02/22-rdf-syntax-ns#type" in result["results"], "describe_node missed rdf:type")
    type_values = result["results"]["http://www.w3.org/1999/02/22-rdf-syntax-ns#type"]
    _assert(any((item.get("object") or "").startswith("https://spec.industrialontologies.org/ontology/construct/") for item in type_values), "describe_node missed MLLO model type")
    _assert(not any((item.get("object") or "") in HIDDEN_TYPES for item in type_values), "describe_node still exposes hidden rdf:type values")
    report["describe_node"] = {"predicates": len(result["results"])}

    _step("find_node_by_label")
    result = await find_node_by_label_tool("model execution", repo=repo)
    _assert(result["count"] > 0, "find_node_by_label returned no matches")
    _assert(result["results"][0]["node"] == "https://spec.industrialontologies.org/ontology/construct/ModelExecution", "find_node_by_label did not resolve ModelExecution")
    report["find_node_by_label"] = {"count": result["count"]}

    _step("find_common_neighbors")
    result = await find_common_neighbors_tool(ML_MODEL_1, ML_MODEL_2, repo=repo)
    _assert(result["count"] > 0, "find_common_neighbors returned no overlap")
    report["find_common_neighbors"] = {"count": result["count"]}

    _step("compare_nodes")
    result = await compare_nodes_tool(ML_MODEL_1, ML_MODEL_2, repo=repo)
    _assert("shared_properties" in result["results"], "compare_nodes missing shared_properties")
    report["compare_nodes"] = {"shared_properties": len(result["results"]["shared_properties"])}

    _step("graph_traversal")
    result = await graph_traversal_tool(ML_MODEL_1, "https://spec.industrialontologies.org/ontology/construct/ModelExecution", max_hops=2, repo=repo)
    _assert(result["count"] > 0, "graph_traversal returned no reachable model executions")
    report["graph_traversal"] = {"count": result["count"]}

    _step("find_shortest_path")
    result = await find_shortest_path_tool(ML_MODEL_1, MODEL_EXECUTION_1, repo=repo)
    _assert(result.get("count", 0) > 0 or result.get("hops") is not None, "find_shortest_path returned no path")
    report["find_shortest_path"] = {"count": result["count"], "hops": result.get("hops")}

    _step("find_all_paths")
    result = await find_all_paths_tool(ML_MODEL_1, MODEL_EXECUTION_1, repo=repo)
    _assert(result["count"] > 0, "find_all_paths returned no paths")
    report["find_all_paths"] = {"count": result["count"]}

    _step("trace_lineage")
    result = await trace_lineage_tool(PREPROCESSED_DATASET_1, repo=repo)
    _assert(result["count"] > 0, "trace_lineage returned no upstream lineage")
    report["trace_lineage"] = {"count": result["count"]}

    _step("find_subgraph")
    result = await find_subgraph_tool(ML_MODEL_1, depth=1, repo=repo)
    _assert(len(result["results"]["nodes"]) > 1, "find_subgraph returned too few nodes")
    _assert(len(result["results"]["edges"]) > 0, "find_subgraph returned no edges")
    report["find_subgraph"] = {"nodes": len(result["results"]["nodes"]), "edges": len(result["results"]["edges"])}

    _step("get_class_hierarchy")
    result = await get_class_hierarchy_tool("https://spec.industrialontologies.org/ontology/construct/MachineLearningModel", repo=repo)
    _assert(result["count"] > 0, "get_class_hierarchy returned no hierarchy rows")
    report["get_class_hierarchy"] = {"count": result["count"]}

    _step("get_class_schema")
    result = await get_class_schema_tool("https://spec.industrialontologies.org/ontology/construct/MachineLearningModel", repo=repo)
    _assert(result["results"]["instance_usage"], "get_class_schema instance_usage is empty")
    report["get_class_schema"] = {
        "ontology_defined": len(result["results"]["ontology_defined"]),
        "instance_usage": len(result["results"]["instance_usage"]),
    }

    _step("find_related_classes")
    result = await find_related_classes_tool("https://spec.industrialontologies.org/ontology/construct/MachineLearningModel", repo=repo)
    _assert(result["count"] > 0, "find_related_classes returned no related classes")
    report["find_related_classes"] = {"count": result["count"]}

    _step("check_class_membership")
    result = await check_class_membership_tool(ML_MODEL_1, "https://spec.industrialontologies.org/ontology/construct/MachineLearningModel", repo=repo)
    _assert(result.get("boolean") is True, "check_class_membership failed for MLModel1 -> MachineLearningModel")
    report["check_class_membership"] = {"boolean": result["boolean"]}

    _step("count_by_type")
    result = await count_by_type_tool(repo=repo)
    _assert(any(row.get("class") == "https://spec.industrialontologies.org/ontology/construct/ModelExecution" for row in result["results"]), "count_by_type missed ModelExecution")
    report["count_by_type"] = {"count": result["count"]}

    _step("count_by_property")
    result = await count_by_property_tool("https://spec.industrialontologies.org/ontology/construct/hasDataInput", repo=repo)
    _assert(result["count"] > 0, "count_by_property returned no values for ml:hasDataInput")
    report["count_by_property"] = {"count": result["count"]}

    _step("get_property_distribution")
    result = await get_property_distribution_tool("https://spec.industrialontologies.org/ontology/construct/MachineLearningModel", "https://spec.industrialontologies.org/ontology/construct/isExecutedIn", repo=repo)
    _assert(result["count"] > 0, "get_property_distribution returned no distribution")
    report["get_property_distribution"] = {"count": result["count"]}

    _step("find_missing_properties")
    result = await find_missing_properties_tool("https://spec.industrialontologies.org/ontology/construct/MachineLearningModel", ["http://example.com/nonexistentProperty"], repo=repo)
    _assert(result["count"] > 0, "find_missing_properties returned no instances")
    report["find_missing_properties"] = {"count": result["count"]}

    _step("find_outliers")
    result = await find_outliers_tool("https://spec.industrialontologies.org/ontology/construct/MachineLearningModel", "http://example.com/nonexistentNumericProperty", repo=repo)
    _assert("outliers" in result["results"], "find_outliers did not return outlier structure")
    report["find_outliers"] = {"outliers": len(result["results"]["outliers"])}

    _step("find_external_links")
    result = await find_external_links_tool(ML_MODEL_1, repo=repo)
    _assert("results" in result and isinstance(result["results"], list), "find_external_links did not return a results list")
    report["find_external_links"] = {"count": result["count"]}

    _step("find_cross_ontology_nodes")
    result = await find_cross_ontology_nodes_tool("http://example.com/MNIST#", repo=repo)
    _assert(result["count"] > 0, "find_cross_ontology_nodes returned no cross-ontology nodes")
    report["find_cross_ontology_nodes"] = {"count": result["count"]}

    _step("find_bridge_nodes")
    result = await find_bridge_nodes_tool("https://spec.industrialontologies.org/ontology/construct/", "http://example.com/MNIST#", repo=repo)
    report["find_bridge_nodes"] = {"count": result["count"]}

    _step("get_annotation_properties")
    result = await get_annotation_properties_tool("https://spec.industrialontologies.org/ontology/construct/ModelExecution", repo=repo)
    _assert(result["count"] > 0, "get_annotation_properties returned no annotations")
    report["get_annotation_properties"] = {"count": result["count"]}

    _step("find_by_external_id")
    result = await find_by_external_id_tool(ML_MODEL_1, id_property=OWL_SAME_AS, repo=repo)
    _assert("results" in result and isinstance(result["results"], list), "find_by_external_id did not return a results list")
    report["find_by_external_id"] = {"count": result["count"]}

    _step("get_namespace_summary")
    result = await get_namespace_summary_tool(repo=repo)
    namespaces = {row.get("namespace") for row in result["results"]}
    _assert("http://example.com/MNIST#" in namespaces, "get_namespace_summary missed MNIST namespace")
    _assert("https://spec.industrialontologies.org/ontology/construct/" in namespaces, "get_namespace_summary missed MLLO namespace")
    report["get_namespace_summary"] = {"count": result["count"]}

    print(json.dumps({"ok": True, "repo": repo, "tests": report}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except AssertionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
