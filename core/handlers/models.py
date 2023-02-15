import glob
import os
from typing import List
from urllib.parse import urlparse

from basicsr.utils.download_util import load_file_from_url
from starlette.websockets import WebSocket

from core.dataclasses.model_data import ModelData
from core.handlers.websockets import SocketHandler


class ModelHandler:
    _instance = None
    models_path = None
    socket_handler = None

    def __new__(cls, models_path=None):
        if cls._instance is None:
            cls._instance = super(ModelHandler, cls).__new__(cls)
            cls._instance.models = {}
            cls._instance.models_path = models_path
            cls._instance.socket_handler = SocketHandler()
            cls._instance.socket_handler.register("models", cls._instance.socket_models)
        if models_path:
            if not os.path.exists(models_path):
                os.makedirs(models_path)
                cls._instance.models_path = models_path
        return cls._instance

    async def socket_models(self, websocket: WebSocket, data):
        print(f"Socket model request received: {data}")
        if "model_type" not in data:
            print(f"Invalid request: {data}")
            return {"message":"Invalid data."}
        else:
            ext_include = None if "ext_include" not in data else data["ext_include"]
            ext_exclude = None if "ext_exclude" not in data else data["ext_exclude"]
            model_list = self.load_models(data["model_type"], ext_include=ext_include, ext_exclude=ext_exclude)
            print(f"Got model_list: {model_list}")
            model_json = [model.serialize() for model in model_list]
            return {"models": model_json}

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

        if ext_include is None:
            ext_include = []

        try:
            model_path = os.path.join(self.models_path, model_type)
            print(f"Checking: {model_path}")
            if not os.path.exists(model_path):
                os.makedirs(model_path)

            for file in glob.iglob(model_path + '**/**', recursive=True):
                full_path = file
                if os.path.isdir(full_path):
                    continue
                if os.path.islink(full_path) and not os.path.exists(full_path):
                    print(f"Skipping broken symlink: {full_path}")
                    continue
                if ext_exclude is not None and any([full_path.endswith(x) for x in ext_exclude]):
                    continue
                if len(ext_include) != 0:
                    model_type, extension = os.path.splitext(file)
                    if extension not in ext_include:
                        print(f"NO EXT: {extension}")
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

    @staticmethod
    def friendly_name(file: str):
        if "http" in file:
            file = urlparse(file).path

        file = os.path.basename(file)
        model_name, extension = os.path.splitext(file)
        return model_name
