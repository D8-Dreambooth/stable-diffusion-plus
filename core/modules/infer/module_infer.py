import os.path

from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.handlers.websockets import SocketHandler
from core.modules.base.module_base import BaseModule


class InferenceModule(BaseModule):
    name: str = "Inference"

    def __init__(self, name):
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(name, self.path)

    def initialize_api(self, app: FastAPI):
        @app.get(f"/{self.name}/infer")
        async def create_image(
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
        handler.register("infer", _start_inference)


async def _start_inference(websocket, data):
    print(f"Inference passed: {data}")
    await websocket.send_text("Inference received.")


def initialize():
    print("Infer Init!")
    return InferenceModule("Inference")
