from typing import Union, List

import torch
from PIL.Image import Image


class BaseUpscaler:
    def __init__(self, scale_factor: int, model_data=None):
        self.requires_latents = False
        self.model_data = model_data
        self.scale_factor = scale_factor

    def upscale(self, image: Union[Image, torch.FloatTensor], infer_settings, callback=None, callback_steps=5):
        raise NotImplementedError

    def unload(self, destroy: bool = False):
        pass
