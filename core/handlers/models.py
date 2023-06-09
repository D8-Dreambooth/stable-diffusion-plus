import gc
import glob
import importlib
import logging
import os
import shutil
import traceback
from typing import List, Dict, Union
from urllib.parse import urlparse

import torch
from basicsr.utils.download_util import load_file_from_url
from huggingface_hub import snapshot_download

from core.dataclasses.model_data import ModelData
from core.handlers.directories import DirectoryHandler
from core.handlers.websocket import SocketHandler
from dreambooth.sd_to_diff import extract_checkpoint

logger = logging.getLogger(__name__)


# This class is a singleton used to easily move models in and out of CPU/GPU memory
# If you're relying on this instead of deleting loaded models, then it might be a good idea to check
# if they are currently on the desired device, and if not, move it there.
class ModelManager:
    _to_cpu_handlers = []
    _to_gpu_handlers = []
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance

    def register(self, to_cpu_method, to_gpu_method):
        self._to_cpu_handlers.append(to_cpu_method)
        self._to_gpu_handlers.append(to_gpu_method)

    def to_cpu(self):
        for handler in self._to_cpu_handlers:
            handler()

    def to_gpu(self):
        for handler in self._to_gpu_handlers:
            handler()


class ModelHandler:
    _instance = None
    _instances = {}
    models_path = []
    shared_path = None
    user_path = None
    protected_path = None
    socket_handler = None
    model_watcher = None
    loaded_models = {}
    listed_models = {}
    model_loaders = {}
    model_finders = {}
    load_params = {}
    user_name = None
    logger = None

    def __new__(cls, user_name=None, watcher=None):
        if cls._instance is None and watcher is not None:
            dir_handler = DirectoryHandler()
            models_path = dir_handler.get_directory("models")
            cls._instance = super(ModelHandler, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(f"{__name__}-shared")
            cls._instance.model_watcher = watcher
            cls._instance.models = {}
            cls._instance.loaded_models = {}
            cls._instance.models_path = models_path
            cls._instance.shared_path = dir_handler.get_shared_directory("models")
            cls._instance.socket_handler = SocketHandler()
            cls._instance.socket_handler.register("models", cls._instance.list_models)
            cls._instance.socket_handler.register("load_model", cls._instance._load_model)
            cls._instance.initialize_loaders()
            manager = ModelManager()
            manager.register(cls._instance.to_cpu, cls._instance.to_gpu)

        if user_name is not None:
            if user_name in cls._instances:
                return cls._instances[user_name]

            else:
                dir_handler = DirectoryHandler(user_name=user_name)
                models_path = dir_handler.get_directory("models")
                user_instance = super(ModelHandler, cls).__new__(cls)
                user_instance.logger = logging.getLogger(f"{__name__}-{user_name}")
                user_instance.shared_path = dir_handler.get_shared_directory("models")
                user_instance.protected_path = dir_handler.get_protected_directory("models")
                user_instance.user_path = dir_handler.get_user_directory("models")
                user_instance.models = {}
                user_instance.model_watcher = cls._instance.model_watcher
                user_instance.loaded_models = {}
                user_instance.models_path = models_path
                user_instance.socket_handler = SocketHandler()
                user_instance.socket_handler.register("models", user_instance.list_models, user_name)
                user_instance.socket_handler.register("load_model", user_instance._load_model, user_name)
                user_instance.user_name = user_name
                manager = ModelManager()
                manager.register(user_instance.to_cpu, user_instance.to_gpu)
                user_instance.initialize_loaders()
                cls._instances[user_name] = user_instance
                return user_instance
        else:
            return cls._instance

    async def list_models(self, msg):
        data = msg["data"]
        loaded_model = None
        model_json = []
        if "model_type" not in data:
            self.logger.warning(f"Invalid request: {data}")
            return {"message": "Invalid data."}
        else:
            model_type = data["model_type"]
            model_types = [model_type] if not "_" in model_type else model_type.split("_")
            for model_type in model_types:
                if model_type in self.model_finders:
                    model_list = await self.model_finders[model_type](data, self)
                else:
                    ext_include = None if "ext_include" not in data else data["ext_include"]
                    ext_exclude = None if "ext_exclude" not in data else data["ext_exclude"]
                    model_list = self.load_models(model_type=model_type, ext_include=ext_include,
                                                  ext_exclude=ext_exclude)

                self.listed_models[model_type] = model_list
                model_jsons = [model.serialize() for model in model_list]
                model_json.extend(model_jsons)
                if model_type in self.loaded_models:
                    model_data, _ = self.loaded_models[model_type]
                    loaded_model = model_data.hash
            return {"models": model_json, "loaded": loaded_model}

    async def find_model(self, model_type: str, value: Union[str, Dict]):
        if model_type in self.listed_models:
            models = self.listed_models[model_type]
        elif model_type in self.load_params:
            params = self.load_params[model_type]
            models = self.load_models(model_type, **params)
        else:
            self.logger.warning(f"Can't list models: {model_type}")
            models = self.load_models(model_type)

        for model in models:
            if isinstance(value, dict):
                if model.hash == value["hash"]:
                    return model
            else:
                if model.name == value or model.hash == value or model.display_name == value or model.path == value:
                    return model
        logger.debug(f"Model not found: {value}")
        return None

    async def _load_model(self, msg):
        data = msg["data"]
        try:
            md = ModelData("http")
            md.deserialize(data)
        except Exception as e:
            self.logger.warning(f"Can't deserialize: {data} {e}")
            return {"message": "Unable to deserialize data."}

        if "model_type" not in data:
            self.logger.warning(f"Invalid request: {data}")
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

        # Save these for later so when "refresh" is called, we can reload.
        if "_" in model_type:
            model_types = model_type.split("_")
        else:
            model_types = [model_type]
        for model_type in model_types:
            self.load_params[model_type] = {
                "model_url": model_url,
                "ext_include": ext_include,
                "ext_exclude": ext_exclude,
                "download_name": download_name
            }

            if "diffusers" == model_type:
                diff_dirs = self.load_diffusion_models("dreambooth" in model_type)
                for diff_dir in diff_dirs:
                    name = None
                    if "working" in diff_dir:
                        # Set model data.name to the parent directory of diff_dir
                        name = os.path.basename(os.path.dirname(diff_dir))
                    model_data = ModelData(diff_dir, name=name)
                    output.append(model_data)
                return output

            if ext_include is None:
                ext_include = []

            try:
                for mp in self.models_path:
                    model_path = os.path.join(mp, model_type)
                    if not os.path.exists(model_path):
                        os.makedirs(model_path)

                    for file in glob.iglob(model_path + '**/**', recursive=True):
                        full_path = file
                        if os.path.isdir(full_path):
                            continue
                        if os.path.islink(full_path) and not os.path.exists(full_path):
                            continue
                        if ext_exclude is not None and any([full_path.endswith(x) for x in ext_exclude]):
                            continue
                        if len(ext_include) != 0:
                            model_type, extension = os.path.splitext(file)
                            if extension not in ext_include:
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
                self.logger.warning(f"Exception: {e}")
                traceback.print_exc()
                pass

        return output

    def refresh(self, model_type: str, to_load=None, model_name=None):
        model_data = None
        if to_load:
            self.logger.debug(f"Reloading model from data: {to_load}")
            model_data = ModelData(to_load, name=model_name).__dict__
        msg = {
            "name": "reload_models",
            "model_type": model_type,
            "user": self.user_name,
            "to_load": model_data
        }
        logger.debug(f"Broadcasting: {msg}")
        self.socket_handler.queue.put_nowait(msg)

    def load_diffusion_models(self, load_dreambooth: bool = False) -> List[str]:
        model_directories = []
        target_directories = []
        for path in self.models_path:
            target_directories.append(os.path.join(path, "diffusers"))
            if load_dreambooth:
                target_directories.append(os.path.join(path, "dreambooth"))

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

        if len(output) == 0:
            dest_folder = os.path.join(self.models_path[1], "diffusers", "stable-diffusion-1-5")
            self.logger.info("No diffusion models found. Downloading default.")
            repo_id = "runwayml/stable-diffusion-v1-5"
            exclude_files = ['.gitattributes', 'Upload', 'v1-5-pruned*', 'README.md', 'Update', 'README.md', "*.bin"]

            snapshot_download(repo_id, revision=None, repo_type="model", cache_dir=None, local_dir=dest_folder,
                              local_dir_use_symlinks=False, ignore_patterns=exclude_files)
            output.append(dest_folder)

            self.refresh("diffusers")
        return output

    def register_loader(self, model_type, callback):
        if model_type not in self.model_loaders:
            self.model_loaders[model_type] = callback

    def register_finder(self, model_type: str, callback):
        if model_type not in self.model_finders:
            self.model_finders[model_type] = callback

    def load_model(self, model_type: str, model_data: ModelData, unload: bool = True):
        self.logger.debug(f"Loading model ({model_type})")
        if model_type in self.loaded_models:
            loaded_model_data, model = self.loaded_models[model_type]
            if model_data != loaded_model_data and unload:
                self.logger.debug(f"Unloading model...")
                del model
                del self.loaded_models[model_type]
                if torch.has_cuda:
                    torch.cuda.empty_cache()
                gc.collect()
            else:
                if torch.cuda.is_available():
                    model = model.to('cuda')
                return model

        # Convert stable-diffusion/checkpoints to diffusers
        if model_type == "stable-diffusion":
            target_model = os.path.join(self.models_path, "diffusers", os.path.basename(model_data.path))
            if os.path.exists(target_model):
                self.logger.info("Model already extracted.")
                return target_model

            self.logger.info("Converting sd model to diffusers.")

            try:
                results = extract_checkpoint("test", model_data.path, extract_ema=True, train_unfrozen=True)
                model_dir = results[1]
                if os.path.exists(model_dir):
                    diffusers_path = os.path.join(model_dir, "working")
                    if os.path.exists(diffusers_path):
                        dest_path = os.path.join(self.models_path, "diffusers")
                        os.makedirs(dest_path)
                        dest_path = os.path.join(self.models_path, "diffusers", os.path.basename(model_data.path))
                        if not os.path.exists(dest_path):
                            shutil.copytree(diffusers_path, dest_path)
                    shutil.rmtree(model_dir)

            except Exception as e:
                self.logger.warning(f"Couldn't extract checkpoint: {e}")
        else:
            if model_type not in self.model_loaders:
                self.logger.warning(f"No registered loader for model type: {model_type}")
            else:
                loaded = self.model_loaders[model_type](model_data)
                if loaded:
                    if torch.has_cuda:
                        try:
                            loaded = loaded.to("cuda")
                        except:
                            self.logger.debug("Couldn't load model to GPU.")

                    if torch.has_mps:
                        try:
                            loaded = loaded.to("ddp")
                        except:
                            self.logger.debug("Couldn't load model to DDP.")
                    if unload:
                        self.loaded_models[model_type] = (model_data, loaded)
                    return loaded
        return None

    def to_cpu(self):
        self.log_vram()
        for model_type, model in self.loaded_models.items():
            model_data, loaded_model = model[0], model[1]
            self.loaded_models[model_type] = (model_data, loaded_model.to("cpu"))
        try:
            gc.collect()
            torch.cuda.empty_cache()
            self.log_vram()
        except:
            pass

    def to_gpu(self):
        device = "cpu"
        if torch.has_cuda:
            device = "cuda"
        if torch.has_mps:
            device = "ddp"
        for model_type, model in self.loaded_models.items():
            model_data, loaded_model = model[0], model[1]
            self.loaded_models[model_type] = (model_data, loaded_model.to(device))
        try:
            gc.collect()
            torch.cuda.empty_cache()
        except:
            pass

    # A method to log the current/total VRAM usage
    def log_vram(self):
        if torch.has_cuda:
            self.logger.debug(f"Current VRAM usage: {torch.cuda.memory_allocated() / 1024 ** 3} GB")
            self.logger.debug(f"Total VRAM usage: {torch.cuda.memory_reserved() / 1024 ** 3} GB")
        else:
            self.logger.debug("No CUDA device detected.")

    @staticmethod
    def friendly_name(file: str):
        if "http" in file:
            file = urlparse(file).path

        file = os.path.basename(file)
        model_name, extension = os.path.splitext(file)
        return model_name
