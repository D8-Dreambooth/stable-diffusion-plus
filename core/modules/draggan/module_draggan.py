import asyncio
import logging
import os
from typing import Dict

from fastapi import FastAPI
from starlette.responses import JSONResponse

from core.handlers.models import ModelHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


# Rename this class to match your module name
class SampleModule(BaseModule):

    def __init__(self):
        # Rename this variable to match your module name
        self.name: str = "DragGAN"
        self.id = "draggan"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.id, self.name, self.path)

    # This method is called when the module is loaded by the server
    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)
        self._initialize_api(app)

    # We use this to register websocket events from the client
    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("dragGanStart", self._start_draggan)
        handler.register("dragGanStop", self._stop_draggan)

    # We use this to register API endpoints
    def _initialize_api(self, app: FastAPI):
        @app.get(f"/{self.name}/sampleFunction")
        async def import_model() -> JSONResponse:
            """
            Check the current state of Dreambooth processes.
            foo
            @return:
            """
            # Here's where we would call some methods from module_functions.py if we wanted to.
            return JSONResponse(content={"message": f"Message received started."})

    async def _start_draggan(self, data: Dict):
        logger.debug(f"Data: {data}")
        user = data.get("user", None)
        mh = ModelHandler(user_name=user)
        model_url = "https://drive.google.com/u/0/uc?id=1PQutd-JboOCOZqmd95XWxWrO8gGEvRcO&export=download&confirm=t&uuid=77711f3d-fb94-4292-8e79-954702391294&at=AKKF8vz47BfyF9-sjG98vPsXGB_n:1684857630766"
        model = mh.load_models("draggan", model_url, download_name="550000.pt")
        await asyncio.sleep(1)
        # Always return JSON
        return {"status": "Success"}

    async def _stop_draggan(self, data: Dict):
        logger.debug(f"Data: {data}")
        user = data.get("user", None)
