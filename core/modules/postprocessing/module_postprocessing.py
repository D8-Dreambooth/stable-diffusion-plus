import asyncio
import logging
import os

from fastapi import FastAPI

from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


# Rename this class to match your module name
class PostProcessingModule(BaseModule):

    def __init__(self):
        # Rename this variable to match your module name
        self.id = "postprocessing"
        self.name: str = "PostProcessing"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.id, self.name, self.path)

    # This method is called when the module is loaded by the server
    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)

    # We use this to register websocket events from the client
    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("process_image", self._process_image)
        handler.register("process_directory", self._process_directory)

    async def _process_image(self, data):
        logger.debug(f"Data: {data}")
        await asyncio.sleep(1)
        # Always return JSON
        return {"status": "Success"}

    async def _process_directory(self, data):
        logger.debug(f"Data: {data}")
        await asyncio.sleep(1)
        # Always return JSON
        return {"status": "Success"}
