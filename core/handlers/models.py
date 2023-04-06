import gc
import glob
import importlib
import logging
import os
import shutil
import traceback
from typing import List
from urllib.parse import urlparse

import torch
from basicsr.utils.download_util import load_file_from_url

from core.dataclasses.model_data import ModelData
from core.handlers.directories import DirectoryHandler
from core.handlers.websocket import SocketHandler
from dreambooth.sd_to_diff import extract_checkpoint


class ModelHandler:
    _instance = None
    _instances = {}
    models_path = []
    socket_handler = None
    loaded_models = {}
    listed_models = {}
    model_loaders = {}
    model_finders = {}
    load_params = {}
    user_name = None
    logger = None

    def __new__(cls, user_name=None):
        if cls._instance is None:
            dir_handler = DirectoryHandler()
            models_path = dir_handler.get_directory("models")
            cls._instance = super(ModelHandler, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(f"{__name__}-shared")
            cls._instance.logger.debug(f"INIT MODEL HANDLER: {models_path}")
            cls._instance.models = {}
            cls._instance.loaded_models = {}
            cls._instance.models_path = models_path
            cls._instance.socket_handler = SocketHandler()
            cls._instance.socket_handler.register("models", cls._instance.list_models)
            cls._instance.socket_handler.register("load_model", cls._instance.loadmodel)
            cls._instance.initialize_loaders()
        if user_name is not None:
            if user_name in cls._instances:
                return cls._instances[user_name]

            else:
                dir_handler = DirectoryHandler(user_name=user_name)
                models_path = dir_handler.get_directory("models")
                user_instance = super(ModelHandler, cls).__new__(cls)
                user_instance.logger = logging.getLogger(f"{__name__}-{user_name}")
                user_instance.models = {}
                user_instance.loaded_models = {}
                user_instance.models_path = models_path
                user_instance.socket_handler = SocketHandler()
                user_instance.socket_handler.register("models", user_instance.list_models, user_name)
                user_instance.socket_handler.register("load_model", user_instance.loadmodel, user_name)
                user_instance.user_name = user_name
                user_instance.initialize_loaders()
                cls._instances[user_name] = user_instance
                return user_instance
        else:
            return cls._instance

    async def list_models(self, msg):
        data = msg["data"]
        self.logger.debug(f"Socket model request received: {data}")
        if "model_type" not in data:
            self.logger.debug(f"Invalid request: {data}")
            return {"message": "Invalid data."}
        else:
            model_list = []
            model_type = data["model_type"]
            if model_type in self.model_finders:
                self.logger.debug(f"Using finder: {model_type}")
                model_list = self.model_finders[model_type](data, self)
            else:
                self.logger.debug(f"Using default model loader: {model_type}")
                ext_include = None if "ext_include" not in data else data["ext_include"]
                ext_exclude = None if "ext_exclude" not in data else data["ext_exclude"]
                model_list = self.load_models(model_type=data["model_type"], ext_include=ext_include, ext_exclude=ext_exclude)

            self.logger.debug(f"Got model_list: {model_list}")
            model_json = [model.serialize() for model in model_list]
            loaded_model = None
            if data["model_type"] in self.loaded_models:
                model_data, _ = self.loaded_models[data["model_type"]]
                loaded_model = model_data.hash
            return {"models": model_json, "loaded": loaded_model}

    async def find_model(self, model_type: str, value: str):
        if model_type in self.listed_models:
            models = self.listed_models[model_type]
        elif model_type in self.load_params:
            params = self.load_params[model_type]
            models = self.load_models(model_type, **params)
        else:
            self.logger.debug("Can't list models?")
            models = []
        for model in models:
            if model.name == value or model.hash == value or model.display_name == value or model.path == value:
                return model

    async def loadmodel(self, msg):
        data = msg["data"]
        self.logger.debug(f"Socket model request received: {data}")
        try:
            md = ModelData("http")
            md.deserialize(data)
        except Exception as e:
            self.logger.debug(f"Can't deserialize: {data} {e}")
            return {"error": "Unable to deserialize data."}

        if "model_type" not in data:
            self.logger.debug(f"Invalid request: {data}")
            return {"message": "Invalid data."}
        else:
            model_type = data["model_type"]
            self.load_model(model_type, md)
            return {"loaded": md.serialize()}

    def initialize_loaders(self):
        directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), "model_types")
        for filename in os.listdir(directory):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = os.path.basename(filename).replace(".py", "")
                module = importlib.import_module(f"core.handlers.model_types.{module_name}")
                if hasattr(module, "register_function"):
                    module.register_function(self)

    def load_models(self,
                    model_type: str,
                    model_url: str = None,
                    ext_include: List[str] = None,
                    ext_exclude: List[str] = None,
                    download_name=None
                    ) -> List[ModelData]:
        """
        A one-and done loader to try finding the desired models in specified directories.

        @param model_type: The type of model being loaded, and the directory name to store/find the models in.
        @param model_url: If the model does not exist locally, get it from here.        
        @param download_name: Specify to download from model_url immediately.
        @param ext_include: An optional list of filename extensions to include
        @param ext_exclude: An optional list of filename extensions to exclude
        @return: A list of ModelData objects containing the desired model(s)

        """
        output = []
        self.logger.debug(f"Request for mt: {model_type}")

        # Save these for later so when "refresh" is called, we can reload.
        self.load_params[model_type] = {
            "model_url": model_url,
            "ext_include": ext_include,
            "ext_exclude": ext_exclude,
            "download_name": download_name
        }

        if model_type == "diffusers":
            self.logger.debug("Loading diffusion models??")
            diff_dirs = self.load_diffusion_models()
            for diff_dir in diff_dirs:
                self.logger.debug(f"Enumerating: {diff_dir}")
                output.append(ModelData(diff_dir))
            return output

        if ext_include is None:
            ext_include = []

        try:
            self.logger.debug(f"MP: {self.models_path}")
            for mp in self.models_path:
                model_path = os.path.join(mp, model_type)
                self.logger.debug(f"Checking: {model_path}")
                if not os.path.exists(model_path):
                    os.makedirs(model_path)

                for file in glob.iglob(model_path + '**/**', recursive=True):
                    full_path = file
                    if os.path.isdir(full_path):
                        continue
                    if os.path.islink(full_path) and not os.path.exists(full_path):
                        self.logger.debug(f"Skipping broken symlink: {full_path}")
                        continue
                    if ext_exclude is not None and any([full_path.endswith(x) for x in ext_exclude]):
                        continue
                    if len(ext_include) != 0:
                        model_type, extension = os.path.splitext(file)
                        if extension not in ext_include:
                            self.logger.debug(f"NO EXT: {extension}")
                            continue
                    model_data = ModelData(full_path)
                    if model_data not in output:
                        output.append(model_data)

                if model_url is not None and len(output) == 0:
                    if download_name is not None:
                        dl = load_file_from_url(model_url, model_path, True, download_name)
                        model_data = ModelData(dl)
                        output.append(model_data)
                    else:
                        model_data = ModelData(model_url)
                        output.append(model_data)

        except Exception as e:
            self.logger.warning(f"Fucking bullshit: {e}")
            traceback.print_exc()
            pass

        return output

    def refresh(self, model_type: str):
        if model_type not in self.load_params:
            self.logger.debug("Unable to refresh model: ", model_type)
        else:
            params = self.load_params[model_type]
            reloaded = self.load_models(model_type, **params)
            msg = {
                "name": "reload_models",
                "model_type": model_type,
                "models": reloaded,
                "user": self.user_name
            }
            self.socket_handler.manager.broadcast(msg)

    def load_diffusion_models(self):
        model_directories = []
        target_directories = []
        for path in self.models_path:
            target_directories.append(os.path.join(path, "diffusers"))

        self.logger.debug(f"Model dirs: {target_directories}")
        for model_path in target_directories:
            for root, dirs, files in os.walk(model_path):
                # Check if the current directory contains a "model_index.json" file
                if "model_index.json" in files:
                    model_directories.append(root)
                    # Stop searching this directory's subdirectories
                    dirs[:] = []
                # Continue searching other directories
                else:
                    subdirs = [os.path.join(root, d) for d in dirs if os.path.isdir(os.path.join(root, d))]
                    for subdir in subdirs:
                        for subroot, subdirs, subfiles in os.walk(subdir):
                            # Check if the current directory contains a "model_index.json" file
                            if "model_index.json" in subfiles:
                                model_directories.append(subroot)
                                # Stop searching this directory's subdirectories
                                subdirs[:] = []
                            # Continue searching other directories
                            else:
                                subsubdirs = [os.path.join(subroot, d) for d in subdirs if
                                              os.path.isdir(os.path.join(subroot, d))]
                                subdirs[:] = subsubdirs

        output = []
        for md in model_directories:
            if md not in output:
                output.append(md)
        return output

    def register_loader(self, model_type, callback):
        if model_type not in self.model_loaders:
            self.logger.debug(f"Registered model loader: {model_type}")
            self.model_loaders[model_type] = callback

    def register_finder(self, model_type: str, callback):
        if model_type not in self.model_finders:
            self.logger.debug(f"Registering model finder: {model_type}")
            self.model_finders[model_type] = callback

    def load_model(self, model_type: str, model_data: ModelData):
        self.logger.debug(f"We need to load: {model_data.serialize()}")
        if model_type in self.loaded_models:
            loaded_model_data, model = self.loaded_models[model_type]
            if model_data != loaded_model_data:
                self.logger.debug(f"Unloading model: {self.loaded_models[model_type]}")
                del model
                del self.loaded_models[model_type]
                if torch.has_cuda:
                    torch.cuda.empty_cache()
                gc.collect()
        # Convert stable-diffusion/checkpoints to diffusers
        if model_type == "stable-diffusion":
            self.logger.debug("Convert sd model to diffusers.")
            target_model = os.path.join(self.models_path, "diffusers", os.path.basename(model_data.path))
            if os.path.exists(target_model):
                self.logger.debug("Model already extracted")
                return target_model

            try:
                results = extract_checkpoint("test", model_data.path, extract_ema=True, train_unfrozen=True)
                model_dir = results[1]
                self.logger.debug(f"Model Dir: {model_dir}")
                if os.path.exists(model_dir):
                    self.logger.debug(f"We got something: {model_dir}")
                    diffusers_path = os.path.join(model_dir, "working")
                    if os.path.exists(diffusers_path):
                        self.logger.debug("Found the diffusers too.")
                        dest_path = os.path.join(self.models_path, "diffusers")
                        os.makedirs(dest_path)
                        dest_path = os.path.join(self.models_path, "diffusers", os.path.basename(model_data.path))
                        if os.path.exists(dest_path):
                            self.logger.debug("Model already exists!")
                        else:
                            shutil.copytree(diffusers_path, dest_path)
                            self.logger.debug("Diffusers extracted?")
                    shutil.rmtree(model_dir)

            except Exception as e:
                self.logger.warning(f"Couldn't extract checkpoint: {e}")
        else:
            if model_type not in self.model_loaders:
                self.logger.warning(f"No registered loader for model type: {model_type}")
            else:
                loaded = self.model_loaders[model_type](model_data)
                if loaded:
                    self.logger.debug(f"{model_type} model loaded.")
                    if torch.has_cuda:
                        try:
                            loaded = loaded.to("cuda")
                        except:
                            self.logger.debug("Couldn't load model to GPU.")

                    self.loaded_models[model_type] = (model_data, loaded)
                    return loaded
        return None

    @staticmethod
    def friendly_name(file: str):
        if "http" in file:
            file = urlparse(file).path

        file = os.path.basename(file)
        model_name, extension = os.path.splitext(file)
        return model_name
