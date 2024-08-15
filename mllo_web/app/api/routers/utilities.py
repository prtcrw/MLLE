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
