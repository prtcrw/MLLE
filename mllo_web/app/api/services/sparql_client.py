import contextlib
import re
from abc import ABC, abstractmethod

import requests

from mllo_web.app.api.config import AppConfig


class QueryBuilder(ABC):

    @abstractmethod
    def build_query(self) -> str:
        raise NotImplementedError


class TotalRecordsQueryBuilder(QueryBuilder):

    def __init__(self, delegate: QueryBuilder):
        self.delegate = delegate

    def build_query(self) -> str:
        query = self.delegate.build_query()
        query = re.sub(r"SELECT", "SELECT (COUNT(*) AS ?total_records) WHERE { SELECT ", query, count=1) + " }"
        return query


class PaginationQueryBuilder(QueryBuilder):

    def __init__(self, delegate: QueryBuilder, page: int, items_per_page: int):
        self.delegate = delegate
        self.page = page
        self.items_per_page = items_per_page

    def build_query(self) -> str:
        query = self.delegate.build_query()

        limit = self.items_per_page
        offset = (self.page - 1) * self.items_per_page

        query = query + f' LIMIT {limit} OFFSET {offset}'

        return query


class SparqlClient(ABC):

    @abstractmethod
    def query(self, statement) -> dict:
        pass


class MobiSparqlClient(SparqlClient):

    def __init__(self, config: AppConfig):
        self.endpoint = config.mobi_endpoint
        if config.mobi_auth_type:
            if config.mobi_auth_type == 'basic':
                self.auth = requests.auth.HTTPBasicAuth(config.mobi_auth_username,
                                                        config.mobi_auth_password)
            else:
                if config.mobi_auth_type:
                    raise AttributeError(f'Unsupported authentication method: {config.mobi_auth_type}')
                else:
                    raise AttributeError(f'No authentication method specified.')

    def query(self, statement: str) -> dict:
        headers = {'Accept': 'application/sparql-results+json'}
    
        # print(f"\n{'='*60}")
        print(f"SPARQL Query:\n{statement}")
        # print(f"{'='*60}\n")
        with contextlib.closing(requests.Session()) as session:
            response = session.get(self.endpoint, params={
                'query': statement,
            }, auth=self.auth, verify=False)
            # print(response)
            res = response.json()
            if 'error' in res:
                errorMessage, errorDetails = res['errorMessage'], res['errorDetails']
                raise ValueError(f'{errorMessage}\n{errorDetails}')
            return self.to_dict(res)

    def to_dict(self, sparql_result):
        results_dict_list = []

        # Extract variable names
        vars_list = sparql_result.get('head', {}).get('vars', [])

        # Extract the bindings
        bindings = sparql_result.get('results', {}).get('bindings', [])

        # Process each binding
        for binding in bindings:
            parsed_result = {}
            for var in vars_list:
                if var in binding:
                    parsed_result[var] = binding[var]['value']
                else:
                    parsed_result[var] = None  # If the key is not present, set value as None
            results_dict_list.append(parsed_result)

        return results_dict_list

class GraphDBSparqlClient(SparqlClient):

    def __init__(self, config: AppConfig):
        self.endpoint = config.graphdb_endpoint
        self.auth = None

        if config.graphdb_auth_type == 'basic':
            self.auth = requests.auth.HTTPBasicAuth(
                config.graphdb_auth_username,
                config.graphdb_auth_password
            )
        elif config.graphdb_auth_type not in ('none', '', None):
            raise AttributeError(f'Unsupported authentication method: {config.graphdb_auth_type}')

    def query(self, statement: str) -> dict:
        headers = {
            'Accept': 'application/sparql-results+json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        # print(f"\n{'='*60}")
        print(f"SPARQL Query:\n{statement}")
        # print(f"{'='*60}\n")

        with contextlib.closing(requests.Session()) as session:
            response = session.post(
                self.endpoint,
                data={'query': statement},
                auth=self.auth,
                headers=headers,
                verify=False
            )

            # print(f"Status: {response.status_code}")
            # print(f"Content-Type: {response.headers.get('Content-Type')}")
            # print(f"Response body: {response.text[:500]}")

            if not response.ok:
                raise ValueError(f"GraphDB Error {response.status_code}: {response.text}")

            if not response.text:
                raise ValueError("GraphDB returned an empty response")

            res = response.json()
            return self.to_dict(res)

    def to_dict(self, sparql_result):
        results_dict_list = []
        vars_list = sparql_result.get('head', {}).get('vars', [])
        bindings = sparql_result.get('results', {}).get('bindings', [])

        for binding in bindings:
            parsed_result = {}
            for var in vars_list:
                if var in binding:
                    parsed_result[var] = binding[var]['value']
                else:
                    parsed_result[var] = None
            results_dict_list.append(parsed_result)

        return results_dict_list
