import os
import types
from typing import Dict

from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule


class ExtensionHandler:
    _instance = None
    _initialized = False
    _base_dir = None
    _extensions_dir = None
    _active_extensions = {}

    def __new__(cls, base_dir: str, extensions_dir: str):
        if not cls._instance:
            cls._instance = super(ExtensionHandler, cls).__new__(cls)
            cls._instance._base_dir = base_dir
            cls._instance._extensions_dir = extensions_dir
            cls._instance._initialize_extensions()
            cls._socket_handler = SocketHandler()
        return cls._instance

    def _initialize_extensions(self):
        shared_path = os.path.join(self._base_dir, "core")

        def get_shared_methods():
            methods = {}
            for file in os.listdir(shared_path):
                if file.endswith(".py"):
                    module_name = file[:-3]
                    module = __import__(f"core.shared.{module_name}")
                    for attr in dir(module):
                        item = getattr(module, attr)
                        if callable(item):
                            methods[attr] = item
            return methods

        shared_methods = get_shared_methods()

        for root, dirs, files in os.walk(self._extensions_dir):
            for file in files:
                if file.endswith(".py"):
                    extension_file = os.path.join(root, file)
                    extension_name = file[:-3]
                    try:
                        extension = types.ModuleType(extension_name)
                        exec(open(extension_file).read(), vars(extension))
                        initialize = getattr(extension, "initialize", None)
                        if callable(initialize):
                            for attr in dir(extension):
                                item = getattr(extension, attr)
                                if callable(item):
                                    setattr(item, "__globals__", shared_methods)
                            self._active_extensions[extension_name] = initialize()
                    except Exception as e:
                        print(f"Failed to initialize extension '{extension_name}': {e}")

    def get_extensions(self) -> Dict[str, BaseModule]:
        return self._active_extensions
