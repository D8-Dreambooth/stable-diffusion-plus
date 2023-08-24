import base64
import decimal
import importlib
import inspect
import json
import logging
import pkgutil
import re

import upscalers
from diffusers.schedulers import KarrasDiffusionSchedulers

import core.helpers.upscalers
from io import BytesIO
from typing import Dict, Union, List, Optional

from PIL import Image
from pydantic import Field, BaseModel

from core.dataclasses.model_data import ModelData
from core.handlers.model_types.diffusers_loader import get_pipeline_parameters
from core.helpers.upscalers.base_upscaler import BaseUpscaler
from core.modules.infer.src.prompt_magic import PromptHelper

logger = logging.getLogger(__name__)


def list_upscalers():
    available = upscalers.available_models()
    if "SwinIR 4x" in available:
        available.remove("SwinIR 4x")
        available.append("SwinIR_4x")
    return available


def list_characters():
    results = [""]
    ph = PromptHelper()
    if ph.llm is not None:
        chars = ph.llm.list_characters()
        logger.debug(f"Chars: {chars}")
        print(f"Chars: {chars}")
        results.extend(chars)
    else:
        logger.warning("Unable to load LLM.")
    return results


def list_postprocessors():
    postprocessors = []

    package = core.helpers.upscalers
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f'{package.__name__}.{modname}')
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseUpscaler) and obj != BaseUpscaler:
                postprocessors.append(name)

    return postprocessors


def list_schedulers():
    scheduler_names = [scheduler.name for scheduler in KarrasDiffusionSchedulers]
    return scheduler_names


