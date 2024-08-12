import math
from fastapi import APIRouter, Query

router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])

pipelines = [
    {
        "pipelineName": 'Pipeline A',
        "pipelineType": 'Type 1',
        "pipelineStructure": 'Structure A',
        "pipelineDataInput": 'Input A',
        "pipelineAssociatedModel": 'Model A',
    },
    {
        "pipelineName": 'Pipeline B',
        "pipelineType": 'Type 2',
        "pipelineStructure": 'Structure B',
        "pipelineDataInput": 'Input B',
        "pipelineAssociatedModel": 'Model B',
    },
    {
        "pipelineName": 'Pipeline C',
        "pipelineType": 'Type 3',
        "pipelineStructure": 'Structure C',
        "pipelineDataInput": 'Input C',
        "pipelineAssociatedModel": 'Model C',
    },
    {
        "pipelineName": 'Pipeline D',
        "pipelineType": 'Type 1',
        "pipelineStructure": 'Structure D',
        "pipelineDataInput": 'Input D',
        "pipelineAssociatedModel": 'Model D',
    },
    {
        "pipelineName": 'Pipeline E',
        "pipelineType": 'Type 2',
        "pipelineStructure": 'Structure E',
        "pipelineDataInput": 'Input E',
        "pipelineAssociatedModel": 'Model E',
    },
    {
        "pipelineName": 'Pipeline F',
        "pipelineType": 'Type 3',
        "pipelineStructure": 'Structure F',
        "pipelineDataInput": 'Input F',
        "pipelineAssociatedModel": 'Model F',
    },
    {
        "pipelineName": 'Pipeline G',
        "pipelineType": 'Type 1',
        "pipelineStructure": 'Structure G',
        "pipelineDataInput": 'Input G',
        "pipelineAssociatedModel": 'Model G',
    },
    {
        "pipelineName": 'Pipeline H',
        "pipelineType": 'Type 2',
        "pipelineStructure": 'Structure H',
        "pipelineDataInput": 'Input H',
        "pipelineAssociatedModel": 'Model H',
    },
    {
        "pipelineName": 'Pipeline I',
        "pipelineType": 'Type 3',
        "pipelineStructure": 'Structure I',
        "pipelineDataInput": 'Input I',
        "pipelineAssociatedModel": 'Model I',
    },
    {
        "pipelineName": 'Pipeline J',
        "pipelineType": 'Type 1',
        "pipelineStructure": 'Structure J',
        "pipelineDataInput": 'Input J',
        "pipelineAssociatedModel": 'Model J',
    },
    {
        "pipelineName": 'Pipeline K',
        "pipelineType": 'Type 2',
        "pipelineStructure": 'Structure K',
        "pipelineDataInput": 'Input K',
        "pipelineAssociatedModel": 'Model K',
    },
    {
        "pipelineName": 'Pipeline L',
        "pipelineType": 'Type 3',
        "pipelineStructure": 'Structure L',
        "pipelineDataInput": 'Input L',
        "pipelineAssociatedModel": 'Model L',
    },
    {
        "pipelineName": 'Pipeline M',
        "pipelineType": 'Type 1',
        "pipelineStructure": 'Structure M',
        "pipelineDataInput": 'Input M',
        "pipelineAssociatedModel": 'Model M',
    },
    {
        "pipelineName": 'Pipeline N',
        "pipelineType": 'Type 2',
        "pipelineStructure": 'Structure N',
        "pipelineDataInput": 'Input N',
        "pipelineAssociatedModel": 'Model N',
    },
    {
        "pipelineName": 'Pipeline O',
        "pipelineType": 'Type 3',
        "pipelineStructure": 'Structure O',
        "pipelineDataInput": 'Input O',
        "pipelineAssociatedModel": 'Model O',
    },
    {
        "pipelineName": 'Pipeline P',
        "pipelineType": 'Type 1',
        "pipelineStructure": 'Structure P',
        "pipelineDataInput": 'Input P',
        "pipelineAssociatedModel": 'Model P',
    },
    {
        "pipelineName": 'Pipeline Q',
        "pipelineType": 'Type 2',
        "pipelineStructure": 'Structure Q',
        "pipelineDataInput": 'Input Q',
        "pipelineAssociatedModel": 'Model Q',
    },
    {
        "pipelineName": 'Pipeline R',
        "pipelineType": 'Type 3',
        "pipelineStructure": 'Structure R',
        "pipelineDataInput": 'Input R',
        "pipelineAssociatedModel": 'Model R',
    },
    {
        "pipelineName": 'Pipeline S',
        "pipelineType": 'Type 1',
        "pipelineStructure": 'Structure S',
        "pipelineDataInput": 'Input S',
        "pipelineAssociatedModel": 'Model S',
    },
    {
        "pipelineName": 'Pipeline T',
        "pipelineType": 'Type 2',
        "pipelineStructure": 'Structure T',
        "pipelineDataInput": 'Input T',
        "pipelineAssociatedModel": 'Model T',
    },
]


@router.get("/")  # Define a GET endpoint for "/pipelines"
async def get_pipelines(page: int = Query(default=1, description="Page number"),
                        items_per_page: int = Query(default=10, description="Number of pipelines to return per page")):
    # Calculate total pages based on results and page size
    total_pages = math.ceil(len(pipelines) / items_per_page)

    # Slice data based on page and results per page
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    displayed_datasets = pipelines[start_index:end_index]

    return {
        "data": displayed_datasets,
        "total_pages": total_pages,
    }
