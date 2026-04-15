from __future__ import annotations

try:
    from fastmcp import FastMCP
except ImportError as exc:
    raise RuntimeError("fastmcp is required to run mllo_mcp_server.py") from exc

from mllo_web.core.tools.graph_native import (
    check_class_membership_tool,
    compare_nodes_tool,
    count_by_property_tool,
    count_by_type_tool,
    describe_node_tool,
    filter_by_string_tool,
    find_all_paths_tool,
    find_bridge_nodes_tool,
    find_by_external_id_tool,
    find_by_property_value_tool,
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
from mllo_web.core.tools.mllo import (
    analyze_deployed_models_tool,
    compare_pipelines_tool,
    execute_sparql_tool,
    explore_category_tool,
    find_datasets_tool,
    find_models_tool,
    find_pipelines_tool,
    get_artifact_details_tool,
)

mcp = FastMCP("MLLE")


@mcp.tool()
async def find_datasets(
    search_term: str = "",
    role: str = "",
    date_from: str = "",
    date_to: str = "",
    repo: str | None = None,
) -> dict:
    return await find_datasets_tool(search_term=search_term, role=role, date_from=date_from, date_to=date_to, repo=repo)


@mcp.tool()
async def find_models(
    dataset_name: str = "",
    model_type: str = "",
    repo: str | None = None,
) -> dict:
    return await find_models_tool(dataset_name=dataset_name, model_type=model_type, repo=repo)


@mcp.tool()
async def find_pipelines(
    search_term: str = "",
    pipeline_type: str = "",
    repo: str | None = None,
) -> dict:
    return await find_pipelines_tool(search_term=search_term, pipeline_type=pipeline_type, repo=repo)


@mcp.tool()
async def compare_pipelines(
    pipeline_ids: list[str],
    repo: str | None = None,
) -> dict:
    return await compare_pipelines_tool(pipeline_ids=pipeline_ids, repo=repo)


@mcp.tool()
async def analyze_deployed_models(repo: str | None = None) -> dict:
    return await analyze_deployed_models_tool(repo=repo)


@mcp.tool()
async def get_artifact_details(
    iri: str,
    repo: str | None = None,
    show_upper_ontology: bool = False,
) -> dict:
    return await get_artifact_details_tool(iri=iri, repo=repo, show_upper_ontology=show_upper_ontology)


@mcp.tool()
async def explore_category(
    category_name: str,
    repo: str | None = None,
) -> dict:
    return await explore_category_tool(category_name=category_name, repo=repo)


@mcp.tool()
async def execute_sparql(
    query: str,
    use_inference: bool = False,
    repo: str | None = None,
) -> dict:
    return await execute_sparql_tool(query=query, use_inference=use_inference, repo=repo)


@mcp.tool()
async def filter_by_string(search_term: str, repo: str | None = None) -> dict:
    return await filter_by_string_tool(search_term=search_term, repo=repo)


@mcp.tool()
async def find_by_type(class_iri: str, limit: int = 50, repo: str | None = None) -> dict:
    return await find_by_type_tool(class_iri=class_iri, limit=limit, repo=repo)


@mcp.tool()
async def find_by_property_value(property_iri: str, value: str, repo: str | None = None) -> dict:
    return await find_by_property_value_tool(property_iri=property_iri, value=value, repo=repo)


@mcp.tool()
async def list_all_classes(repo: str | None = None) -> dict:
    return await list_all_classes_tool(repo=repo)


@mcp.tool()
async def list_all_properties(class_iri: str | None = None, repo: str | None = None) -> dict:
    return await list_all_properties_tool(class_iri=class_iri, repo=repo)


@mcp.tool()
async def find_surrounding_nodes(iri: str, depth: int = 1, repo: str | None = None) -> dict:
    return await find_surrounding_nodes_tool(iri=iri, depth=depth, repo=repo)


@mcp.tool()
async def describe_node(iri: str, repo: str | None = None) -> dict:
    return await describe_node_tool(iri=iri, repo=repo)


@mcp.tool()
async def find_node_by_label(label: str, repo: str | None = None) -> dict:
    return await find_node_by_label_tool(label=label, repo=repo)


@mcp.tool()
async def compare_nodes(iri_1: str, iri_2: str, repo: str | None = None) -> dict:
    return await compare_nodes_tool(iri_1=iri_1, iri_2=iri_2, repo=repo)


@mcp.tool()
async def find_common_neighbors(iri_1: str, iri_2: str, repo: str | None = None) -> dict:
    return await find_common_neighbors_tool(iri_1=iri_1, iri_2=iri_2, repo=repo)


@mcp.tool()
async def graph_traversal(start_iri: str, target_class: str, max_hops: int = 10, repo: str | None = None) -> dict:
    return await graph_traversal_tool(start_iri=start_iri, target_class=target_class, max_hops=max_hops, repo=repo)


@mcp.tool()
async def find_shortest_path(iri_1: str, iri_2: str, repo: str | None = None) -> dict:
    return await find_shortest_path_tool(iri_1=iri_1, iri_2=iri_2, repo=repo)


@mcp.tool()
async def find_all_paths(iri_1: str, iri_2: str, max_hops: int = 10, repo: str | None = None) -> dict:
    return await find_all_paths_tool(iri_1=iri_1, iri_2=iri_2, max_hops=max_hops, repo=repo)


@mcp.tool()
async def trace_lineage(iri: str, direction: str = "upstream", max_hops: int = 10, repo: str | None = None) -> dict:
    return await trace_lineage_tool(iri=iri, direction=direction, max_hops=max_hops, repo=repo)


@mcp.tool()
async def find_subgraph(root_iri: str, depth: int = 2, repo: str | None = None) -> dict:
    return await find_subgraph_tool(root_iri=root_iri, depth=depth, repo=repo)


@mcp.tool()
async def get_class_hierarchy(root_class: str | None = None, repo: str | None = None) -> dict:
    return await get_class_hierarchy_tool(root_class=root_class, repo=repo)


@mcp.tool()
async def get_class_schema(class_iri: str, repo: str | None = None) -> dict:
    return await get_class_schema_tool(class_iri=class_iri, repo=repo)


@mcp.tool()
async def find_related_classes(class_iri: str, repo: str | None = None) -> dict:
    return await find_related_classes_tool(class_iri=class_iri, repo=repo)


@mcp.tool()
async def get_namespace_summary(repo: str | None = None) -> dict:
    return await get_namespace_summary_tool(repo=repo)


@mcp.tool()
async def check_class_membership(
    iri: str,
    class_iri: str,
    use_inference: bool = False,
    repo: str | None = None,
) -> dict:
    return await check_class_membership_tool(iri=iri, class_iri=class_iri, use_inference=use_inference, repo=repo)


@mcp.tool()
async def count_by_type(repo: str | None = None) -> dict:
    return await count_by_type_tool(repo=repo)


@mcp.tool()
async def count_by_property(property_iri: str, repo: str | None = None) -> dict:
    return await count_by_property_tool(property_iri=property_iri, repo=repo)


@mcp.tool()
async def get_property_distribution(class_iri: str, property_iri: str, repo: str | None = None) -> dict:
    return await get_property_distribution_tool(class_iri=class_iri, property_iri=property_iri, repo=repo)


@mcp.tool()
async def find_missing_properties(class_iri: str, required_properties: list[str], repo: str | None = None) -> dict:
    return await find_missing_properties_tool(class_iri=class_iri, required_properties=required_properties, repo=repo)


@mcp.tool()
async def find_outliers(class_iri: str, property_iri: str, repo: str | None = None) -> dict:
    return await find_outliers_tool(class_iri=class_iri, property_iri=property_iri, repo=repo)


@mcp.tool()
async def find_external_links(iri: str, repo: str | None = None) -> dict:
    return await find_external_links_tool(iri=iri, repo=repo)


@mcp.tool()
async def find_cross_ontology_nodes(namespace_uri: str, repo: str | None = None) -> dict:
    return await find_cross_ontology_nodes_tool(namespace_uri=namespace_uri, repo=repo)


@mcp.tool()
async def find_bridge_nodes(namespace_1: str, namespace_2: str, repo: str | None = None) -> dict:
    return await find_bridge_nodes_tool(namespace_1=namespace_1, namespace_2=namespace_2, repo=repo)


@mcp.tool()
async def get_annotation_properties(iri: str, repo: str | None = None) -> dict:
    return await get_annotation_properties_tool(iri=iri, repo=repo)


@mcp.tool()
async def find_by_external_id(id_value: str, id_property: str | None = None, repo: str | None = None) -> dict:
    return await find_by_external_id_tool(id_value=id_value, id_property=id_property, repo=repo)


if __name__ == "__main__":
    mcp.run()
