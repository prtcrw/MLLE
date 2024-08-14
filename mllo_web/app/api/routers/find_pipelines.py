import math
from fastapi import APIRouter, Query, HTTPException
from mllo_web.app.api.routers import sparql_query as sq

router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])

SPARQL_ENDPOINT = "https://localhost:8443/mobirest/sparql"
 
def fetch_data():
    try:
        with open("mllo_web/app/api/queries/find_pipelines_query.txt") as file:
            SPARQL_QUERY = file.read()
        sparql_results = sq.query(SPARQL_ENDPOINT, SPARQL_QUERY)
        return sq.to_dict(sparql_results)
    except Exception as e:
        raise HTTPException(status_code= 500, detail=f"Failed to fetch models data: {e}")

pipelines = fetch_data() 


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
