from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import mllo_web.frontend.web as web_dir
from mllo_web.app.api.config import get_config
from mllo_web.app.api.routers import find_datasets, find_models, find_pipelines, plot_performances
from mllo_web.app.api.services.sparql_client import MobiSparqlClient
from mllo_web.app.util.logging import Logger

config = get_config()
logger = Logger.get_logger(config=config)

app = FastAPI(title="MLLO")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=config.allow_credentials,
    allow_origins=config.allow_origins,
    allow_methods=config.allow_methods,
    allow_headers=config.allow_headers
)

app.sparql_client = MobiSparqlClient(config=config)

# Include all routers
app.include_router(find_datasets.router, prefix="/api")
app.include_router(find_models.router, prefix="/api")
app.include_router(find_pipelines.router, prefix="/api")
app.include_router(plot_performances.router, prefix="/api")

web_root_path = Path(list(web_dir.__path__)[0])

try:
    app.mount("/", StaticFiles(directory=Path(web_root_path, "dist"), html=True), name="ui")
except RuntimeError:
    logger.warning(f"No UI found at {web_root_path}/dist, skipping UI mount")


def run():
    if config.dev:
        logger.info(f"Running in the development mode.")

    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    run()
