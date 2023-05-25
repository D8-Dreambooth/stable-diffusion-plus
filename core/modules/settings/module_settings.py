import asyncio
import logging
import os

import bcrypt
from fastapi import FastAPI

from core.handlers.config import ConfigHandler
from core.handlers.models import ModelHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


class SettingsModule(BaseModule):

    def __init__(self):
        self.id = "settings"
        self.name = "Settings"
        self.path = os.path.abspath(os.path.dirname(__file__))
        self.config_handler = ConfigHandler()
        super().__init__(self.id, self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        socket_handler = SocketHandler()
        socket_handler.register("set_settings", self.set_settings)
        socket_handler.register("test_push", self.test_push)

    async def refresh_after_delay(self, mh):
        await asyncio.sleep(30)  # Wait for 30 seconds
        mh.refresh("diffusers")

    async def test_push(self, req):
        mh = ModelHandler(user_name="admin")
        asyncio.create_task(self.refresh_after_delay(mh))
        return {"status": "ACK ACK"}

    async def set_settings(self, req):
        data = req["data"] if "data" in req else {}
        section = data.get("section", None)
        key = data.get("key", None)
        value = data.get("value", None)
        updated = False
        if section and key and value is not None:
            key = key.replace(" ", "_")
            section = section.replace(" ", "_")
            if section == "core" or section == "users":
                updated = self.config_handler.set_item_protected(key, value, section)
            else:
                updated = self.config_handler.set_item_protected(key, value, section)

        status = {"status": "Updated" if updated else "Invalid key or section", "key": key, "value": value}
        return status

    async def update_password(self, req):
        user = req.get("user", None)
        ch = ConfigHandler()
        user_data = ch.get_item_protected(user, "users", None)
        is_admin = False
        if user:
            if user_data:
                is_admin = user_data.get("admin", False)

            data = req["data"] if "data" in req else {}

            update_user = data.get("user", None)
            password = data.get("password", None)
            if is_admin or update_user == user:
                encrypted_pass = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                user_data["pass"] = encrypted_pass.decode()
                ch.set_item_protected(user, user_data, "users")
                return {"status": "Password updated successfully."}
            return {"status": "Unable to update password."}



