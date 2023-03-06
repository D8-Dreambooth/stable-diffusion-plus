import os.path

from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.handlers.websockets import SocketHandler
from core.modules.base.module_base import BaseModule


class ImportExportModule(BaseModule):
    name: str = "Import/Export"

    def __init__(self, name):
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(name, self.path)

    def initialize_api(self, app: FastAPI):
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

    def initialize_websocket(self, handler: SocketHandler):
        super().initialize_websocket(handler)
        print("Init infer handler!")
        handler.register("import_export", _import_model)


async def _import_model(data):
    model_info = data["model_info"]
    websocket = data["socket"]
    print(f"Ext passed: {model_info}")
    await websocket.send_text({"message": "ext received."})


def initialize():
    print("Infer Init!")
    return ImportExportModule("Import/Export")
