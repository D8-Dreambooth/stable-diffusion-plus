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
        templates_dir = os.path.join(self.path, "templates")
        locale_data = None
        logger.debug("Looking for template dir: %s", templates_dir)
        if os.path.exists(templates_dir):
            ch = ConfigHandler()
            existing_locales = ch.get_item_protected(self.name, "locales", {})
            updated = False
            for file in os.listdir(templates_dir):
                if ".json" not in file or "titles" not in file:
                    continue
                logger.debug("Loading locale file: %s", file)
                with open(os.path.join(templates_dir, file), "r") as f:
                    locale_data = json.load(f)
                file_key = file.replace(".json", "")
                file_key = file_key.replace("titles_", "")
                # Loop through default locales and add missing keys, remove extra keys
                if file_key in existing_locales:
                    existing_locale = existing_locales[file_key]
                    for key, value in locale_data.items():
                        if key not in existing_locale:
                            updated = True
                            existing_locale[key] = value
                    for key, value in existing_locale.items():
                        if key not in locale_data:
                            updated = True
                            existing_locale.pop(key)
                    existing_locales[file_key] = existing_locale
                else:
                    updated = True
                    existing_locales[file_key] = locale_data
            if updated:
                ch.set_item_protected(self.name, existing_locales, "locales")

        self.icon = icon_path
        self._set_defaults()

    def get_files(self):
        return self.css_files, self.js_files, self.custom_files, self.source

    def get_locale(self, lang: str = "en"):
        ch = ConfigHandler()
        locales_data = ch.get_item_protected(self.name, "locales", {})
        logger.debug("Locales data: %s", locales_data)
        locale_data = {}
        if lang in locales_data:
            locale_data = locales_data[lang]
        return locale_data

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
        templates_dir = os.path.join(self.path, "templates")
        # Get default system language
        config_handler = ConfigHandler()
        if os.path.exists(templates_dir):
            default_file = os.path.join(templates_dir, f"defaults.json")
            if os.path.exists(default_file):
                config_handler.set_module_default(default_file, self.name)
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
                        # Tries to set default values for a module if none exist
                        config_handler.set_default_config(file_data, file_key, False)
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
