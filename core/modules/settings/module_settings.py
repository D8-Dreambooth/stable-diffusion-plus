import logging
import os

from fastapi import FastAPI

from core.handlers.config import ConfigHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


class SettingsModule(BaseModule):

    def __init__(self):
        self.name = "Settings"
        self.path = os.path.abspath(os.path.dirname(__file__))
        self.config_handler = ConfigHandler()
        super().__init__(self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        logger.debug("Init settings module.")
        socket_handler = SocketHandler()
        socket_handler.register("get_settings", self.get_settings)
        socket_handler.register("set_settings", self.set_settings)

    async def get_settings(self, req):
        logger.debug(f"Get settings request: {req}")
        user = None
        if "data" in req:
            data = req["data"]
            if "user" in data:
                user = data["user"]
                logger.debug(f"USER: {user}")

        return {"status": "ACK ACK"}

    async def set_settings(self, req):
        logger.debug(f"Set settings request: {req}")
        return {"status": "ACK ACK"}




