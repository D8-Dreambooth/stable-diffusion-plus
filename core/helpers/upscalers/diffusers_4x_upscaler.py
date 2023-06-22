import torch
from diffusers import StableDiffusionUpscalePipeline

from core.helpers.upscalers.base_upscaler import BaseUpscaler


class Diffusers4xUpscaler(BaseUpscaler):
    def __init__(self, scale_factor: int, model_data=None):
        super().__init__(scale_factor)
        self.requires_latents = True
        model_id = "stabilityai/stable-diffusion-x4-upscaler"
        self.pipeline = StableDiffusionUpscalePipeline.from_pretrained(model_id, revision="fp16",
                                                                       torch_dtype=torch.float16)
        self.pipeline.enable_xformers_memory_efficient_attention()
        self.pipeline.to("cpu")

    def upscale(self, image, settings, callback=None, callback_steps=5):
        if torch.cuda.is_available():
            self.pipeline.to("cuda")
        generator = torch.Generator(device='cuda')
        generator.manual_seed(settings.seed)
        target_width = int(image.width * self.scale_factor)
        target_height = int(image.height * self.scale_factor)
        # Downscale image so that the outputs size is the input image dims * scale factor
        image = image.resize((target_width // 4, target_height // 4))
        output = self.pipeline(
            prompt=settings.prompt,
            image=image,
            callback=callback,
            callback_steps=5
        ).images[0]
        self.unload()
        return output

    def unload(self, destroy: bool = False):
        if destroy:
            del self.pipeline
        else:
            self.pipeline.to("cpu")
