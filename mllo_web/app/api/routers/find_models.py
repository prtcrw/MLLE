from fastapi import APIRouter

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("/")  # Define a GET endpoint for "/models"
async def get_models():
    datasets = [
        {
            "modelName": 'Model A',
            "modelType": 'Type 1',
            "modelPerformanceMetric": 'Accuracy',
            "modelPerformanceValue": 95,
            "modelObjective": 'Classification',
            "dataPreprocessing": 'Normalization',
            "mlInputTimestamp": '2024-08-08T12:00:00Z',
            "datasetUsedFor": 'Training Data',
        },
    ]
    return datasets
