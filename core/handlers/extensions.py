import importlib
import inspect
import logging
import os
import types
from typing import Dict

from core.handlers.directories import DirectoryHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule
from core.shared.base_extension import BaseExtension

logger = logging.getLogger(__name__)


class ExtensionHandler:
    _instance = None
    _initialized = False
    _base_dir = None
    _extensions_dir = None
    _active_extensions = {}

    def __new__(cls):
        if not cls._instance:
            dir_handler = DirectoryHandler()
            extensions_dir = dir_handler.get_directory("extensions")
            base_dir = dir_handler.app_path
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
                if file.endswith(".py") and "__init__" not in file:
                    module_name = file[:-3]
                    module = __import__(f"core.shared.{module_name}")
                    for attr in dir(module):
                        item = getattr(module, attr)
                        if callable(item):
                            methods[attr] = item
            return methods

        shared_methods = get_shared_methods()
        for ext_dir in self._extensions_dir:
            for root, dirs, files in os.walk(ext_dir):
                for file in files:
                    if file.endswith(".py"):
                        extension_file = os.path.join(root, file)
                        extension_name = file[:-3]
                        extension_dir = os.path.basename(os.path.dirname(extension_file))
                        if extension_name in self._active_extensions:
                            continue
                        try:
                            module_str = f"core.extensions.{extension_dir}.{extension_name}"
                            ext = importlib.import_module(module_str)
                            module_classes = inspect.getmembers(ext, inspect.isclass)
                            base_classes = [cls for name, cls in module_classes if
                                            issubclass(cls, BaseExtension) and cls is not BaseExtension]
                            if not base_classes:
                                continue
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
                            pass

    def get_extensions(self) -> Dict[str, BaseModule]:
        return self._active_extensions
