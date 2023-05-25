import json
import os.path
import logging
import traceback

from fastapi import FastAPI

from core.handlers.config import ConfigHandler
from core.handlers.directories import DirectoryHandler
from core.handlers.websocket import SocketHandler


logger = logging.getLogger(__name__)


class BaseModule:

    def __init__(self, id, name, path):
        self.id = id
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
        if os.path.exists(templates_dir):
            dh = DirectoryHandler()
            protected_dir = dh.protected_path
            locales_dir = os.path.join(protected_dir, "locales")
            defaults_dir = os.path.join(protected_dir, "defaults")
            locales_file = os.path.join(locales_dir, f"locales.json")
            if not os.path.exists(locales_dir):
                os.makedirs(locales_dir)
            if not os.path.exists(defaults_dir):
                os.makedirs(defaults_dir)
            existing_locales = {}
            if os.path.exists(locales_file):
                logger.debug(f"Loading existing locales {locales_file}")
                with open(locales_file, "r") as f:
                    existing_locales = json.load(f)
            updated = False
            module_locales = os.path.join(templates_dir, "locales")
            if os.path.exists(module_locales):
                logger.debug(f"Enumerating module locales {module_locales}")
                for file in os.listdir(module_locales):
                    if ".json" not in file or "titles" not in file:
                        continue
                    with open(os.path.join(module_locales, file), "r") as f:
                        locale_data = json.load(f)
                    lang_key = file.replace(".json", "")
                    lang_key = lang_key.replace("titles_", "")
                    logger.debug("LANG KEY: " + lang_key)
                    existing_lang = existing_locales.get(lang_key, {})
                    existing_locale = existing_lang.get(f"module_{self.id}", {})
                    # Loop through default locales and add missing keys, remove extra keys
                    for key, value in locale_data.items():
                        if key not in existing_locale:
                            updated = True
                            existing_locale[key] = value
                    for key, value in existing_locale.items():
                        if key not in locale_data:
                            updated = True
                            existing_locale.pop(key)
                    existing_lang[f"module_{self.id}"] = existing_locale
                    existing_locales[lang_key] = existing_lang

            if updated:
                logger.debug(f"Updating locale: {self.id}")
                with open(locales_file, "w") as f:
                    json.dump(existing_locales, f, indent=4)

        self.icon = icon_path
        self._set_defaults()

    def get_files(self):
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

    def get_defaults(self):
        config_handler = ConfigHandler()
        return config_handler.get_module_defaults(self.name)

    def _set_defaults(self):
        templates_dir = os.path.join(self.path, "templates")
        config_dir = os.path.join(templates_dir, "config")
        defaults_dir = os.path.join(templates_dir, "defaults")
        # Get default system language
        config_handler = ConfigHandler()
        if os.path.exists(defaults_dir):
            for file in os.listdir(defaults_dir):
                if ".json" not in file:
                    continue
                default_file = os.path.abspath(os.path.join(defaults_dir, file))
                default_name = file.replace(".json", "")
                if default_name == "defaults":
                    default_name = self.name
                config_handler.set_module_default(default_file, default_name)
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
                        config_handler.set_default_config(file_data, file_key, True)
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
