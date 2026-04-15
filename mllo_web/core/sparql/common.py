from __future__ import annotations

from typing import Optional

from mllo_web.app.api.config import get_config
from mllo_web.app.api.services.sparql_client import QueryBuilder

import re


config = get_config()
EXPLICIT_GRAPH = "FROM <http://www.ontotext.com/explicit>"


def inject_explicit_graph(query: str) -> str:
    if EXPLICIT_GRAPH in query:
        return query
    return re.sub(
        r"(?is)(SELECT\s+DISTINCT\b.*?)(\bWHERE\s*\{)",
        rf"\1\n{EXPLICIT_GRAPH}\n\2",
        query,
        count=1,
    )


def parse_option_params(option: Optional[list[str]]) -> dict:
    option_params = {}
    if option:
        for option_item in option:
            option_key, option_value = option_item.split(",")
            if option_value == "true":
                option_value = True
            elif option_value == "false":
                option_value = False
            option_params[option_key] = option_value
    return option_params


def to_order_by_string(sort: Optional[list[str]], mapping: dict) -> str | None:
    parsed_sort = []
    for key, direction in parse_option_params(sort).items():
        mapped_key = mapping.get(key)
        if mapped_key:
            parsed_sort.append(f"{direction.upper()}(?{mapped_key})")
    if parsed_sort:
        return f"\nORDER BY {' '.join(parsed_sort)}"
    return None


def dataset_role_filter(
    training_data: bool = False,
    test_data: bool = False,
    validation_data: bool = False,
    production_data: bool = False,
    raw_data: bool = False,
) -> str:
    roles = {
        "ml:TrainingDataSet": training_data,
        "ml:TestDataSet": test_data,
        "ml:ValidationDataSet": validation_data,
        "ml:ProductionMachineLearningDataSet": production_data,
        "ml:RawDataSet": raw_data,
    }
    return " ".join(role for role, checked in roles.items() if checked).strip()


__all__ = [
    "QueryBuilder",
    "config",
    "dataset_role_filter",
    "inject_explicit_graph",
    "parse_option_params",
    "to_order_by_string",
]

