import json
import logging
import os
from typing import List, Dict

from fastapi import FastAPI, Depends, UploadFile, File, Form
from starlette.responses import JSONResponse

from core.handlers.file import FileHandler
from core.handlers.users import UserHandler, User, get_current_active_user
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


class FileBrowserModule(BaseModule):

    def __init__(self):
        self.name = "Files"
        self.path = os.path.abspath(os.path.dirname(__file__))
        self.user_handler = None
        super().__init__(self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self.user_handler = UserHandler()
        self._initialize_api(app)
        # self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
        @app.get(f"/files/files")
        async def list_files() -> JSONResponse:
            """
            foo
            @return:
            """
            return JSONResponse(content={"message": f"Job started."})

        @app.post("/files/upload")
        async def create_upload_files(
                files: List[UploadFile] = File(...),
                file_data: str = Form(...),
                current_user: User = Depends(get_current_active_user)
        ):
            logger.debug(f"Current user: {current_user}")
            user_name = None
            if current_user:
                user_name = current_user["name"]
            file_handler = FileHandler(user_name=user_name)
            user_dir = file_handler.user_dir

            for data in json.loads(file_data):
                dest_dir = os.path.abspath(os.path.join(user_dir, data["dest"]))
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)

            # Save files
            for i, file in enumerate(files):
                contents = await file.read()
                data = json.loads(file_data)[i]
                logger.debug(f"Saving file {data['name']} to {data['dest']}")
                file_handler.save_file(data["dest"], data["name"], contents)
            return {"message": "Files uploaded successfully"}
