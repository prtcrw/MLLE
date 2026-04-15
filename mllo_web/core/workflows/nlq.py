from __future__ import annotations

from fastapi import HTTPException

from mllo_web.core.domain.nlq import NLQExecutionPayload, NLQQueryState, NLQRequest, NLQResponse
from mllo_web.core.llm import LLMGateway, QueryIntent, classify_intent
from mllo_web.core.sparql import (
    DeployedModelsQueryBuilder,
    FindDatasetsQueryBuilder,
    FindModelsQueryBuilder,
    FindPipelinesQueryBuilder,
    IriQueryBuilder,
    build_compare_pipelines_query,
    build_explore_category_query,
)
from mllo_web.core.workflows.answering import generate_answer
from mllo_web.core.workflows.generation import (
    REPAIR_MESSAGE,
    SYSTEM_MESSAGE,
    contains_cannot_answer,
    extract_sparql,
    generate_sparql,
    inject_prefixes,
)
from mllo_web.core.workflows.lineage import lineage_query_spec
from mllo_web.core.workflows.lineage import execute_lineage_orchestration
from mllo_web.core.workflows.performance import execute_performance_orchestration, performance_query_spec
from mllo_web.core.workflows.shared import (
    active_provider_config,
    dataset_role_params_to_query_args,
    normalize_list,
    pipeline_names_from_params,
)
from mllo_web.app.api.services.graphdb_client import GraphDBClient
from mllo_web.app.api.services.interaction_logging import (
    finalize_nlq_trace,
    reset_nlq_trace,
    start_nlq_trace,
    update_nlq_trace,
)
from mllo_web.app.api.services.settings_model import load_settings


async def _execute_structured_tool(
    intent: QueryIntent,
    repo: str,
    use_inference: bool,
    graphdb_client: GraphDBClient,
) -> tuple[str, list[dict]]:
    params = intent.params or {}
    if intent.tool == "find_datasets":
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
            search_term=params.get("search_term") or params.get("dataset_name") or "",
            dataset_role=dataset_role_params_to_query_args(params.get("dataset_roles")),
            type_query=bool(params.get("type_query", False)),
            model_types=normalize_list(params.get("model_types")),
            sort=None,
        )
        sparql = query_builder.build_query()
    elif intent.tool == "find_models":
        query_builder = FindModelsQueryBuilder(
            search_term=params.get("search_term") or params.get("dataset_name") or "",
            model_types=normalize_list(params.get("model_types")),
            deployment_status=normalize_list(params.get("deployment_status")),
            sort=None,
        )
        sparql = query_builder.build_query()
    elif intent.tool == "find_pipelines":
        query_builder = FindPipelinesQueryBuilder(
            search_term=params.get("search_term") or params.get("pipeline_name") or "",
            toggle_constraint=bool(params.get("toggle_constraint", False)),
            sort=None,
            pipeline_types=normalize_list(params.get("pipeline_types")),
        )
        sparql = query_builder.build_query()
    elif intent.tool == "analyze_deployed_models":
        sparql = DeployedModelsQueryBuilder(search_term=params.get("search_term") or "", sort=None).build_query()
    elif intent.tool == "compare_pipelines":
        sparql = build_compare_pipelines_query(pipeline_names_from_params(params))
    elif intent.tool == "get_artifact_details":
        sparql = IriQueryBuilder(params.get("iri") or "").build_query()
    elif intent.tool == "explore_category":
        sparql = build_explore_category_query(params.get("category_name") or params.get("category") or params.get("search_term") or "")
    else:
        raise ValueError(f"Unsupported structured tool: {intent.tool}")
    results = await graphdb_client.query(sparql, repo=repo, use_inference=use_inference)
    return sparql, results


