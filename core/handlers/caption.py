import inspect
import logging
import os
from importlib import import_module
from typing import Dict

from PIL import Image

from core.helpers import BaseCaptioner

logger = logging.getLogger(__name__)


class CaptionHandler:
    captioners = {}

    def caption_image(self, image: Image, captioner: str, params: Dict, unload: bool = True):
        self.list_captioners()
        if captioner not in self.captioners:
            logger.error(f"Captioner {captioner} not found.")
            return ""
        return self.captioners[captioner].caption(image, params, unload)

    def list_captioners(self):
        captioner_dir = os.path.join(os.path.dirname(__file__), "helpers/captioners")
        for file in os.listdir(captioner_dir):
            if file.endswith(".py"):
                name = file[:-3]
                if name != "__init__" and name != "base":
                    # Import the module and find the Captioner class
                    module = import_module(f"{__name__}.captioners.{name}")
                    for member_name in dir(module):
                        member = getattr(module, member_name)
                        if (
                                inspect.isclass(member)
                                and issubclass(member, BaseCaptioner)
                                and member != BaseCaptioner
                        ):
                            # Initialize the Captioner class and store it in self.captioners
                            if name not in self.captioners:
                                self.captioners[name] = member()

        return self.captioners
