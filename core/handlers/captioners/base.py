from typing import Dict

import PIL.Image as Image


class BaseCaptioner:
    def __init__(self, config):
        self.config = config
        self._setup()

    def _setup(self):
        pass

    def caption(self, image: Image, params: Dict, unload: bool) -> str:
        raise NotImplementedError
