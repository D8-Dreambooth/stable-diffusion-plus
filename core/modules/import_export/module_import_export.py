import asyncio
import logging
import os.path

import requests
from fastapi import FastAPI, Query
from huggingface_hub import snapshot_download
from starlette.responses import JSONResponse

from core.handlers.models import ModelHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule


logger = logging.getLogger(__name__)


class ImportExportModule(BaseModule):

    def __init__(self):
        self.name: str = "Import/Export"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_api(app)
        self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
        @app.get(f"/{self.name}/import")
        async def import_model(
                api_key: str = Query("", description="If an API key is set, this must be present.", )) -> \
                JSONResponse:
            """
            Check the current state of Dreambooth processes.
            foo
            @return:
            """
            return JSONResponse(content={"message": f"Job started."})

    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("extract_checkpoint", _import_model)
        handler.register("download_model", self._download_model)

    async def _download_model(self, request):
        user = request["user"] if "user" in request else None
        mh = ModelHandler(user_name=user)
        data = request["data"]
        model_url = data["url"]
        model_type = data["model_type"]
        model_name = data["name"] if "name" in data else None
        if not model_name:
            model_name = model_url.split("/")[-1]
            if "http" in model_url:
                model_name = model_name.split(".")[0]
        models_dir = os.path.join(mh.models_path[1], model_type)
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        from_hub = True
        if "http" in model_url and "huggingface" not in model_url:
            from_hub = False

        dest_folder = os.path.join(models_dir, model_name)

        if from_hub:
            repo_id = model_url
            include_files = ["*.safetensors", "*.bin", "*.ckpt", "*.json", "*.txt", "*.yaml", "*.yml"]
            exclude_files = ["*.md", ".gitattributes"]
            if model_type == "diffusers":
                include_files = ["*.safetensors", "*.json", "*.txt", "*.yaml", "*.yml"]
                exclude_files = ["*-pruned.ckpt", "*-pruned.safetensors", "README.md", ".gitattributes", "*.bin", "*.ckpt"]
            snapshot_download(repo_id, revision=None, repo_type="model", cache_dir=None, local_dir=dest_folder,
                              local_dir_use_symlinks=False, allow_patterns=include_files, ignore_patterns=exclude_files)
        else:
            try:
                # Download the file from the URL?
                filename = model_url.split('/')[-1].replace(" ", "_")  # be careful with file names
                file_path = os.path.join(dest_folder, filename)

                r = requests.get(model_url, stream=True)
                if r.ok:
                    logger.debug("saving to", os.path.abspath(file_path))
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024 * 8):
                            if chunk:
                                f.write(chunk)
                                f.flush()
                                os.fsync(f.fileno())
                else:  # HTTP status code 4XX/5XX
                    logger.debug("Download failed: status code {}\n{}".format(r.status_code, r.text))
            except:
                logger.debug("Download failed: {}".format(model_url))

        mh.refresh(model_type)


async def _import_model(data):
    msg_id = data["id"]
    logger.debug(f"Model import: {data}")
    model_data = data["data"] if "data" in data else None
    if model_data:
        from dreambooth.sd_to_diff import extract_checkpoint
        model_name = model_data["name"]
        model_path = model_data["path"]
        is_512 = model_data["is_512"] if "is_512" in model_data else False
        asyncio.create_task(extract_checkpoint(model_name, model_path, is_512=is_512, from_hub=False))
    return {"name": "extraction_started", "message": "Extraction started.", "id": msg_id}

