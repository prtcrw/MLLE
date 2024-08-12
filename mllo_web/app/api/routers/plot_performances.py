from fastapi import APIRouter, Query
from typing import List, Optional

router = APIRouter(prefix="/v1/performances", tags=["performances"])

# Example performance data
performances = [
    {"datasetName": 'Dataset A', "accuracy": 65, "precision": 60, "recall": 55},
    {"datasetName": 'Dataset B', "accuracy": 59, "precision": 58, "recall": 61},
    {"datasetName": 'Dataset C', "accuracy": 80, "precision": 77, "recall": 70},
    {"datasetName": 'Dataset D', "accuracy": 72, "precision": 70, "recall": 69},
    {"datasetName": 'Dataset E', "accuracy": 68, "precision": 65, "recall": 62},
    {"datasetName": 'Dataset F', "accuracy": 85, "precision": 80, "recall": 75},
    {"datasetName": 'Dataset G', "accuracy": 77, "precision": 75, "recall": 72},
    {"datasetName": 'Dataset H', "accuracy": 91, "precision": 88, "recall": 85},
    {"datasetName": 'Dataset I', "accuracy": 62, "precision": 60, "recall": 58},
    {"datasetName": 'Dataset J', "accuracy": 74, "precision": 71, "recall": 70},
    # Add more data as needed
]

@router.get("/")
async def get_plot_performances(
    y_axis_metric: str = Query("accuracy", alias="yAxisMetric"),
    performance_cutoff: Optional[int] = Query(None),
    order_by: Optional[str] = Query(None),
    group_by: Optional[str] = Query("datasetName"),
):
    # Filter by performance cutoff if provided
    filtered_performances = performances
    if performance_cutoff is not None:
        filtered_performances = [
            p for p in performances if p[y_axis_metric] >= performance_cutoff
        ]

    # Order by the specified metric if provided
    if order_by:
        reverse_order = order_by.lower() == "descending"
        filtered_performances.sort(key=lambda p: p[y_axis_metric], reverse=reverse_order)

    # Group by (currently no specific logic for grouping, returning the filtered data)
    # You could implement logic here if you want to aggregate or group data
    grouped_performances = filtered_performances

    # Return the filtered and sorted data
    return grouped_performances
