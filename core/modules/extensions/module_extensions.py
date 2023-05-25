import logging
import os.path

from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


class ExtensionModule(BaseModule):

    def __init__(self):
        self.id = "extensions"
        self.name = "Extension Manager"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.id, self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_api(app)
        self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
        @app.get(f"/extensions/test")
        async def extension_test(
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
        handler.register("extension", _start_inference)


async def _start_inference(data):
    websocket = data["socket"]
    await websocket.send_text("ext received.")


def initialize():
    return ExtensionModule("Inference")
