import csv
from io import StringIO
from typing import Optional, List


def parse_sort_params(sort: Optional[List[str]]) -> dict:
    """Parses sort parameters from a list of strings.

    Args:
        sort: A list of strings representing sort criteria.

    Returns:
        A dictionary of parsed sort parameters, or an error message if the format is invalid.
    """

    sort_params = {}

    if sort:
        for sort_item in sort:
            try:
                sort_key, sort_direction = sort_item.split(",")
                sort_params[sort_key] = sort_direction.lower()
            except ValueError:
                raise ValueError(
                    "Invalid sort parameter format. Use comma-separated key and direction (e.g., column_name,asc).")

    return sort_params


def to_order_by_string(sort: Optional[List[str]], mapping: dict) -> str | None:
    parsed_sort = []
    for key, direction in parse_sort_params(sort).items():
        mapped_key = mapping.get(key)
        if mapped_key:
            parsed_sort.append(f"{direction.upper()}(?{mapped_key})")

    if len(parsed_sort) > 0:
        sort_string = " ".join(parsed_sort)
        return f"\nORDER BY {sort_string}"

    return None


async def generate_csv_response(header, values):
    """
    Generates a CSV response from the given data.

    Args:
        header: A list of strings representing headers.
        values: A list of lists representing the CSV data.

    Returns:
        A generator yielding the CSV data as a string.
    """

    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(header)
    writer.writerows(values)
    csv_data.seek(0)
    yield csv_data.read()
