import logging
import os.path

import torch
from diffusers import DiffusionPipeline, DEISMultistepScheduler, UniPCMultistepScheduler
from diffusers.models.cross_attention import AttnProcessor2_0

from core.dataclasses.model_data import ModelData

logger = logging.getLogger(__name__)


def load_diffusers(model_data: ModelData):
    model_path = model_data.path
    pipeline = None
    if not os.path.exists(model_path):
        logger.debug(f"Unable to load model: {model_path}")
    else:
        try:
            pipeline = DiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float16)
            pipeline = pipeline.to("cuda")
            pipeline.unet.set_attn_processor(AttnProcessor2_0())
            pipeline.unet = torch.compile(pipeline.unet)
            # pipeline.enable_xformers_memory_efficient_attention()
            pipeline.vae.enable_tiling()
            pipeline.scheduler.config["solver_type"] = "bh2"
            pipeline.scheduler = UniPCMultistepScheduler.from_config(pipeline.scheduler.config)
        except Exception as e:
            logger.warning(f"Exception loading pipeline: {e}")
    return pipeline


def register_function(model_handler):
    model_handler.register_loader("diffusers", load_diffusers)
