import csv
from io import StringIO
from typing import Optional, List


def to_order_by_string(sort: Optional[List[str]], mapping: dict) -> str:
    parsed_sort = []
    for key, direction in parse_option_params(sort).items():
        mapped_key = mapping.get(key)
        if mapped_key:
            parsed_sort.append(f"{direction.upper()}(?{mapped_key})")

    if len(parsed_sort) > 0:
        sort_string = " ".join(parsed_sort)
        return f"\nORDER BY {sort_string}"

    return None


def parse_option_params(option: Optional[List[str]]) -> dict:
    """Parses option parameters from a list of strings.

    Args:
        option: A list of strings representing option criteria.

    Returns:
        A dictionary of parsed option parameters, or an error message if the format is invalid.
    """

    option_params = {}

    if option:
        for option_item in option:
            try:
                option_key, option_value = option_item.split(",")
                if option_value == 'true':
                    option_value = True
                elif option_value == 'false':
                    option_value = False

                option_params[option_key] = option_value
            except ValueError:
                raise ValueError(
                    "Invalid option parameter format. Use comma-separated key and value (e.g., name,value).")

    return option_params


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


def dataset_role_filter(training_data: bool = False,
                        test_data: bool = False,
                        validation_data: bool = False,
                        production_data: bool = False,
                        raw_data: bool = False) -> str:
    roles = {
        "ml:TrainingDataSet": training_data,
        "ml:TestDataSet": test_data,
        "ml:ValidationDataSet": validation_data,
        "ml:ProductionMachineLearningDataSet": production_data,
        "ml:RawDataSet": raw_data
    }
    replacement_string = " ".join(role for role, checked in roles.items() if checked)

    return replacement_string.strip()
