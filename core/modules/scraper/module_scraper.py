import logging
import os

from fastapi import FastAPI

from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule
from core.modules.scraper.src.google_images_download import scrape_images
from core.modules.scraper.src.scraper_config import ScraperConfig

logger = logging.getLogger(__name__)


# Rename this class to match your module name
class ScraperModule(BaseModule):

    def __init__(self):
        # Rename this variable to match your module name
        self.name: str = "Scraper"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__("scraper", self.name, self.path)

    # This method is called when the module is loaded by the server
    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)
        # self._initialize_api(app)

    # We use this to register websocket events from the client
    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("get_scraper_params", self._get_scraper_params)
        handler.register("scrape_images", self._scrape)

    @staticmethod
    async def _get_scraper_params(data):
        params = ScraperConfig()
        # Always return JSON
        return {"params": params.get_params()}

    async def _scrape(self, data):
        user_params = data["data"]["params"]
        user = data["user"] if "user" in data else None
        params = ScraperConfig(**user_params)
        paths, errors = scrape_images(params, user)
        # Always return JSON
        return {"images": paths, "errors": errors}
