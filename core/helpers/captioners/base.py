from typing import Dict

import PIL.Image as Image
import torch

from core.handlers.models import ModelManager


class BaseCaptioner:
    model = None
    processor = None
    device = None

    def __init__(self, config=None):
        self.config = config
        ModelManager().register(self._to_cpu, self._to_gpu)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._setup()

    def _setup(self):
        pass

    def _to_cpu(self):
        if self.model:
            self.model = self.model.to("cpu")
        if self.processor:
            try:
                self.processor = self.processor.to("cpu")
            except:
                pass

    def _to_gpu(self):
        if self.model:
            self.model = self.model.to(self.device)
        if self.processor:
            try:
                self.processor = self.processor.to(self.device)
            except:
                pass

    def caption(self, image: Image, params: Dict = None, unload: bool = False) -> str:
        raise NotImplementedError
