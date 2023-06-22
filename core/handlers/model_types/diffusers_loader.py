import importlib
import inspect
import logging
import os.path
import re
import sys
import traceback

import tomesd
import torch
from diffusers import DiffusionPipeline, UniPCMultistepScheduler, ControlNetModel, \
    AutoencoderKL, StableDiffusionPipeline
from diffusers.models.attention_processor import AttnProcessor2_0
from safetensors.torch import load_file

from core.dataclasses.model_data import ModelData
from core.handlers.model_types.controlnet_processors import controlnet_models as controlnet_data

logger = logging.getLogger(__name__)


def initialize_pipeline(pipeline, loras, weight: float = 0.9):
    try:
        pipeline.unet.set_attn_processor(AttnProcessor2_0())
        if os.name != "nt":
            pipeline.unet = torch.compile(pipeline.unet)
    except:
        logger.debug("Unable to set attention processor.")

    try:
        pipeline.enable_xformers_memory_efficient_attention()
    except AttributeError:
        logger.debug("Unable to enable memory efficient attention.")

    if issubclass(pipeline.__class__, StableDiffusionPipeline):
        try:
            tomesd.apply_patch(pipeline, ratio=0.5)
        except:
            logger.debug("Unable to apply tomesd patch.")
        # If our pipeline inherits from StableDiffusionPipeline, we need to set the scheduler to UniPCMultistepScheduler
        try:
            logger.debug("Setting scheduler to UniPCMultistepScheduler.")
            pipeline.scheduler = UniPCMultistepScheduler.from_config(pipeline.scheduler.config)
            pipeline.scheduler.config["solver_type"] = "bh2"
        except:
            logger.debug("Unable to initialize scheduler.")

    if len(loras):
        for lora in loras:
            if "path" in lora:
                pipeline = apply_lora(pipeline, lora['path'], weight)
                logger.debug(f"Loading lora: {lora['name']}")
    return pipeline.to("cuda")


def initialize_controlnets(model_data):
    nets = []
    if "controlnet_type" not in model_data.data:
        return nets

    controlnet_type = model_data.data["controlnet_type"]
    if isinstance(controlnet_type, str):
        controlnet_type = [controlnet_type]
    from core.handlers.models import ModelHandler
    mh = ModelHandler()
    sp = mh.shared_path
    controlnet_dir = os.path.join(sp, "controlnet")
    for controlnet_name in controlnet_type:
        for mkey, md in controlnet_data.items():
            if mkey == controlnet_name:
                controlnet_url = md["model_url"]
                local_file = os.path.join(controlnet_dir, os.path.splitext(os.path.basename(md["model_file"]))[0])
                if os.path.exists(local_file):
                    logger.debug(f"Using local controlnet model: {local_file}")
                    controlnet_url = local_file

                controlnet = ControlNetModel.from_pretrained(controlnet_url, cache_dir=controlnet_dir,
                                                             torch_dtype=torch.float16)
                nets.append(controlnet)

    return nets


def load_diffusers(model_data: ModelData, existing_pipeline: DiffusionPipeline = None):
    model_path = model_data.path
    if f"models{os.path.sep}dreambooth" in model_path and "working" not in model_path:
        model_path = os.path.join(model_path, "working")
    pipeline_cls = model_data.data.get("pipeline", "DiffusionPipeline")
    pipeline = None
    if not os.path.exists(model_path):
        logger.debug(f"Unable to load model: {model_path}")
    else:
        try:
            nets = initialize_controlnets(model_data)
            pipe_args = {
                "torch_dtype": torch.float16
            }
            if "Onnx" in pipeline_cls:
                pipe_args["export"] = True
            if "vae" in model_data.data:
                pipe_args["vae"] = AutoencoderKL.from_pretrained(
                    model_data.data["vae"],
                    torch_dtype=torch.float16
                )
            if "Legacy" in pipeline_cls:
                pipe_args["safety_checker"] = None
                pipe_args["feature_extractor"] = None
                pipe_args["requires_safety_checker"] = False
            if len(nets):
                logger.debug(f"Loading {len(nets)} controlnets.")
                pipe_args["controlnet"] = nets
            if existing_pipeline is not None:
                # Add existing pipeline to args
                existing_components = existing_pipeline.components
                for key, value in existing_components.items():
                    pipe_args[key] = value

            logger.debug(f"Loading pipeline: {pipeline_cls} from {model_path}")
            # Instantiate pipeline using pipeline_cls string
            if pipeline_cls == "DiffusionPipeline" or pipeline_cls is None or pipeline_cls == "auto":
                src_pipe = DiffusionPipeline.from_pretrained(model_path, **pipe_args)
            else:
                pipe_obj = get_pipeline_cls(pipeline_cls)
                src_pipe = pipe_obj.from_pretrained(model_path, **pipe_args)

            pipeline = initialize_pipeline(src_pipe, loras=model_data.data.get("loras", []),
                                           weight=model_data.data.get("lora_weight", 0.9))
        except Exception as e:
            logger.warning(f"Exception loading pipeline: {e}")
            traceback.print_exc()
    return pipeline


