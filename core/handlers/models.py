import gc
import glob
import importlib
import logging
import os
import shutil
from typing import List
from urllib.parse import urlparse

import torch
from basicsr.utils.download_util import load_file_from_url

from core.dataclasses.model_data import ModelData
from core.handlers.websockets import SocketHandler

logger = logging.getLogger(__name__)


class ModelHandler:
    _instance = None
    models_path = None
    socket_handler = None
    loaded_models = {}
    model_loaders = {}

    def __new__(cls, models_path=None):
        if cls._instance is None:
            cls._instance = super(ModelHandler, cls).__new__(cls)
            cls._instance.models = {}
            cls._instance.loaded_models = {}
            cls._instance.models_path = models_path
            cls._instance.socket_handler = SocketHandler()
            cls._instance.socket_handler.register("models", cls._instance.list_models)
            cls._instance.socket_handler.register("load_model", cls._instance.loadmodel)
            cls._instance.initialize_loaders()

        return cls._instance

    async def list_models(self, msg):
        data = msg["data"]
        logger.debug(f"Socket model request received: {data}")
        if "model_type" not in data:
            logger.debug(f"Invalid request: {data}")
            return {"message": "Invalid data."}
        else:
            ext_include = None if "ext_include" not in data else data["ext_include"]
            ext_exclude = None if "ext_exclude" not in data else data["ext_exclude"]
            model_list = self.load_models(data["model_type"], ext_include=ext_include, ext_exclude=ext_exclude)
            logger.debug(f"Got model_list: {model_list}")
            model_json = [model.serialize() for model in model_list]
            return {"models": model_json}

    async def loadmodel(self, msg):
        data = msg["data"]
        logger.debug(f"Socket model request received: {data}")
        try:
            md = ModelData("http")
            md.deserialize(data)
        except Exception as e:
            logger.debug(f"Can't deserialize: {data} {e}")
            return {"error": "Unable to deserialize data."}

        if "model_type" not in data:
            logger.debug(f"Invalid request: {data}")
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

        if model_type == "diffusers":
            logger.debug("Loading diffusion models??")
            diff_dirs = self.load_diffusion_models()
            for diff_dir in diff_dirs:
                output.append(ModelData(diff_dir))
            return output

        if ext_include is None:
            ext_include = []

        try:
            model_path = os.path.join(self.models_path, model_type)
            logger.debug(f"Checking: {model_path}")
            if not os.path.exists(model_path):
                os.makedirs(model_path)

            for file in glob.iglob(model_path + '**/**', recursive=True):
                full_path = file
                if os.path.isdir(full_path):
                    continue
                if os.path.islink(full_path) and not os.path.exists(full_path):
                    logger.debug(f"Skipping broken symlink: {full_path}")
                    continue
                if ext_exclude is not None and any([full_path.endswith(x) for x in ext_exclude]):
                    continue
                if len(ext_include) != 0:
                    model_type, extension = os.path.splitext(file)
                    if extension not in ext_include:
                        logger.debug(f"NO EXT: {extension}")
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

        except Exception:
            pass

        return output

    def load_diffusion_models(self, model_path=None):
        model_directories = []
        if not model_path:
            model_path = os.path.join(self.models_path, "diffusers")
        for root, dirs, files in os.walk(model_path):
            # Check if the current directory contains a "model_index.json" file
            if "model_index.json" in files:
                model_directories.append(root)
                # Stop searching this directory's subdirectories
                dirs[:] = []
            # Continue searching other directories
            else:
                for ck_dir in dirs:
                    subdir = os.path.join(root, ck_dir)
                    if os.path.isdir(subdir):
                        model_directories.extend(self.load_diffusion_models(subdir))
        output = []
        for md in model_directories:
            if md not in output:
                output.append(md)
        return output

    def register_loader(self, model_type, callback):
        if model_type not in self.model_loaders:
            logger.debug(f"Registered model loader: {model_type}")
            self.model_loaders[model_type] = callback

    def load_model(self, model_type: str, model_data: ModelData):
        logger.debug(f"We need to load: {model_data.serialize()}")
        if model_type in self.loaded_models:
            logger.debug(f"Unloading: {self.loaded_models[model_type]}")
            del self.loaded_models[model_type]
            if torch.has_cuda:
                torch.cuda.empty_cache()
            gc.collect()
        # Convert stable-diffusion/checkpoints to diffusers
        if model_type == "stable-diffusion":
            logger.debug("Convert sd model to diffusers.")
            target_model = os.path.join(self.models_path, "diffusers", os.path.basename(model_data.path))
            if os.path.exists(target_model):
                logger.debug("Model already extracted")
                return target_model
            from dreambooth.dreambooth.sd_to_diff import extract_checkpoint
            try:
                results = extract_checkpoint("test", model_data.path, extract_ema=True, train_unfrozen=True)
                model_dir = results[1]
                logger.debug(f"Model Dir: {model_dir}")
                if os.path.exists(model_dir):
                    logger.debug(f"We got something: {model_dir}")
                    diffusers_path = os.path.join(model_dir, "working")
                    if os.path.exists(diffusers_path):
                        logger.debug("Found the diffusers too.")
                        dest_path = os.path.join(self.models_path, "diffusers")
                        os.makedirs(dest_path)
                        dest_path = os.path.join(self.models_path, "diffusers", os.path.basename(model_data.path))
                        if os.path.exists(dest_path):
                            logger.debug("Model already exists!")
                        else:
                            shutil.copytree(diffusers_path, dest_path)
                            logger.debug("Diffusers extracted?")
                    shutil.rmtree(model_dir)

            except Exception as e:
                logger.debug(f"Couldn't extract checkpoint: {e}")
        else:
            if model_type not in self.model_loaders:
                logger.debug(f"No registered loader for model type: {model_type}")
            else:
                loaded = self.model_loaders[model_type](model_data)
                if loaded:
                    logger.debug(f"{model_type} model loaded.")
                    if torch.has_cuda:
                        try:
                            loaded = loaded.to("cuda")
                        except:
                            logger.debug("Couldn't load model to GPU.")

                    self.loaded_models[model_type] = loaded
                    return loaded
        return None

    @staticmethod
    def friendly_name(file: str):
        if "http" in file:
            file = urlparse(file).path

        file = os.path.basename(file)
        model_name, extension = os.path.splitext(file)
        return model_name
