import importlib
import os
from typing import Dict

from core.modules.base.module_base import BaseModule


class ModuleHandler:
    _instance = None
    module_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modules"))
    active_modules = {}

    def __new__(cls, module_dir):
        if cls._instance is None:
            cls._instance = super(ModuleHandler, cls).__new__(cls)
            cls._instance.module_dir = module_dir
            cls._instance.initialize_modules()
        return cls._instance

    def initialize_modules(self):
        for root, dirs, files in os.walk(self.module_dir):
            for mod_dir in dirs:
                module_path = os.path.join(root, mod_dir)
                for file in os.listdir(module_path):
                    if file.endswith(".py"):
                        module_file = os.path.join(module_path, file)
                        module_dir = os.path.basename(os.path.dirname(module_file))
                        module_name = file[:-3]
                        try:
                            module_str = f"core.modules.{module_dir}.{module_name}"
                            module = importlib.import_module(module_str)
                            initialize = getattr(module, "initialize", None)
                            if callable(initialize):
                                module_obj = initialize()
                                self.active_modules[module_name] = module_obj
                            else:
                                print(f"Not callable: {initialize}")
                        except Exception as e:
                            print(f"Failed to initialize module '{module_name}': {e}")

    def get_modules(self) -> Dict[str, BaseModule]:
        return self.active_modules
