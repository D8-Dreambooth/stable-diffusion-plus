import asyncio
import base64
import os
import logging
from typing import Dict

import cv2
from PIL import Image
from deepface import DeepFace
from fastapi import FastAPI, Query
from fastapi.params import Depends
from starlette.responses import JSONResponse

from core.handlers.file import FileHandler
from core.handlers.images import ImageHandler
from core.handlers.status import StatusHandler
from core.handlers.users import User, get_current_active_user
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


# Rename this class to match your module name
class AnalyzeModule(BaseModule):

    def __init__(self):
        # Rename this variable to match your module name
        self.name: str = "Analyze Module"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.name, self.path)

    # This method is called when the module is loaded by the server
    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)
        self._initialize_api(app)

    # We use this to register websocket events from the client
    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("analyze", self._start_analyze)

    # We use this to register API endpoints
    def _initialize_api(self, app: FastAPI):
        @app.get(f"/analyze/analyzeImage")
        async def import_model(request, current_user: User = Depends(get_current_active_user)) -> JSONResponse:
            logger.debug(f"User: {current_user}")
            return JSONResponse(content={"message": f"Message received started."})

    async def _start_analyze(self, msg: Dict):
        logger.debug("Starting analyze...")
        user = msg.get("user", None)
        data = msg.get("data", None)
        if not data:
            return {"status": "Failure", "message": "No data provided."}

        image_handler = ImageHandler(user_name=user)
        status_handler = StatusHandler(user_name=user)
        path = data["path"]
        src_image = data["image"]
        images, image_data = image_handler.load_image(path, recurse=True)
        img_count = 1
        logger.debug("Analyzing images...")
        status_handler.start(len(images), "Analyzing images...")
        ranks_dict = {}
        logger.debug("Enumerating...")
        for image in images:
            logger.debug(f"Analyzing image {image}")
            status_handler.step(img_count)
            status_handler.update(items={"status": f"Analyzing image {img_count} of {len(images)}"})
            await status_handler.send_async()
            try:
                rank = DeepFace.verify(src_image, image)
                verified = rank["verified"]
                distance = rank["distance"]
                facial_areas = rank["facial_areas"]
                # Open Image from File
                img = cv2.imread(image)
                image_with_box = img.copy()
                for img_name, box in facial_areas.items():
                    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
                    cv2.rectangle(image_with_box, (x, y), (x + w, y + h), (0, 0, 255), 2)
                _, buffer = cv2.imencode('.png', image_with_box)
                image_data = base64.b64encode(buffer).decode('utf-8')
                status_handler.update(items={"status2": f"{rank}", "images": image_data})
                await status_handler.send_async()
                ranks_dict[f"image_{img_count}"] = {"path": path, "image_data": image_data, "distance": distance,
                                                    "verified": verified}
            except:
                pass
            img_count += 1

        # Always return JSON
        return {"status": "Analysis Complete", "ranks": ranks_dict}
