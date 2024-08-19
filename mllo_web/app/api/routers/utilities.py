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
