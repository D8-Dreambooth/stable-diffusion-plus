import logging

from diffusers import StableDiffusionPipeline
from diffusers.pipelines.stable_diffusion import StableDiffusionPipelineOutput

logger = logging.getLogger(__name__)


class StableDiffusionHdVitronPipeline(StableDiffusionPipeline):
    def __call__(self, *args, image=None, **kwargs):
        if image is None:
            raise ValueError("Missing required argument: images")
        result = super().__call__(*args, **kwargs)
        if not isinstance(result, StableDiffusionPipelineOutput):
            raise TypeError(f"Expected {StableDiffusionPipelineOutput}, got {type(result)}")
        images = result.images
        for image in images:
            logger.debug(f"Image shape: {image.shape}")
