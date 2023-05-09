import asyncio
import logging
import os.path

import requests
import torch
from fastapi import FastAPI, Query
from huggingface_hub import snapshot_download
from starlette.responses import JSONResponse

from core.handlers.models import ModelHandler
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule
from core.modules.import_export.src.convert_original_stable_diffusion_to_diffusers import extract_checkpoint
from core.modules.import_export.src.extract_lora_from_model import extract_lora

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
        @app.get(f"/io/import")
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
        handler.register("extract_lora", self._extract_lora)

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
        output_path = dest_folder
        if from_hub:
            repo_id = model_url
            include_files = ["*.safetensors", "*.bin", "*.ckpt", "*.json", "*.txt", "*.yaml", "*.yml"]
            exclude_files = ["*.md", ".gitattributes"]
            if model_type == "diffusers":
                include_files = ["*.safetensors", "*.json", "*.txt", "*.yaml", "*.yml"]
                exclude_files = ["*-pruned.ckpt", "*-pruned.safetensors", "README.md", ".gitattributes", "*.bin",
                                 "*.ckpt"]
            snapshot_download(repo_id, revision=None, repo_type="model", cache_dir=None, local_dir=dest_folder,
                              local_dir_use_symlinks=False, allow_patterns=include_files, ignore_patterns=exclude_files)
        else:
            try:
                # Download the file from the URL?
                filename = model_url.split('/')[-1].replace(" ", "_")  # be careful with file names
                file_path = os.path.join(dest_folder, filename)
                output_path = os.path.abspath(file_path)
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
                    output_path = None
            except:
                logger.debug("Download failed: {}".format(model_url))
                output_path = None

        if output_path:
            mh.refresh(model_type, to_load=dest_folder)

    async def _extract_lora(self, request):
        logger.debug(f"Extract LoRA: {request}")
        user = request["user"] if "user" in request else None
        mh = ModelHandler(user_name=user)
        sh = StatusHandler(user_name=user)
        data = request["data"]
        model_src = data["src"]
        model_tuned = data["tuned"]
        src_model = await mh.find_model("diffusers", model_src)
        tuned_model = await mh.find_model("diffusers", model_tuned)
        precision = data["precision"]
        dim = data["network_dim"]
        conv_dim = data["conv_dim"]
        # Determine the device to use, based on if MPS or cuda and if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        sh.start(desc="Extracting LoRA", total=100)
        asyncio.create_task(extract_lora(src_model, tuned_model, mh, precision, dim, conv_dim, device))
        return {"name": "extraction_started", "message": "No model data provided."}


async def _import_model(data):
    msg_id = data["id"]
    logger.debug(f"Model import: {data}")
    model_data = data.get("data")
    user = None
    if not model_data:
        return {"name": "extraction_failed", "message": "No model data provided."}

    if "user" in data:
        user = data["user"]

    sh = StatusHandler(user_name=user)
    mh = ModelHandler(user_name=user)
    sh.update("status", f"Extracting model {model_data}...")
    await sh.send_async()
    model_name = model_data["name"]
    model_path = model_data["path"]
    is_512 = model_data.get("is_512", False)
    save_shared = model_data.get("save_shared", False)
    model_dir = os.path.dirname(model_path)
    config_file = None
    # Check if a yaml exists in the model_dir
    for file in os.listdir(model_dir):
        if file.endswith(".yaml"):
            config_file = os.path.join(model_dir, file)
            break
    model_dest = mh>model_path[1] if save_shared else mh.models_path[0]
    dest_dir = os.path.join(model_dest, "diffusers", model_name.replace(".safetensors", "") if ".safetensors" in model_name else model_name.replace(".ckpt", ""))
    extract_args = {
        "checkpoint_path": model_path,
        "dump_path": dest_dir,
        "original_config_file": config_file,
        "image_size": 512 if is_512 else 768,
        "extract_ema": True,
        "from_safetensors": "safetensors" in model_path,
        "to_safetensors": True,
        "status_handler": sh,
        "prediction_type": "epsilon" if is_512 else "v_prediction"
    }
    await asyncio.to_thread(extract_checkpoint, **extract_args)
    mh.refresh("diffusers")
    return {"name": "extraction_started", "message": "Extraction started.", "id": msg_id}
