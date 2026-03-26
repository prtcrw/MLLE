from __future__ import annotations

import logging

import httpx

from mllo_web.app.api.services.namespace_filter import filter_results

logger = logging.getLogger(__name__)


class GraphDBClient:
    def __init__(
        self,
        base_url: str = "http://localhost:7200",
        default_repo: str = "mllo4",
        repo_allowlist: list[str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_repo = default_repo
        self.repo_allowlist = repo_allowlist

    async def list_repos(self) -> list[str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/rest/repositories")
        if not response.is_success:
            raise ValueError(f"GraphDB repo lookup failed: {response.status_code} {response.text[:500]}")

        payload = response.json()
        repos: list[str] = []
        for item in payload:
            repo_id = item.get("id") or item.get("uri", "").rstrip("/").rsplit("/", 1)[-1]
            if repo_id:
                repos.append(repo_id)
        return repos

    async def validate_repo(self, repo: str | None = None) -> str:
        resolved_repo = repo or self.default_repo
        if self.repo_allowlist is not None and resolved_repo not in self.repo_allowlist:
            raise ValueError(f"Repository '{resolved_repo}' is not allowed")
        repos = await self.list_repos()
        if resolved_repo not in repos:
            raise ValueError(f"Repository '{resolved_repo}' was not found")
        return resolved_repo

    async def query(
        self,
        sparql: str,
        repo: str | None = None,
        use_inference: bool = False,
        show_upper_ontology: bool = False,
    ) -> list[dict]:
        resolved_repo = await self.validate_repo(repo)
        params = None if use_inference else {"infer": "false"}
        headers = {
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/repositories/{resolved_repo}",
                params=params,
                data={"query": sparql},
                headers=headers,
            )
        if not response.is_success:
            raise ValueError(f"GraphDB Error {response.status_code}: {response.text[:1000]}")
        payload = response.json()
        results = self._to_dict(payload)
        return filter_results(results, show_upper_ontology=show_upper_ontology)

    async def get_ontology_schema(self, repo: str | None = None) -> list[dict]:
        from mllo_web.app.api.routers.natural_language_query import ONTOLOGY_SCHEMA_QUERY

        return await self.query(ONTOLOGY_SCHEMA_QUERY, repo=repo)

    async def get_prefixes(self, repo: str | None = None) -> list[dict]:
        from mllo_web.app.api.routers.natural_language_query import PREFIX_QUERY

        return await self.query(PREFIX_QUERY, repo=repo, show_upper_ontology=True)

    async def get_sample_triples(self, repo: str | None = None) -> list[dict]:
        from mllo_web.app.api.routers.natural_language_query import SAMPLE_TRIPLES_QUERY

        return await self.query(SAMPLE_TRIPLES_QUERY, repo=repo, show_upper_ontology=True)

    async def get_named_individuals(self, repo: str | None = None) -> list[dict]:
        from mllo_web.app.api.routers.natural_language_query import NAMED_INDIVIDUALS_QUERY

        return await self.query(NAMED_INDIVIDUALS_QUERY, repo=repo)

    @staticmethod
    def _to_dict(sparql_result: dict) -> list[dict]:
        results_dict_list: list[dict] = []
        vars_list = sparql_result.get("head", {}).get("vars", [])
        bindings = sparql_result.get("results", {}).get("bindings", [])
        for binding in bindings:
            parsed_result = {}
            for var in vars_list:
                if var in binding:
                    parsed_result[var] = binding[var]["value"]
                else:
                    parsed_result[var] = None
            results_dict_list.append(parsed_result)
        return results_dict_list
