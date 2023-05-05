import asyncio
import os
import logging

from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.handlers.file import FileHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


# Rename this class to match your module name
class SampleModule(BaseModule):

    def __init__(self):
        # Rename this variable to match your module name
        self.name: str = "Sample Module"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.name, self.path)

    # This method is called when the module is loaded by the server
    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)
        self._initialize_api(app)

    # We use this to register websocket events from the client
    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("sample_socket_call", self._sample_method)

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

    async def _sample_method(self, data):
        logger.debug(f"Data: {data}")
        await asyncio.sleep(1)
        # Always return JSON
        return {"status": "Success"}