async def _execute_with_state(
    *,
    question: str,
    intent: QueryIntent,
    resolved_repo: str,
    use_inference: bool,
    graphdb_client: GraphDBClient,
    gateway: LLMGateway,
) -> NLQExecutionPayload:
    state = NLQQueryState(question=question, repo=resolved_repo)
    state.set_artifact("intent", intent.model_dump())

    if lineage_query_spec(question):
        return await execute_lineage_orchestration(
            question=question,
            resolved_repo=resolved_repo,
            state=state,
            graphdb_client=graphdb_client,
            payload_type=NLQExecutionPayload,
        )

    if performance_query_spec(question):
        return await execute_performance_orchestration(
            question=question,
            resolved_repo=resolved_repo,
            state=state,
            graphdb_client=graphdb_client,
            payload_type=NLQExecutionPayload,
        )

    if intent.tool in {
        "find_datasets",
        "find_models",
        "find_pipelines",
        "analyze_deployed_models",
        "compare_pipelines",
        "get_artifact_details",
        "explore_category",
    }:
        sparql, results = await _execute_structured_tool(intent, resolved_repo, use_inference, graphdb_client)
        state.add_step(tool=intent.tool, params=intent.params, sparql=sparql, results=results, inference_used=use_inference, reasoning=intent.reasoning)
        return NLQExecutionPayload(sparql=sparql, results=results, inference_used=use_inference, state=state)

    settings = load_settings()
    sparql, ctx = await generate_sparql(intent.params.get("question") or question, resolved_repo, settings, graphdb_client, gateway)
    try:
        results = await graphdb_client.query(sparql, repo=resolved_repo, use_inference=use_inference)
    except Exception as exc:
        repair_prompt = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "assistant", "content": sparql},
            {"role": "user", "content": f"{REPAIR_MESSAGE}\n\nExecution error:\n{exc}"},
        ]
        repaired = await gateway.chat_completion(repair_prompt, active_provider_config(settings), purpose="sparql_repair_execution")
        if contains_cannot_answer(repaired):
            raise HTTPException(status_code=422, detail="The question cannot be answered using the available ontology.")
        sparql = inject_prefixes(extract_sparql(repaired), ctx)
        results = await graphdb_client.query(sparql, repo=resolved_repo, use_inference=use_inference)
    state.add_step(tool="custom_sparql", params=intent.params, sparql=sparql, results=results, inference_used=use_inference, reasoning=intent.reasoning)
    return NLQExecutionPayload(sparql=sparql, results=results, inference_used=use_inference, state=state)


async def execute_nlq(
    question: str,
    repo: str | None = None,
    answer_mode: str | None = None,
) -> NLQResponse:
    settings = load_settings()
    trace_token = start_nlq_trace(
        enabled=settings.enable_nlq_logging,
        metadata={
            "question": question,
            "repo_requested": repo,
            "answer_mode_requested": answer_mode,
            "active_llm_provider": settings.active_llm_provider,
        },
    )
    resolved_answer_mode = answer_mode or settings.answer_mode
    graphdb_client = GraphDBClient(
        base_url=settings.graphdb_url,
        default_repo=settings.graphdb_default_repo,
        repo_allowlist=settings.graphdb_repo_allowlist,
    )
    gateway = LLMGateway()
    try:
        resolved_repo = await graphdb_client.validate_repo(repo or settings.graphdb_default_repo)
        intent = await classify_intent(question, gateway, active_provider_config(settings))
        use_inference = False if resolved_answer_mode == "exact" else True if resolved_answer_mode == "conceptual" else intent.use_inference
        execution = await _execute_with_state(
            question=question,
            intent=intent,
            resolved_repo=resolved_repo,
            use_inference=use_inference,
            graphdb_client=graphdb_client,
            gateway=gateway,
        )
        answer = await generate_answer(question, execution.results, settings, gateway, state=execution.state)
        response = NLQResponse(
            question=question,
            intent=intent,
            sparql=execution.sparql,
            results=execution.results,
            answer=answer,
            repo_used=resolved_repo,
            inference_used=execution.inference_used,
        )
        update_nlq_trace(
            resolved_repo=resolved_repo,
            resolved_answer_mode=resolved_answer_mode,
            intent=intent.model_dump(),
        )
        finalize_nlq_trace(
            success=True,
            payload={
                "response": response.model_dump(mode="json"),
                "plan": [step.model_dump(mode="json") for step in execution.state.plan],
                "steps": [step.model_dump(mode="json") for step in execution.state.steps],
                "artifacts": execution.state.artifacts,
            },
        )
        return response
    except Exception as exc:
        finalize_nlq_trace(success=False, error=str(exc))
        raise
    finally:
        reset_nlq_trace(trace_token)


async def nlq_query(body: NLQRequest) -> NLQResponse:
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")
    return await execute_nlq(body.question.strip(), repo=body.repo, answer_mode=body.answer_mode)
