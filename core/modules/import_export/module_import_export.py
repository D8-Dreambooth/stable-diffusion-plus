import asyncio
import logging
import os.path

from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

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

