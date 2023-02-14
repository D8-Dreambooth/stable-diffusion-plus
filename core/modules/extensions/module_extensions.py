import os.path

from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.handlers.websockets import SocketHandler
from core.modules.base.module_base import BaseModule


class ExtensionModule(BaseModule):
    name: str = "Extension"

    def __init__(self, name):
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(name, self.path)

    def initialize_api(self, app: FastAPI):
        @app.get(f"/{self.name}/extension")
        async def extension_test(
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
        handler.register("extension", _start_inference)


async def _start_inference(websocket, data):
    print(f"Ext passed: {data}")
    await websocket.send_text("ext received.")


def initialize():
    print("Infer Init!")
    return ExtensionModule("Inference")
