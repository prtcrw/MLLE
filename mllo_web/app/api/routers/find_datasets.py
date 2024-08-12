from fastapi import APIRouter

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])


@router.get("/")  # Define a GET endpoint for "/datasets"
async def get_datasets():
    datasets = [
        {
            "datasetName": "Dataset A",
            "datasetUsedFor": "Training Data",
            "mlInputTimestamp": "2024-08-08T12:00:00Z",
            "datasetSize": "500MB",
            "datasetCharacteristics": "High Quality",
            "datasetSource": "Source A",
            "modelOutput": "Output A",
            "outputUtilization": "Model Training",
        },
    ]
    return datasets
