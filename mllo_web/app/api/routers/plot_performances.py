from fastapi import APIRouter

router = APIRouter(prefix="/v1/performances", tags=["performances"])


@router.get("/")  # Define a GET endpoint for "/performances"
async def get_plot_performances():
    performances = [
        {
            "datasetName": 'Dataset A',
            "data": 65,
        },
        {
            "datasetName": 'Dataset B',
            "data": 59,
        },
        {
            "datasetName": 'Dataset C',
            "data": 80,
        },
    ]
    return performances
