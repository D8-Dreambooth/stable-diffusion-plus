import json
import os.path
import logging
import traceback

from fastapi import FastAPI

from core.handlers.config import ConfigHandler
from core.handlers.websocket import SocketHandler


logger = logging.getLogger(__name__)


class BaseModule:

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.logger = logger
        self.socket_handler = None
        self.source = os.path.join(self.path, "index.html")
        self.css_files, self.js_files, self.custom_files = self._enum_files()

        icon_path = os.path.join(self.path, "logo.png")
        if not os.path.exists(icon_path):
            icon_path = None
        self.icon = icon_path
        self._set_defaults()

    def get_files(self):
        foo = "foo"

        return self.css_files, self.js_files, self.custom_files, self.source

    def _enum_files(self):
        css_dir = os.path.join(self.path, "css")
        js_dir = os.path.join(self.path, "js")
        custom_dir = os.path.join(self.path, "custom")
        css_files = []
        js_files = []
        custom_files = []

        for file_dir, output, filter in [(css_dir, css_files, ".css"), (js_dir, js_files, ".js"), (custom_dir, custom_files, None)]:
            if not os.path.exists(file_dir) or not os.path.isdir(file_dir):
                continue
            files = os.listdir(file_dir)
            for file in files:
                if filter is not None and filter not in file:
                    continue
                full_file = os.path.abspath(os.path.join(file_dir, file))
                output.append(full_file)
        return css_files, js_files, custom_files

    def _set_defaults(self):
        config_dir = os.path.join(self.path, "config")
        config_handler = ConfigHandler()
        if os.path.exists(config_dir):
            files = os.listdir(config_dir)
            for file in files:
                if ".json" not in file:
                    continue
                full_file_path = os.path.abspath(os.path.join(config_dir, file))
                try:
                    with open(full_file_path) as f:
                        file_key = file.replace(".json", "")
                        file_data = json.load(f)
                        logger.debug(f"Check/set default config: {file_key}")
                        # Tries to set default values for a module if none exist
                        config_handler.set_default_config(file_data, file_key)
                except Exception as e:
                    logger.warning(f"Exception loading default JSON: {e}")
                    traceback.print_exc()

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_api(app)
        self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
        pass

    def _initialize_websocket(self, handler: SocketHandler):
        # Keep a reference to the handler for deregister and broadcast functions
        self.socket_handler = handler
