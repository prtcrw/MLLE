from __future__ import annotations

from mllo_web.app.api.routers.find_datasets import FindDatasetsQueryBuilder
from mllo_web.app.api.routers.find_models import DeployedModelsQueryBuilder, FindModelsQueryBuilder
from mllo_web.app.api.routers.find_pipelines import FindPipelinesQueryBuilder
from mllo_web.app.api.routers.natural_language_query import (
    _build_compare_pipelines_query,
    _build_explore_category_query,
)
from mllo_web.app.api.routers.query_iri import IriQueryBuilder
from mllo_web.app.tools.common import run_query


async def find_datasets_tool(
    search_term: str = "",
    role: str = "",
    date_from: str = "",
    date_to: str = "",
    repo: str | None = None,
) -> dict:
    dataset_role = [f"{role}_data,true"] if role in {"training", "test", "validation", "production", "raw"} else None
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
        start_date=date_from or None,
        end_date=date_to or None,
    )
    return await run_query("find_datasets", query_builder.build_query(), repo=repo)


async def find_models_tool(
    dataset_name: str = "",
    model_type: str = "",
    repo: str | None = None,
) -> dict:
    query_builder = FindModelsQueryBuilder(
        search_term=dataset_name,
        model_types=[model_type] if model_type else None,
    )
    return await run_query("find_models", query_builder.build_query(), repo=repo)


async def find_pipelines_tool(
    search_term: str = "",
    pipeline_type: str = "",
    repo: str | None = None,
) -> dict:
    query_builder = FindPipelinesQueryBuilder(
        search_term=search_term,
        pipeline_types=[pipeline_type] if pipeline_type else None,
    )
    return await run_query("find_pipelines", query_builder.build_query(), repo=repo)


async def compare_pipelines_tool(
    pipeline_ids: list[str],
    repo: str | None = None,
) -> dict:
    return await run_query("compare_pipelines", _build_compare_pipelines_query(pipeline_ids), repo=repo)


async def analyze_deployed_models_tool(repo: str | None = None) -> dict:
    query_builder = DeployedModelsQueryBuilder(search_term="", sort=None)
    return await run_query("analyze_deployed_models", query_builder.build_query(), repo=repo)


async def get_artifact_details_tool(
    iri: str,
    repo: str | None = None,
    show_upper_ontology: bool = False,
) -> dict:
    return await run_query(
        "get_artifact_details",
        IriQueryBuilder(iri).build_query(),
        repo=repo,
        show_upper_ontology=show_upper_ontology,
    )


async def explore_category_tool(
    category_name: str,
    repo: str | None = None,
) -> dict:
    return await run_query(
        "explore_category",
        _build_explore_category_query(category_name),
        repo=repo,
        use_inference=True,
    )


async def execute_sparql_tool(
    query: str,
    use_inference: bool = False,
    repo: str | None = None,
) -> dict:
    return await run_query("execute_sparql", query, repo=repo, use_inference=use_inference)
