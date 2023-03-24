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
        user = req.get("user", None)
        ch = ConfigHandler()
        shared_config, protected_config = ch.get_all_protected()
        user_data = ch.get_item_protected(user, "users", None)
        users = []
        for user, ud in protected_config["users"].items():
            users.append(ud)
        logger.debug(f"Use data and user: {user_data} {user}")
        pc = {"users": users}
        if user:
            if user_data:
                logger.debug(f"USER: {user}")
                if user_data["admin"]:
                    pc = protected_config
        logger.debug(f"USER: {user}")
        return {"status": "ACK ACK", "shared": shared_config, "protected": pc}

    async def set_settings(self, req):
        logger.debug(f"Set settings request: {req}")
        data = req["data"] if "data" in req else {}
        section = data.get("section", None)
        key = data.get("key", None)
        value = data.get("value", None)
        updated = False
        if section and key and value is not None:
            key = key.replace(" ", "_")
            section = section.replace(" ", "_")
            logger.debug("We have all values...")
            if section == "core" or section == "users":
                logger.debug(f"Set protected: {section}")
                updated = self.config_handler.set_item_protected(key, value, section)
            else:
                logger.debug(f"Set shared: {section}")
                updated = self.config_handler.set_item(key, value, section)

        status = {"status": "Updated" if updated else "Invalid key or section", "key": key, "value": value}
        return status




