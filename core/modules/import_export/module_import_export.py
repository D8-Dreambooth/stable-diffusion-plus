import os.path

from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule


class ImportExportModule(BaseModule):

    def __init__(self):
        self.name: str = "Import/Export"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_api(app)
        self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
        @app.get(f"/{self.name}/import")
        async def import_model(
                api_key: str = Query("", description="If an API key is set, this must be present.", )) -> \
                JSONResponse:
            """
            Check the current state of Dreambooth processes.
            foo
            @return:
            """
            return JSONResponse(content={"message": f"Job started."})

    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("import_export", _import_model)


async def _import_model(data):
    websocket = data["socket"]
    await websocket.send_text({"message": "ext received."})
