import logging
import traceback
from typing import List

import PIL.Image
from PIL.Image import Resampling
from controlnet_aux import OpenposeDetector, MLSDdetector, HEDdetector, CannyDetector, MidasDetector
from controlnet_aux import PidiNetDetector, NormalBaeDetector, LineartDetector, LineartAnimeDetector, ContentShuffleDetector

from core.modules.infer.src.preprocessors.coco_detector import CocoDetector

logger = logging.getLogger(__name__)

model_data = [
    {
        "name": "ControlNet 1.1 Depth",
        "model_file": "control_v11p_sd15_depth.pth",
        "config_file": "control_v11p_sd15_depth.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_depth",
        "image_type": "image",
        "preprocessor": "Depth_Midas"
    },
    {
        "name": "ControlNet 1.1 Normal",
        "model_file": "control_v11p_sd15_normalbae.pth",
        "config_file": "control_v11p_sd15_normalbae.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_normalbae",
        "image_type": "image",
        "preprocessor": "Normal"
    },
    {
        "name": "ControlNet 1.1 Canny",
        "model_file": "control_v11p_sd15_canny.pth",
        "config_file": "control_v11p_sd15_canny.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_canny",
        "image_type": "image",
        "preprocessor": "Canny"
    },
    {
        "name": "ControlNet 1.1 MLSD",
        "model_file": "control_v11p_sd15_mlsd.pth",
        "config_file": "control_v11p_sd15_mlsd.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_mlsd",
        "image_type": "image",
        "preprocessor": "MLSD"
    },
    {
        "name": "ControlNet 1.1 Scribble",
        "model_file": "control_v11p_sd15_scribble.pth",
        "config_file": "control_v11p_sd15_scribble.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_scribble",
        "image_type": "mask",
        "preprocessor": "Scribble"
    },
    {
        "name": "ControlNet 1.1 Soft Edge",
        "model_file": "control_v11p_sd15_softedge.pth",
        "config_file": "control_v11p_sd15_softedge.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_softedge",
        "image_type": "image",
        "preprocessor": "SoftEdge_HED"
    },
    {
        "name": "ControlNet 1.1 Segmentation",
        "model_file": "control_v11p_sd15_seg.pth",
        "config_file": "control_v11p_sd15_seg.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_seg",
        "image_type": "image",
        "preprocessor": "COCO"
    },
    {
        "name": "ControlNet 1.1 Openpose",
        "model_file": "control_v11p_sd15_openpose.pth",
        "config_file": "control_v11p_sd15_openpose.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_openpose",
        "image_type": "image",
        "preprocessor": "Openpose"
    },
    {
        "name": "ControlNet 1.1 Lineart",
        "model_file": "control_v11p_sd15_lineart.pth",
        "config_file": "control_v11p_sd15_lineart.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_lineart",
        "image_type": "image",
        "preprocessor": "Lineart"
    },
    {
        "name": "ControlNet 1.1 Anime Lineart",
        "model_file": "control_v11p_sd15s2_lineart_anime.pth",
        "config_file": "control_v11p_sd15s2_lineart_anime.yaml",
        "model_url": "lllyasviel/control_v11p_sd15s2_lineart_anime",
        "image_type": "image",
        "preprocessor": "Lineart_Anime"
    },
    {
        "name": "ControlNet 1.1 Instruct Pix2Pix",
        "model_file": "control_v11e_sd15_ip2p.pth",
        "config_file": "control_v11e_sd15_ip2p.yaml",
        "model_url": "lllyasviel/control_v11e_sd15_ip2p",
        "image_type": "image",
        "preprocessor": None
    },
    {
        "name": "ControlNet 1.1 Inpaint",
        "model_file": "control_v11p_sd15_inpaint.pth",
        "config_file": "control_v11p_sd15_inpaint.yaml",
        "model_url": "lllyasviel/control_v11p_sd15_inpaint",
        "image_type": "image",
        "preprocessor": None
    },
    {
        "name": "ControlNet 1.1 Tile (Unfinished)",
        "model_file": "control_v11u_sd15_tile.pth",
        "config_file": "control_v11u_sd15_tile.yaml",
        "model_url": "lllyasviel/control_v11u_sd15_tile",
        "image_type": "image",
        "preprocessor": None
    },
    {
        "name": "ControlNet 1.1 Shuffle",
        "model_file": "control_v11e_sd15_shuffle.pth",
        "config_file": "control_v11e_sd15_shuffle.yaml",
        "model_url": "lllyasviel/control_v11e_sd15_shuffle",
        "image_type": "image",
        "preprocessor": "Shuffle"
    }
]