class InferSettings(BaseModel):
    pipelines = get_pipeline_parameters()
    processors = list_postprocessors()

    # Models
    model: Dict = Field("None", description="Model data.", title="Model", group="Model",
                        custom_type="diffusers_modelSelect")
    vae: Optional[Dict] = Field(None, description="VAE.", title="VAE", group="Model", custom_type="vae_modelSelect",
                                advanced=True)

    # Inference
    pipeline: str = Field("auto", description="Pipeline.", title="Pipeline", group="General",
                          choices=get_pipeline_parameters(None, True),
                          advanced=True)
    num_images: int = Field(1, description="Number of images.", title="Num Images", ge=1, le=10000, group="General")
    prompt: str = Field("", description="Prompt.", title="Prompt", group="General")
    negative_prompt: str = Field("", description="Negative prompt.", title="Negative Prompt", group="General")

    width: int = Field(512, description="Width.", title="Width", ge=8, multiple_of=8, le=4096, group="General")
    height: int = Field(512, description="Height for inference.", title="Infer Height", ge=8, multiple_of=8, le=4096,
                        group="General")
    scheduler: str = Field("UniPCMultistepScheduler", description="Scheduler.", title="Scheduler", group="Advanced",
                           choices=list_schedulers(), advanced=True)
    batch_size: int = Field(1, description="Batch size.", title="Batch Size", gt=0, le=1000, group="Advanced",
                            advanced=True)
    apply_tomesd: bool = Field(False, description="Apply TomeSD.", title="Apply TomeSD", group="Advanced",
                               advanced=True)
    tomesd_scale: float = Field(0.5, description="TomeSD scale.", title="TomeSD Scale", ge=0.0, le=1.0,
                                multiple_of=0.1, group="Advanced", advanced=True)
    pipeline_settings: Dict = Field({}, description="Pipeline settings.", title="Pipeline Settings", group="Advanced",
                                    custom_type=None)
    scale: float = Field(7.5, description="Scale.", title="Scale", ge=0.0, le=100.0, multiple_of=0.1, group="Advanced",
                         advanced=True)
    seed: int = Field(-1, description="Seed.", title="Seed", ge=-1, group="Advanced", advanced=True)
    steps: int = Field(30, description="Steps.", title="Steps", ge=1, le=10000, group="Advanced", advanced=True)

    image: Optional[str] = Field(None, description="Image for inference.", title="Infer Image", group="Inpaint",
                                 advanced=True)
    use_batch_image: Optional[bool] = Field(False, description="Use batch image.", title="Use Batch Image",
                                            group="Inpaint", advanced=True)
    batch_image_path: Optional[str] = Field(None, description="Batch image path.", title="Batch Image Path",
                                            group="Inpaint", advanced=True, custom_type="fileBrowser")
    mask: Optional[str] = Field(None, description="Mask for inference.", title="Infer Mask", group="Inpaint",
                                custom_type="none")
    inpaint_masked: bool = Field(True,
                                 description="Enable to inpaint the masked area. Disable to inpaint non-masked areas.",
                                 title="Invert Mask", group="Inpaint",
                                 advanced=True)
    inpaint_mask_radius: int = Field(10, description="Radius of inpainting mask in pixels.",
                                     title="Inpaint Mask Radius", ge=0,
                                     le=100, group="Inpaint", advanced=True)
    inpaint_fill_mode: str = Field("noise", description="Inpaint fill mode.", title="Inpaint Fill Mode",
                                   group="Inpaint", choices=["noise", "original"], advanced=True)
    use_input_resolution: bool = Field(True, description="Use input resolution.", title="Use Input Resolution",
                                       group="Inpaint", advanced=True)
    scale_mode: str = Field("scale", description="Scale mode for inference.", title="Infer Scale Mode",
                            group="Inpaint", choices=["scale", "stretch", "contain"], advanced=True)
    # Preprocessing
    # def improve_prompt(self, add: str = "", filter: str = "", prompt_per_image: int = 1,
    # character: str = "default", max_tokens: int = 150):
    preprocess: bool = Field(False, description="Preprocess.", title="Preprocess", group="Preprocessing",
                             advanced=True,
                             toggle_fields=["preprocess_add", "preprocess_filter", "preprocess_character"
                                                                                   "preprocess_max_tokens",
                                            "preprocess_prompts_per_image"])
    preprocess_add: str = Field("", title="Add to Prompt",
                                description="A string or comma-separated list of strings to add to the prompt.",
                                group="Preprocessing",
                                advanced=True)
    preprocess_filter: str = Field("", title="Filter",
                                   description="A string or comma-separated list of strings to remove from the prompt.",
                                   group="Preprocessing", advanced=True)
    preprocess_character: str = Field("default", title="Character",
                                      description="The character/persona to use for prompt generation.",
                                      group="Preprocessing", choices=list_characters(), advanced=True)
    preprocess_max_tokens: int = Field(150, title="Max Tokens",
                                       description="The maximum number of tokens to add to the prompt.",
                                       ge=10, le=1000, group="Preprocessing", advanced=True)
    preprocess_prompts_per_image: int = Field(1, title="Prompts Per Image",
                                              description="Number of 'modified' prompts to generate per image.", ge=1,
                                              le=100,
                                              group="Preprocessing", advanced=True)
    # Postprocessing
    postprocess: bool = Field(False, description="Postprocess.", title="Postprocess", group="Postprocessing",
                              advanced=True,
                              toggle_fields=["postprocess_mode", "postprocess_scale", "postprocess_steps",
                                             "postprocess_scaler", "postprocess_strength"])
    postprocess_scaler: str = Field("Lanczos", description="Postprocess scaler.", title="Postprocess Scaler",
                                    choices=list_upscalers(), group="Postprocessing", advanced=True)
    postprocess_scale: float = Field(1.0, description="Postprocess scale.", title="Postprocess Scale", ge=0.0,
                                     le=10.0, group="Postprocessing", advanced=True)
    postprocess_steps: int = Field(60, description="Postprocess steps.", title="Postprocess Steps", ge=1, le=10000,
                                   group="Postprocessing", advanced=True)
    postprocess_strength: float = Field(0.4, description="Postprocess strength.", title="Postprocess Strength",
                                        ge=0.0, le=1.0, multiple_of=0.01, group="Postprocessing", advanced=True)
    # Controlnet
    controlnet_type: Optional[str] = Field(None, description="ControlNet type.", title="ControlNet Type",
                                           group="ControlNet", custom_type="controlnet_modelSelect", advanced=True)
    controlnet_preprocess: bool = Field(True, description="ControlNet preprocess.", title="ControlNet Preprocess",
                                        group="ControlNet")

    controlnet_batch: bool = Field(False, description="ControlNet batch.", title="Batch Input", group="ControlNet",
                                   toggle_fields=["controlnet_batch_dir", "controlnet_batch_find",
                                                  "controlnet_batch_replace", "controlnet_batch_use_prompt"])
    controlnet_image: Optional[str] = Field(None, description="ControlNet image.", title="ControlNet Image",
                                            group="ControlNet", custom_type="imageEditor")
    use_control_resolution: bool = Field(True, description="Use control resolution.", title="Use Control Resolution",
                                         group="ControlNet")
    controlnet_scale_mode: str = Field("scale", description="ControlNet scale mode.", title="ControlNet Scale Mode",
                                       group="ControlNet", choices=["scale", "other_choice1", "other_choice2"])

    controlnet_mask: Optional[str] = Field(None, description="ControlNet mask.", title="ControlNet Mask",
                                           group="ControlNet", custom_type="none")
    controlnet_batch_dir: Optional[str] = Field(None, description="ControlNet batch directory.",
                                                title="ControlNet Batch Directory", group="ControlNet",
                                                custom_type="fileBrowser")
    controlnet_batch_find: str = Field("", description="ControlNet batch find.", title="ControlNet Batch Find",
                                       group="ControlNet")
    controlnet_batch_replace: str = Field("", description="ControlNet batch replace.", title="ControlNet Batch Replace",
                                          group="ControlNet")
    controlnet_batch_use_prompt: str = Field(True, description="ControlNet batch use prompt.",
                                             title="ControlNet Batch Use Prompt", group="ControlNet")

    # Loras
    lora_weight: float = Field(0.9, description="LoRA weight.", title="LoRA Weight", ge=0.0, le=1.0, multiple_of=0.01,
                               group="Loras")
    loras: Optional[List[Dict]] = Field(None, description="List of LoRAs.", title="LoRAs", group="Loras",
                                        custom_type="lora_modelSelect")

    def __init__(self, data: Dict):
        super().__init__(**data)
        for key, value in data.items():
            if key == "model":
                md = ModelData(value["path"])
                md.deserialize(value)
                value = md
                # Convert dict to ModelData class here
            elif key == "mask" or key == "image":
                # Load image from base64 and verify it's got data
                if "data:image/png" in value:
                    img_data = re.sub('^data:image/.+;base64,', '', value)
                    # Convert base64 data to bytes
                    img_bytes = base64.b64decode(img_data)
                    if len(img_bytes) == 0:
                        print("Empty image data")
                        value = None
            else:
                attribute_type = type(getattr(self, key, None))
                if attribute_type is int or attribute_type is float or attribute_type is complex or attribute_type is decimal.Decimal:
                    try:
                        value = attribute_type(value)
                    except (ValueError, TypeError):
                        pass
                elif attribute_type is str:
                    try:
                        value = attribute_type(value)
                    except (ValueError, TypeError):
                        pass
                elif attribute_type is bool:
                    if isinstance(value, str):
                        if value.lower() == 'true':
                            value = True
                        elif value.lower() == 'false':
                            value = False
                        else:
                            pass
                    elif isinstance(value, bool):
                        setattr(self, key, value)
                        pass
                    elif value is None:
                        value = False
                else:
                    pass
            setattr(self, key, value)

    def from_prompt_data(self, prompt_data):
        for key, value in prompt_data.items():
            try:
                getattr(self, key)
                setattr(self, key, value)
                continue
            except AttributeError:
                pass
            if key == "resolution":
                if isinstance(value, tuple) and len(value) == 2:
                    self.width, self.height = value

    def get_controlnet_image(self) -> Union[Image.Image, None]:
        value = self.controlnet_image
        if value is not None:
            # Load image from base64
            if "data:image/png" in value:
                img_data = re.sub('^data:image/.+;base64,', '', value)
                # Convert base64 data to bytes
                img_bytes = base64.b64decode(img_data)
                if len(img_bytes) == 0:
                    print("Empty image data")
                    return None

                out_img = Image.open(BytesIO(img_bytes))
                logging.getLogger(__name__).debug(f"Loaded controlnet image with size {out_img.size}")
                return out_img

    def get_controlnet_mask(self) -> Union[Image.Image, None]:
        value = self.controlnet_mask
        if value is not None:
            # Load image from base64
            if "data:image/png" in value:
                img_data = re.sub('^data:image/.+;base64,', '', value)
                # Convert base64 data to bytes
                img_bytes = base64.b64decode(img_data)
                if len(img_bytes) == 0:
                    print("Empty image data")
                    return None
                return Image.open(BytesIO(img_bytes))

    def get_infer_image(self) -> Union[Image.Image, None]:
        value = self.image
        if value is not None:
            # Load image from base64
            if "data:image/png" in value:
                img_data = re.sub('^data:image/.+;base64,', '', value)
                # Convert base64 data to bytes
                img_bytes = base64.b64decode(img_data)
                if len(img_bytes) == 0:
                    print("Empty image data")
                    return None
                return Image.open(BytesIO(img_bytes))

    def get_infer_mask(self) -> Union[Image.Image, None]:
        value = self.mask
        if value is not None:
            # Load image from base64
            if "data:image/png" in value:
                img_data = re.sub('^data:image/.+;base64,', '', value)
                # Convert base64 data to bytes
                img_bytes = base64.b64decode(img_data)
                if len(img_bytes) == 0:
                    print("Empty image data")
                    return None
                return Image.open(BytesIO(img_bytes))

    def get_model(self):
        if isinstance(self.model, ModelData):
            return self.model
        elif isinstance(self.model, dict):
            if self.model.get("path") is None:
                return None
            return ModelData(self.model["path"])

    def get_params(self):
        tc_fields = {}
        keys = []
        for f, data in self.__fields__.items():
            if f == "pipelines" or f == "controlnets":
                tc_fields[f] = getattr(self, f)
                continue
            value = getattr(self, f)
            try:
                json.dumps(value)
            except TypeError:
                continue
            field_dict = {}

            for prop in ['default', 'description', 'title', 'ge', 'le', 'gt', 'lt', 'multiple_of']:
                if hasattr(data.field_info, prop):
                    value = getattr(data.field_info, prop)
                    # Check if the property is JSON serializable
                    if value is None:
                        continue
                    try:
                        json.dumps(value)
                        if prop == "ge":
                            prop = "min"
                        elif prop == "le":
                            prop = "max"
                        elif prop == "gt":
                            prop = "min"
                            value = value + 1
                        elif prop == "lt":
                            prop = "max"
                            value = value - 1
                        elif prop == "multiple_of":
                            prop = "step"
                        field_dict[prop] = value
                    except TypeError:
                        pass

            field_dict['value'] = getattr(self, f)
            field_dict['type'] = data.outer_type_.__name__

            # Check if 'choices' is in 'extras'
            extra_fields = ["choices", "custom_type", "group", "toggle_fields", "advanced"]
            if hasattr(data.field_info, "extra"):
                extras = getattr(data.field_info, "extra")
                for extra in extra_fields:
                    if extra in extras:
                        field_dict[extra] = extras[extra]
            keys.append(f)
            tc_fields[f] = field_dict
        tc_fields['keys'] = keys
        return tc_fields

    def as_dict(self):
        ignore_keys = ["pipelines", "processors", "pipe_keys"]
        out_dict = {}
        for k, v in self.__dict__.items():
            try:
                if "image" in k or k in ignore_keys:
                    continue
                if k == "model":
                    v = v.__dict__
                val = json.dumps(v)
                out_dict[k] = val
            except TypeError:
                pass
        return out_dict