import logging
import os.path

from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.dataclasses.infer_data import InferSettings
from core.modules.base.module_base import BaseModule
from core.modules.infer.src.infer_utils import start_inference

logger = logging.getLogger(__name__)


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


async def _start_inference(msg):
    data = msg["data"]
    websocket = msg["socket"]
    msg_id = msg["id"]

    logger.debug(f"Raw data: {data}")
    infer_data = InferSettings(data)
    logger.debug("Sending response")
    await websocket.send_json({"name": "infer", "message": "Inference received.", "id": msg_id})
    logger.debug("Broadcasting response: ")
    images, prompts = await start_inference(infer_data)
    return {"name": "infer", "message": "Inference completed.", "images": images, "prompts": prompts}


def initialize():
    print("Infer Init!")
    return InferenceModule("Inference")
