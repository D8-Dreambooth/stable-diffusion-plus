import asyncio
import logging
import os.path


from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.dataclasses.infer_data import InferSettings
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule
from core.modules.infer.src.infer_utils import start_inference

logger = logging.getLogger(__name__)


class InferenceModule(BaseModule):

    def __init__(self):
        self.name = "Inference"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_api(app)
        self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
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

    def _initialize_websocket(self, handler: SocketHandler):
        handler.register("start_inference", _start_inference)


async def _start_inference(msg):
    data = msg["data"]
    msg_id = msg["id"]
    user = msg["user"] if "user" in msg else None
    logger.debug(f"Raw data: {data}")
    infer_data = InferSettings(data)
    logger.debug(f"Inference data: {infer_data}")
    # Call start_inference() in a separate thread using asyncio.create_task()
    asyncio.create_task(start_inference(infer_data, user))

    # Immediately return a reply to the websocket
    return {"name": "inference_started", "message": "Inference started.", "id": msg_id}
