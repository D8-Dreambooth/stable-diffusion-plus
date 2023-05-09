import logging
import os.path
import traceback

import tomesd
import torch
from diffusers import DiffusionPipeline, UniPCMultistepScheduler, ControlNetModel, \
    StableDiffusionControlNetPipeline, StableDiffusionSAGPipeline, StableDiffusionPipeline

from diffusers.models.attention_processor import AttnProcessor2_0
from safetensors.torch import load_file

from core.dataclasses.model_data import ModelData
from core.handlers.model_types.controlnet_processors import model_data as controlnet_data
from core.pipelines.pipeline_stable_diffusion_controlnet_sag import StableDiffusionControlNetSAGPipeline
from lora_diffusion.lora import patch_pipe

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
    loras = model_data.data.get("loras", [])

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
            pipeline.vae.enable_slicing()
            tomesd.apply_patch(pipeline, ratio=0.5)
            pipeline.scheduler.config["solver_type"] = "bh2"
            pipeline.scheduler = UniPCMultistepScheduler.from_config(pipeline.scheduler.config)
            if len(loras):
                for lora in loras:
                    pipeline = apply_lora(pipeline, lora['path'])
                    logger.debug(f"Loading lora: {lora['name']}")
        except Exception as e:
            logger.warning(f"Exception loading pipeline: {e}")
            traceback.print_exc()
    return pipeline


def load_diffusers_img2img(model_data: ModelData):
    model_path = model_data.path
    controlnet_type = model_data.data["type"] if "type" in model_data.data else None
    if controlnet_type:
        return load_diffusers_controlnet(model_data)

    load_sag = model_data.data.get("enable_sag", True)
    loras = model_data.data.get("loras", [])
    logger.debug(f"Loras: {loras}")
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
            if len(loras):
                for lora in loras:
                    logger.debug(f"Loading lora: {lora['name']}")
                    pipeline.unet.load_attn_procs(lora['path'])
        except Exception as e:
            logger.warning(f"Exception loading pipeline: {e}")
            traceback.print_exc()
    return pipeline


def load_diffusers_inpaint(model_data: ModelData):
    model_path = model_data.path
    controlnet_type = model_data.data["type"] if "type" in model_data.data else None
    if controlnet_type:
        return load_diffusers_controlnet(model_data)

    load_sag = model_data.data.get("enable_sag", True)
    loras = model_data.data.get("loras", [])
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
            if len(loras):
                for lora in loras:
                    logger.debug(f"Loading lora: {lora['name']}")
                    pipeline.unet.load_attn_procs(lora['path'])

        except Exception as e:
            logger.warning(f"Exception loading pipeline: {e}")
            traceback.print_exc()
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


def apply_lora(pipeline, checkpoint_path, alpha=0.75):
    lora_prefix_unet = "lora_unet"
    lora_prefix_text_encoder = "lora_te"
    # load LoRA weight from .safetensors
    state_dict = load_file(checkpoint_path)

    visited = []
    errors = 0
    total = 0
    bad_keys = []
    # directly update weight in diffusers model
    for key in state_dict:
        try:
            if ".alpha" in key or key in visited:
                continue
            total += 1

            if "text" in key:
                layer_infos = key.split(".")[0].split(lora_prefix_text_encoder + "_")[-1].split("_")
                curr_layer = pipeline.text_encoder
            else:
                layer_infos = key.split(".")[0].split(lora_prefix_unet + "_")[-1].split("_")
                curr_layer = pipeline.unet

            temp_name = layer_infos.pop(0)
            while len(layer_infos) > -1:
                try:
                    curr_layer = curr_layer.__getattr__(temp_name)
                    if len(layer_infos) > 0:
                        temp_name = layer_infos.pop(0)
                    elif len(layer_infos) == 0:
                        break
                except Exception:
                    if len(temp_name) > 0:
                        temp_name += "_" + layer_infos.pop(0)
                    else:
                        temp_name = layer_infos.pop(0)

            pair_keys = []
            if "lora_down" in key:
                pair_keys.append(key.replace("lora_down", "lora_up"))
                pair_keys.append(key)
            else:
                pair_keys.append(key)
                pair_keys.append(key.replace("lora_up", "lora_down"))

            # update weight
            if len(state_dict[pair_keys[0]].shape) == 4:
                weight_up = state_dict[pair_keys[0]].to(torch.float32).reshape(state_dict[pair_keys[0]].shape[0], -1)
                weight_down = state_dict[pair_keys[1]].to(torch.float32).transpose(-1, -2).reshape(
                    state_dict[pair_keys[1]].shape[0], -1)

                # Calculate the reshaping dimensions for the output tensor
                out_channels, in_channels, kernel_height, kernel_width = curr_layer.weight.shape

                updated_weight = torch.matmul(weight_up, weight_down).reshape(out_channels, in_channels, kernel_height,
                                                                              kernel_width)
                curr_layer.weight.data += alpha * updated_weight
            else:
                weight_up = state_dict[pair_keys[0]].to(torch.float32)
                weight_down = state_dict[pair_keys[1]].to(torch.float32)
                curr_layer.weight.data += alpha * torch.matmul(weight_up, weight_down)

            # update visited list
            for item in pair_keys:
                visited.append(item)

        except Exception as e:
            errors += 1
            logger.debug(f"Exception loading LoRA key {key}: {e} {traceback.format_exc()}")
            bad_keys.append(key)

    logger.debug(f"LoRA loaded {total - errors} / {total} keys")
    logger.debug(f"BadKeys: {bad_keys}")
    return pipeline






def register_function(model_handler):
    model_handler.register_loader("diffusers", load_diffusers)
    model_handler.register_loader("diffusers_inpaint", load_diffusers_inpaint)
    model_handler.register_loader("diffusers_img2img", load_diffusers_img2img)
