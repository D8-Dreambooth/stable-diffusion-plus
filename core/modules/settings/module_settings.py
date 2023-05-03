import logging
import os

import bcrypt
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
        socket_handler = SocketHandler()
        socket_handler.register("get_settings", self.get_settings)
        socket_handler.register("set_settings", self.set_settings)
        socket_handler.register("change_password", self.update_password)

    async def get_settings(self, req):
        user = req.get("user", None)
        ch = ConfigHandler()
        shared_config, protected_config = ch.get_all_protected()
        user_data = ch.get_item_protected(user, "users", None)
        users = []
        if "users" in protected_config.keys():
            for user, ud in protected_config["users"].items():
                users.append(ud)
        pc = {"users": [user_data]}
        if user:
            if user_data:
                is_admin = user_data.get("admin", False)
                if is_admin:
                    pc = protected_config
                    sorted_users = sorted(users, key=lambda u: u.get("name") != user)
                    pc["users"] = sorted_users
                else:
                    pc = {"users": []}
                    for u in users:
                        if u.get("name") == user:
                            u.pop("admin", None)
                            pc["users"].append(u)
        return {"status": "ACK ACK", "shared": shared_config, "protected": pc}

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
                updated = self.config_handler.set_item(key, value, section)

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
                ch.set_item_protected(user,user_data, "users")
                return {"status": "Password updated successfully."}
            return {"status": "Unable to update password."}