def get_model_data(model_name):
    for model in model_data:
        if model["name"] == model_name:
            return model
    return None


def preprocess_image(images: List[PIL.Image.Image], prompt: str, model_name: str, max_res: int = 1024, process:bool = True):
    model = get_model_data(model_name)
    if not len(images):
        logger.warning("NO IMAGE, STUPID")
        return None, prompt
    if model is None:
        logger.warning("Couldn't get model.")
        return None, prompt

    converted = []
    for img in images:
        converted.append(img.convert("RGB"))

    images = converted

    processor_name = model["preprocessor"] if process else None

    processor = None
    processor_args = {"detect_resolution": max_res, "image_resolution": max_res}
    if processor_name is not None:
        if processor_name == "Depth_Midas":
            processor_args = {}
            processor = MidasDetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "Canny":
            processor_args = {}
            processor = CannyDetector()
        if processor_name == "COCO":
            processor_args = {}
            processor = CocoDetector()
        if processor_name == "Normal":
            processor = NormalBaeDetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "MLSD":
            processor = MLSDdetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "SoftEdge_HED":
            processor = HEDdetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "SoftEdge_HED_safe":
            processor = HEDdetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "PidiNet":
            processor = PidiNetDetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "Openpose":
            processor_args["hand_and_face"] = True
            processor = OpenposeDetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "Shuffle":
            processor = ContentShuffleDetector()
        if processor_name == "Lineart":
            processor = LineartDetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "Lineart_Anime":
            processor = LineartAnimeDetector.from_pretrained("lllyasviel/Annotators")
        if processor_name == "Scribble":
            processor_args["scribble"] = True
            processor = HEDdetector.from_pretrained("lllyasviel/Annotators")

    output = []
    out_prompts = []
    img_idx = 0
    for img in images:
        try:
            if len(prompt) == len(images):
                out_prompts.append(prompt[img_idx])
            img_idx += 1
            width, height = img.size
            logger.debug(f"Max res: {max_res}, width: {width}, height: {height}")
            new_height = height
            new_width = width
            if width > max_res or height > max_res:
                if width > max_res or height > max_res:
                    max_dimension = max_res
                    aspect_ratio = float(width) / float(height)

                    if width > height:
                        new_width = max_dimension
                        new_height = int(new_width / aspect_ratio)
                    else:
                        new_height = max_dimension
                        new_width = int(new_height * aspect_ratio)
                    img = img.resize((new_width, new_height), Resampling.LANCZOS)
                    width = new_width
                    height = new_height

            new_width = int(new_width / 16) * 16
            new_height = int(new_height / 16) * 16

            # Crop the image from center
            if new_width != width or new_height != height:
                left = (width - new_width) // 2
                top = (height - new_height) // 2
                right = (width + new_width) // 2
                bottom = (height + new_height) // 2
                img = img.crop((left, top, right, bottom))

            if processor:
                processed = processor(img, **processor_args) if processor_args else processor(img)
                output.append(processed.convert("RGB"))
            else:
                output.append(img.convert("RGB"))
        except:
            logger.warning("Failed to preprocess image")
            traceback.print_exc()
    return output, out_prompts
