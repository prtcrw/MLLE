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
        query = re.sub(r"SELECT", "SELECT (COUNT(*) AS ?total_records) WHERE { SELECT", query, count=1) + " }"
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
        self.endpoint = config.sparql_client_endpoint
        if config.sparql_client_auth_type:
            if config.sparql_client_auth_type == 'basic':
                self.auth = requests.auth.HTTPBasicAuth(config.sparql_client_auth_username,
                                                        config.sparql_client_auth_password)
            else:
                if config.sparql_client_auth_type:
                    raise AttributeError(f'Unsupported authentication method: {config.sparql_client_auth_type}')
                else:
                    raise AttributeError(f'No authentication method specified.')

    def query(self, statement: str) -> dict:
        with contextlib.closing(requests.Session()) as session:
            response = session.get(self.endpoint, params={
                'query': statement,
            }, auth=self.auth, verify=False)
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
