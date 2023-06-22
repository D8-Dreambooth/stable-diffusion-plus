from typing import Union, List

import numpy as np
import torch
from upscalers import upscale, clear_on_device_caches

from core.handlers.model_types.diffusers_loader import load_diffusers
from core.helpers.upscalers.base_upscaler import BaseUpscaler


class Img2ImgUpscaler(BaseUpscaler):
    def __init__(self, scale_factor: int, model_data, pipeline):
        super().__init__(scale_factor)
        self.requires_latents = False
        model_data.data["pipeline"] = "Img2Img"
        self.pipeline = load_diffusers(model_data)
        self.pipeline.enable_xformers_memory_efficient_attention()
        self.pipeline.enable_attention_slicing()
        self.pipeline.vae.enable_tiling()
        self.pipeline.to("cpu")

    def upscale(self, image: Union[List[np.ndarray], np.ndarray], settings, callback=None, callback_steps=5):
        image = upscale(settings.postprocess_scaler, image, self.scale_factor)
        clear_on_device_caches()
        if torch.cuda.is_available():
            self.pipeline.to("cuda")
        generator = torch.Generator(device='cuda')

        generator.manual_seed(settings.seed)
        output = self.pipeline(
            prompt=settings.prompt,
            negative_prompt=settings.negative_prompt,
            image=image,
            num_inference_steps=settings.postprocess_steps,
            guidance_scale=settings.scale,
            generator=generator,
            callback=callback,
            strength=settings.postprocess_strength,
            callback_steps=5
        ).images[0]
        self.unload()
        return output

    def unload(self, destroy: bool = False):
        if destroy:
            del self.pipeline
        else:
            self.pipeline.to("cpu")