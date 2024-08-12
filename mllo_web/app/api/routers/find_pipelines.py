from fastapi import APIRouter

router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])


@router.get("/")  # Define a GET endpoint for "/pipelines"
async def get_pipelines():
    pipelines = [
        {
            "pipelineName": 'Pipeline A',
            "pipelineType": 'Type 1',
            "pipelineStructure": 'Structure A',
            "pipelineDataInput": 'Input A',
            "pipelineAssociatedModel": 'Model A',
        },
    ]
    return pipelines
