import os.path

from fastapi import FastAPI

from core.handlers.websockets import SocketHandler


class BaseModule:
    name: str = "Base"

    def __init__(self, name, base_path=None):
        self.name = name
        self.socket_handler = None
        self.path = os.path.abspath(os.path.dirname(__file__)) if base_path is None else base_path
        self.source = os.path.join(self.path, "index.html")
        self.css_files, self.js_files, self.custom_files = self._enum_files()

        icon_path = os.path.join(self.path, "logo.png")
        if not os.path.exists(icon_path):
            icon_path = None
        self.icon = icon_path

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

    def initialize_api(self, app: FastAPI):
        pass

    def initialize_websocket(self, handler: SocketHandler):
        # Keep a reference to the handler for deregister and broadcast functions
        self.socket_handler = handler


def initialize():
    return BaseModule("BaseModule")
