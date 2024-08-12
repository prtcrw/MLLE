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
        {
            "datasetName": 'Dataset D',
            "data": 72,
        },
        {
            "datasetName": 'Dataset E',
            "data": 68,
        },
        {
            "datasetName": 'Dataset F',
            "data": 85,
        },
        {
            "datasetName": 'Dataset G',
            "data": 77,
        },
        {
            "datasetName": 'Dataset H',
            "data": 91,
        },
        {
            "datasetName": 'Dataset I',
            "data": 62,
        },
        {
            "datasetName": 'Dataset J',
            "data": 74,
        },
        {
            "datasetName": 'Dataset K',
            "data": 88,
        },
        {
            "datasetName": 'Dataset L',
            "data": 79,
        },
        {
            "datasetName": 'Dataset M',
            "data": 81,
        },
        {
            "datasetName": 'Dataset N',
            "data": 69,
        },
        {
            "datasetName": 'Dataset O',
            "data": 83,
        },
        {
            "datasetName": 'Dataset P',
            "data": 76,
        },
        {
            "datasetName": 'Dataset Q',
            "data": 92,
        },
        {
            "datasetName": 'Dataset R',
            "data": 65,
        },
        {
            "datasetName": 'Dataset S',
            "data": 87,
        },
        {
            "datasetName": 'Dataset T',
            "data": 66,
        },
    ]

    return performances
