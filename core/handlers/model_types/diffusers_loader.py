import logging
import os.path

import tomesd
import torch
from diffusers import DiffusionPipeline, UniPCMultistepScheduler, ControlNetModel, \
    StableDiffusionControlNetPipeline, StableDiffusionSAGPipeline

from diffusers.models.attention_processor import AttnProcessor2_0

from core.dataclasses.model_data import ModelData
from core.handlers.model_types.controlnet_processors import model_data as controlnet_data
from core.pipelines.pipeline_stable_diffusion_controlnet_sag import StableDiffusionControlNetSAGPipeline

logger = logging.getLogger(__name__)


def load_diffusers(model_data: ModelData):
    model_path = model_data.path
    if f"models{os.path.sep}dreambooth" in model_path and "working" not in model_path:
        logger.debug(f"Adding working to dreambooth model path: {model_path}")
        model_path = os.path.join(model_path, "working")

    controlnet_type = model_data.data["type"] if "type" in model_data.data else None
    if controlnet_type:
        return load_diffusers_controlnet(model_data)

    use_sag = model_data.data.get("use_sag", False)
    logger.debug(f"Use Sag: {use_sag}")
    pipeline = None
    if not os.path.exists(model_path):
        logger.debug(f"Unable to load model: {model_path}")
    else:
        try:
            if use_sag:
                pipeline = StableDiffusionSAGPipeline.from_pretrained(model_path, torch_dtype=torch.float16)
            else:
                pipeline = DiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float16)
            pipeline.enable_model_cpu_offload()
            pipeline.unet.set_attn_processor(AttnProcessor2_0())
            if os.name != "nt":
                pipeline.unet = torch.compile(pipeline.unet)
            pipeline.enable_xformers_memory_efficient_attention()
            pipeline.vae.enable_tiling()
            tomesd.apply_patch(pipeline, ratio=0.5)
            pipeline.scheduler.config["solver_type"] = "bh2"
            pipeline.scheduler = UniPCMultistepScheduler.from_config(pipeline.scheduler.config)

        except Exception as e:
            logger.warning(f"Exception loading pipeline: {e}")
    return pipeline


def load_diffusers_img2img(model_data: ModelData):
    model_path = model_data.path
    controlnet_type = model_data.data["type"] if "type" in model_data.data else None
    if controlnet_type:
        return load_diffusers_controlnet(model_data)

    load_sag = model_data.data.get("enable_sag", True)
    pipeline = None
    if not os.path.exists(model_path):
        logger.debug(f"Unable to load model: {model_path}")
    else:
        try:
            if load_sag:
                pipeline = StableDiffusionSAGPipeline.from_pretrained(model_path, torch_dtype=torch.float16)
            else:
                pipeline = DiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float16)
            pipeline.enable_model_cpu_offload()
            pipeline.unet.set_attn_processor(AttnProcessor2_0())
            if os.name != "nt":
                pipeline.unet = torch.compile(pipeline.unet)
            pipeline.enable_xformers_memory_efficient_attention()
            pipeline.vae.enable_tiling()
            pipeline.scheduler.config["solver_type"] = "bh2"
            pipeline.scheduler = UniPCMultistepScheduler.from_config(pipeline.scheduler.config)

        except Exception as e:
            logger.warning(f"Exception loading pipeline: {e}")
    return pipeline


def load_diffusers_inpaint(model_data: ModelData):
    model_path = model_data.path
    controlnet_type = model_data.data["type"] if "type" in model_data.data else None
    if controlnet_type:
        return load_diffusers_controlnet(model_data)

    load_sag = model_data.data.get("enable_sag", True)
    pipeline = None
    if not os.path.exists(model_path):
        logger.debug(f"Unable to load model: {model_path}")
    else:
        try:
            if load_sag:
                pipeline = StableDiffusionSAGPipeline.from_pretrained(model_path, torch_dtype=torch.float16)
            else:
                pipeline = DiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float16)
            pipeline.enable_model_cpu_offload()
            pipeline.unet.set_attn_processor(AttnProcessor2_0())
            if os.name != "nt":
                pipeline.unet = torch.compile(pipeline.unet)
            pipeline.enable_xformers_memory_efficient_attention()
            pipeline.vae.enable_tiling()
            pipeline.scheduler.config["solver_type"] = "bh2"
            pipeline.scheduler = UniPCMultistepScheduler.from_config(pipeline.scheduler.config)

        except Exception as e:
            logger.warning(f"Exception loading pipeline: {e}")
    return pipeline


def load_diffusers_controlnet(model_data: ModelData):
    model_path = model_data.path
    load_sag = model_data.data.get("enable_sag", True)
    pipeline = None
    if not os.path.exists(model_path):
        logger.debug(f"Unable to load model: {model_path}")
        return pipeline

    if "type" not in model_data.data:
        logger.debug("No controlnet type specified.")
        return pipeline

    controlnet_type = model_data.data["type"]
    controlnet_url = None
    for md in controlnet_data:
        if md["name"] == controlnet_type:
            controlnet_url = md["model_url"]
            break
    if not controlnet_url:
        logger.debug("No controlnet url found.")
        return pipeline

    try:
        controlnet = ControlNetModel.from_pretrained(controlnet_url, torch_dtype=torch.float16)
        if load_sag:
            pipeline = StableDiffusionControlNetSAGPipeline.from_pretrained(model_path, torch_dtype=torch.float16,
                                                                            controlnet=controlnet)
        else:
            pipeline = StableDiffusionControlNetPipeline.from_pretrained(model_path, torch_dtype=torch.float16,
                                                                         controlnet=controlnet)
        pipeline.enable_model_cpu_offload()
        pipeline.unet.set_attn_processor(AttnProcessor2_0())
        if os.name != "nt":
            pipeline.unet = torch.compile(pipeline.unet)
        pipeline.enable_xformers_memory_efficient_attention()
        pipeline.vae.enable_tiling()
        tomesd.apply_patch(pipeline, ratio=0.5)
        pipeline.scheduler.config["solver_type"] = "bh2"
        pipeline.scheduler = UniPCMultistepScheduler.from_config(pipeline.scheduler.config)

    except Exception as e:
        logger.warning(f"Exception loading pipeline: {e}")
    return pipeline


def register_function(model_handler):
    model_handler.register_loader("diffusers", load_diffusers)
    model_handler.register_loader("diffusers_inpaint", load_diffusers_inpaint)
    model_handler.register_loader("diffusers_img2img", load_diffusers_img2img)
