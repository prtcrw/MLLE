from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import mllo_web.frontend.web as web_dir

app = FastAPI(title="MLLO")

web_root_path = Path(list(web_dir.__path__)[0])

app.mount("/", StaticFiles(directory=Path(web_root_path, "dist"), html=True), name="ui")


def run():
    uvicorn.run(app, host="0.0.0.0", port=5252)


if __name__ == "__main__":
    run()
