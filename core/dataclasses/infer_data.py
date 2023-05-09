import base64
import decimal
import logging
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, Union, List

from PIL import Image

from core.dataclasses.model_data import ModelData


@dataclass
class InferSettings:
    batch_size: int = 1
    controlnet_batch = False
    controlnet_batch_dir = None
    controlnet_batch_find = ""
    controlnet_batch_replace = ""
    controlnet_batch_use_prompt = ""
    controlnet_image = None
    controlnet_mask = None
    controlnet_preprocess = True
    controlnet_type = None
    enable_controlnet = False
    height: int = 512
    infer_image = None
    infer_mask = None
    mode: str = "infer"
    model: ModelData = "None"
    loras: List[ModelData] = None
    negative_prompt: str = ""
    num_images: int = 1
    prompt: str = ""
    scale: float = 7.5
    seed: int = -1
    use_sag = False
    steps: int = 20
    width: int = 512

    def __init__(self, data: Dict):
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
                return Image.open(BytesIO(img_bytes))

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
        value = self.infer_image
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
        value = self.infer_mask
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
