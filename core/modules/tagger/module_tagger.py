import os
import logging

from fastapi import FastAPI

from core.handlers.file import FileHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


class ImportExportModule(BaseModule):

    def __init__(self):
        self.name: str = "Tagger"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)

    def _initialize_websocket(self, handler: SocketHandler):
        logger.debug("Initializing websocket for Tagger module...")
        super()._initialize_websocket(handler)
        handler.register("get_images", _list_images)
        handler.register("get_image", _get_image)
        handler.register("save_caption", _save_caption)


async def _list_images(data):
    logger.debug(f"Data: {data}")
    user = data["user"]
    actual_data = data["data"]
    fh = FileHandler(user_name=user)
    img_dir = actual_data["image_dir"]
    files = fh.get_dir_content(img_dir)
    data["data"] = {"files": files}
    return data


async def _get_image(data):
    logger.debug(f"Data: {data}")
    user = data["user"]
    fh = FileHandler(user_name=user)
    image = fh.get_file(data)
    data["data"] = {"image": image}
    return data


async def _save_caption(data):
    logger.debug(f"Data: {data}")
    user = data["user"]
    fh = FileHandler(user_name=user)
    tags = data["data"]["caption"]
    filename = data["data"]["path"]
    dest_dir = os.path.dirname(filename)
    filename = os.path.basename(filename)
    # Replace file extension with .txt
    filename = os.path.splitext(filename)[0] + ".txt"
    # Sanitize tags
    tag_items = tags.split(",")
    clean_tags = []
    for tag in tag_items:
        clean_tags.append(tag.strip().replace(" ", "_"))
    tags = ", ".join(clean_tags)
    fh.save_file(dest_dir, filename, tags.encode())
    return {"status": "Saved", "caption": tags}
