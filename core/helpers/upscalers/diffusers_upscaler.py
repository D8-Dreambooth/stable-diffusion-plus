from typing import Union

import torch
from PIL.Image import Image
from diffusers import StableDiffusionLatentUpscalePipeline

from core.helpers.upscalers.base_upscaler import BaseUpscaler


class Diffusers2xUpscaler(BaseUpscaler):
    def __init__(self, scale_factor: int, model_data=None):
        super().__init__(scale_factor)
        self.requires_latents = False
        model_id = "stabilityai/sd-x2-latent-upscaler"
        self.pipeline = StableDiffusionLatentUpscalePipeline.from_pretrained(model_id, torch_dtype=torch.float16)
        self.pipeline.enable_xformers_memory_efficient_attention()
        self.pipeline.to("cpu")

    def upscale(self, image: Union[Image, torch.FloatTensor], settings, callback=None, callback_steps=5):
        if torch.cuda.is_available():
            self.pipeline.to("cuda")
        generator = torch.Generator(device='cuda')
        generator.manual_seed(settings.seed)
        target_width = int(image.width * self.scale_factor)
        target_height = int(image.height * self.scale_factor)
        # Downscale image so that the outputs size is the input image dims * scale factor
        image = image.resize((target_width // 2, target_height // 4))
        out_image = self.pipeline(
            prompt=settings.prompt,
            image=image,
            num_inference_steps=20,
            guidance_scale=0,
            generator=generator,
            callback=callback,
            callback_steps=callback_steps
        ).images[0]
        self.unload()
        return out_image

    def unload(self, destroy: bool = False):
        if destroy:
            del self.pipeline
        else:
            self.pipeline.to("cpu")
        pass