def get_pipeline_cls(class_name):
    subclasses_params = get_pipeline_parameters()
    if class_name == "Default":
        return DiffusionPipeline
    for cls, params in subclasses_params.items():
        if cls == class_name:
            cls_name = params["cls"]
            modules = ['core.pipelines', 'diffusers.pipelines.stable_diffusion', "diffusers.pipelines.controlnet"]
            for module in modules:
                try:
                    mod = importlib.import_module(module)

                    for name, obj in inspect.getmembers(mod):
                        if inspect.isclass(obj) and name == cls_name:
                            pipe_class = getattr(sys.modules[module], cls_name)
                            return pipe_class

                except Exception as e:
                    logger.debug(f"Exception loading module {module}: {e} {traceback.format_exc()}")

    else:
        return None


def get_pipeline_parameters(ignore_keys=None, return_keys=False):
    filter_keys = [
        "Onnx",
        "Flax",
        "UnCLIP",
        "Pix2Pix",
        "Depth2Img",
        "ImageVariation",
        "LatentUpscale",
        "ModelEdit",
        "Excite",
        "Upscale",
        "UnCLIP"
    ]
    filter_pipes = ["StableDiffusionInpaintPipeline", "StableDiffusionLongPromptWeightingPipeline"]
    if ignore_keys is None:
        ignore_keys = ["num_images_per_prompt", "num_inference_steps", "output_type", "return_dict", "eta", "self",
                       "kwargs",
                       "callback", "callback_steps"]
    modules = ['core.pipelines', 'diffusers.pipelines.stable_diffusion', "diffusers.pipelines.controlnet"]
    subclasses_params = {}
    shared_keys = set()
    for module in modules:
        mod = importlib.import_module(module)
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj):
                if issubclass(obj, DiffusionPipeline) or issubclass(obj, StableDiffusionPipeline):
                    skip_class = False
                    if name in subclasses_params:
                        skip_class = True
                    for key in filter_keys:
                        if key in name:
                            skip_class = True
                    if name in filter_pipes:
                        skip_class = True
                    if skip_class:
                        continue
                    sig = inspect.signature(obj.__call__)
                    params = sig.parameters
                    subclasses_params[name] = {}
                    doc = obj.__call__.__doc__  # get the docstring
                    for param_name, param in params.items():
                        param_value = param.default if param.default is not param.empty else None
                        param_doc = re.search(f'{param_name} \((.*?)\):([^\(]*)(\([^\)]*\))?', doc)
                        description = param_doc.group(2).strip() if param_doc else None
                        min_max = re.search('Must be between (\d+(?:\.\d+)?), (\d+(?:\.\d+)?)',
                                            description) if description else None
                        min_value = float(min_max.group(1)) if min_max else 0
                        max_value = float(min_max.group(2)) if min_max else 1
                        # Set type param to type of default value
                        param_type = "unknown"
                        if param_value is not None:
                            param_type = type(param_value).__name__
                        if param_name in ignore_keys:
                            continue
                        if "image" in param_name:
                            param_type = "image"
                        if "prompt" in param_name and "embeds" not in param_name:
                            param_type = "str"
                            if param_value is None:
                                param_value = ""

                        if param_name == "height" or param_name == "width":
                            param_type = "int"
                            param_value = 512

                        param_data = {
                            "value": param_value,
                            "type": param_type,
                            "description": description,
                            "title": param_name.replace('_', ' ').title(),
                            "group": "pipeline",
                            "key": param_name
                        }
                        if param_type == "float" or param_type == "int":
                            if param_type == "int":
                                min_value = int(min_value)
                                max_value = int(max_value)
                            param_data["min"] = min_value
                            param_data["max"] = max_value
                        subclasses_params[name][param_name] = param_data

                    if not shared_keys:
                        # First time through, just set the shared keys to the parameters
                        shared_keys = set(subclasses_params[name].keys())
                    else:
                        # Get the intersection of the current parameters and the already found shared keys
                        shared_keys &= set(subclasses_params[name].keys())

    # Add the ignored keys to the set of shared keys
    shared_keys |= set(ignore_keys)

    # Remove the shared/ignored keys from each class's parameters
    for params in subclasses_params.values():
        for key in shared_keys:
            params.pop(key, None)

    keys = ["Default"]
    d_params = subclasses_params["StableDiffusionPipeline"]
    d_params["cls"] = "StableDiffusionPipeline"
    params = {"Default": d_params}
    for key in subclasses_params.keys():
        subkey = key.replace("Pipeline", "")
        subkey = subkey.replace("StableDiffusion", "")
        if subkey != "":
            keys.append(subkey)
            params[subkey] = subclasses_params[key]
            params[subkey]["cls"] = key
    if return_keys:
        return keys

    return params


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
