import asyncio
import logging
import mimetypes
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi_events.handlers.local import local_handler
from fastapi_events.middleware import EventHandlerASGIMiddleware

import mllo_web.frontend.web as web_dir
from mllo_web.app.api.staticfiles import NoCacheStaticFiles, SPAStaticFiles
from mllo_web.app.api.sockets import SocketIO
from mllo_web.app.services.config.config_default import get_config
from mllo_web.backend.util.logging import MlloLogger

app_config = get_config()
logger = MlloLogger.get_logger(config=app_config)

# Create the app
app = FastAPI(
    title="MLLO",
    docs_url=None,
    redoc_url=None,
    separate_input_output_schemas=False,
)

# Add event handler
event_handler_id: int = id(app)
app.add_middleware(
    EventHandlerASGIMiddleware,
    handlers=[local_handler],  # TODO: consider doing this in services to support different configurations
    middleware_id=event_handler_id,
)

socket_io = SocketIO(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.allow_origins,
    allow_credentials=app_config.allow_credentials,
    allow_methods=app_config.allow_methods,
    allow_headers=app_config.allow_headers,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


web_root_path = Path(list(web_dir.__path__)[0])

try:
    app.mount("/", SPAStaticFiles(directory=Path(web_root_path, "dist"), html=True), name="ui")
except RuntimeError:
    logger.warning(f"No UI found at {web_root_path}/dist, skipping UI mount")
app.mount(
    "/static", NoCacheStaticFiles(directory=Path(web_root_path, "static/")), name="static"
)  # docs favicon is in here


def mllo_web() -> None:
    def find_port(port: int) -> int:
        """Find a port not in use starting at given port"""
        # https://github.com/WaylonWalker
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(("localhost", port)) == 0:
                return find_port(port=port + 1)
            else:
                return port

    port = find_port(app_config.port)
    if port != app_config.port:
        logger.warning(f"Port {app_config.port} in use, using port {port}")

    # Start our own event loop for eventing usage
    loop = asyncio.new_event_loop()
    config = uvicorn.Config(
        app=app,
        host=app_config.host,
        port=port,
        loop="asyncio",
        log_level=app_config.log_level,
        ssl_certfile=app_config.ssl_certfile,
        ssl_keyfile=app_config.ssl_keyfile,
    )
    server = uvicorn.Server(config)

    loop.run_until_complete(server.serve())


if __name__ == "__main__":
    mllo_web()
