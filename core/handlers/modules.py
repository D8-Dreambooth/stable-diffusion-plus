import importlib
import inspect
import logging
import os
import traceback
from typing import Dict

from core.handlers.config import ConfigHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule


logger = logging.getLogger(__name__)


class ModuleHandler:
    _instance = None
    module_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modules"))
    active_modules = {}
    socket_handler = None

    def __new__(cls, module_dir, socket_handler: SocketHandler = None):
        if cls._instance is None and module_dir is not None and socket_handler is not None:
            cls._instance = super(ModuleHandler, cls).__new__(cls)
            cls._instance.module_dir = module_dir
            cls._instance.initialize_modules()
            cls._instance.socket_handler = socket_handler
            socket_handler.register("get_modules", cls._instance._get_modules)
        return cls._instance

    async def _get_modules(self, data):
        ch = ConfigHandler()
        module_data = {}
        for module_name, module in self.active_modules.items():
            model_config = ch.get_config(module_name.replace("module_", ""))
            model_defaults = {}
            try:
                model_defaults = module.get_defaults()
            except Exception as e:
                logger.warning(f"Error getting defaults for {module_name}: {e}")
                pass
            module_data[module_name] = {
                "config": model_config if model_config else {},
                "defaults": model_defaults
            }
        return {"module_data": module_data}

    def initialize_modules(self):
        for root, dirs, files in os.walk(self.module_dir):
            for mod_dir in dirs:
                module_path = os.path.join(root, mod_dir)
                for file in os.listdir(module_path):
                    if file.endswith(".py"):
                        module_file = os.path.join(module_path, file)
                        module_dir = os.path.basename(os.path.dirname(module_file))
                        module_name = file[:-3]

                        if module_name == "module_base":
                            continue
                        if "install" in file:
                            continue
                        if not module_name.startswith("module_"):
                            continue
                        try:
                            module_str = f"core.modules.{module_dir}.{module_name}"
                            module = importlib.import_module(module_str)
                            module_classes = inspect.getmembers(module, inspect.isclass)
                            base_classes = [cls for name, cls in module_classes if
                                            issubclass(cls, BaseModule) and cls is not BaseModule]
                            if not base_classes:
                                continue
                            module_obj = None
                            for cls in base_classes:
                                try:
                                    module_obj = cls()
                                    break
                                except Exception as e:
                                    logging.warning(f"Failed to instantiate module {module_name}: {e}")
                                    traceback.print_exc()
                            if module_obj:
                                self.active_modules[module_name] = module_obj

                        except Exception as e:
                            logger.debug(f"Failed to initialize module '{module_name}': {e}")
                            # traceback.logger.debug_exc()

    def get_modules(self) -> Dict[str, BaseModule]:
        return self.active_modules
