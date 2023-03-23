import logging
import os
from typing import List

from fastapi import FastAPI, Depends, UploadFile, File, Form
from starlette.responses import JSONResponse

from app.auth_helpers import oauth2_scheme, User, get_current_active_user
from core.handlers.file import FileHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


class FileBrowserModule(BaseModule):

    def __init__(self):
        self.name = "Files"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_api(app)
        # self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
        @app.get(f"/{self.name.lower()}/files")
        async def list_files() -> JSONResponse:
            """
            Check the current state of Dreambooth processes.
            foo
            @return:
            """
            return JSONResponse(content={"message": f"Job started."})

        @app.post("/files/upload")
        async def create_upload_files(
                files: List[UploadFile] = File(...),
                dir: str = Form(...),
                current_user: User = Depends(get_current_active_user)
        ):
            logger.debug(f"Current user: {current_user}")
            file_handler = FileHandler(user_name=current_user)

            for file in files:
                contents = await file.read()
                file_handler.save_file(dir, file.filename, contents)
            return {"message": "Files uploaded successfully"}




