from __future__ import annotations

import os
from typing import Any

from mllo_web.app.api.services.settings_model import load_settings


def settings():
    return load_settings()


def graphdb_client():
    from mllo_web.app.api.services.graphdb_client import GraphDBClient

    resolved_settings = settings()
    allowlist_raw = os.getenv("GRAPHDB_REPO_ALLOWLIST", "").strip()
    env_allowlist = [item.strip() for item in allowlist_raw.split(",") if item.strip()] or None
    return GraphDBClient(
        base_url=os.getenv("GRAPHDB_URL", resolved_settings.graphdb_url).rstrip("/"),
        default_repo=os.getenv("GRAPHDB_DEFAULT_REPO", resolved_settings.graphdb_default_repo),
        repo_allowlist=resolved_settings.graphdb_repo_allowlist or env_allowlist,
    )


def escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def is_iri(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def count_payload(results: Any) -> int:
    if isinstance(results, list):
        return len(results)
    if isinstance(results, dict):
        if "nodes" in results and isinstance(results["nodes"], list):
            return len(results["nodes"])
        return len(results)
    return 0


def response(tool: str, results: Any, repo_used: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "tool": tool,
        "results": results,
        "count": count_payload(results),
        "repo_used": repo_used,
    }
    payload.update(extra)
    return payload


async def resolve_repo(repo: str | None = None):
    client = graphdb_client()
    resolved_repo = await client.validate_repo(repo or client.default_repo)
    return client, resolved_repo


async def run_query(
    tool: str,
    sparql: str,
    repo: str | None = None,
    use_inference: bool = False,
    show_upper_ontology: bool = False,
) -> dict[str, Any]:
    client, resolved_repo = await resolve_repo(repo)
    results = await client.query(
        sparql,
        repo=resolved_repo,
        use_inference=use_inference,
        show_upper_ontology=show_upper_ontology,
    )
    return response(tool, results, resolved_repo, inference_used=use_inference)


async def run_raw_query(
    sparql: str,
    repo: str | None = None,
    use_inference: bool = False,
    show_upper_ontology: bool = False,
) -> tuple[list[dict], str]:
    client, resolved_repo = await resolve_repo(repo)
    results = await client.query(
        sparql,
        repo=resolved_repo,
        use_inference=use_inference,
        show_upper_ontology=show_upper_ontology,
    )
    return results, resolved_repo


async def run_ask(
    tool: str,
    sparql: str,
    repo: str | None = None,
    use_inference: bool = False,
) -> dict[str, Any]:
    import httpx

    client, resolved_repo = await resolve_repo(repo)
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    params = None if use_inference else {"infer": "false"}
    async with httpx.AsyncClient(timeout=120.0) as http_client:
        response_obj = await http_client.post(
            f"{client.base_url}/repositories/{resolved_repo}",
            params=params,
            data={"query": sparql},
            headers=headers,
        )
    if not response_obj.is_success:
        raise ValueError(f"GraphDB Error {response_obj.status_code}: {response_obj.text[:1000]}")
    payload = response_obj.json()
    result = bool(payload.get("boolean"))
    return response(tool, [{"result": result}], resolved_repo, inference_used=use_inference, boolean=result)

