import importlib
import inspect
import logging
import pkgutil
import traceback
from typing import List

import PIL.Image
from controlnet_aux.processor import Processor

from core.handlers.images import scale_image
from core.handlers.status import StatusHandler

logger = logging.getLogger(__name__)

controlnet_preprocessors = ["canny", "depth_leres", "depth_leres++", "depth_midas", "depth_zoe", "lineart_anime",
                            "lineart_coarse", "lineart_realistic", "mediapipe_face", "mlsd", "normal_bae",
                            "normal_midas",
                            "openpose", "openpose_face", "openpose_faceonly", "openpose_full", "openpose_hand",
                            "scribble_hed", "scribble_pidinet", "shuffle", "softedge_hed", "softedge_hedsafe",
                            "softedge_pidinet", "softedge_pidsafe"]

controlnet_models = {
    "depth": {
        "name": "Depth",
        "model_url": "lllyasviel/control_v11f1p_sd15_depth",
        "image_type": ["image"],
        "preprocessors": ["depth_leres++", "depth_leres", "depth_zoe", "depth_midas"]
    },
    "normal": {
        "name": "Normal",
        "model_url": "lllyasviel/control_v11p_sd15_normalbae",
        "image_type": ["image"],
        "preprocessors": ["normal_bae", "normal_midas"]
    },
    "canny": {
        "name": "Canny",
        "model_url": "lllyasviel/control_v11p_sd15_canny",
        "image_type": ["image"],
        "preprocessors": ["canny"]
    },
    "mlsd": {
        "name": "MLSD",
        "model_url": "lllyasviel/control_v11p_sd15_mlsd",
        "image_type": ["image"],
        "preprocessors": ["mlsd"]
    },
    "scribble": {
        "name": "Scribble",
        "model_url": "lllyasviel/control_v11p_sd15_scribble",
        "image_type": ["mask", "image"],
        "preprocessors": ["scribble_hed", "scribble_pidinet"]
    },
    "soft_edge": {
        "name": "Soft Edge",
        "model_url": "lllyasviel/control_v11p_sd15_softedge",
        "image_type": ["image"],
        "preprocessors": ["softedge_hed", "softedge_hedsafe", "softedge_pidinet", "softedge_pidsafe"]
    },
    "segmentation": {
        "name": "Segmentation",
        "model_url": "lllyasviel/control_v11p_sd15_seg",
        "image_type": ["image"],
        "preprocessors": "COCO"
    },
    "openpose": {
        "name": "Openpose",
        "model_url": "lllyasviel/control_v11p_sd15_openpose",
        "image_type": ["image"],
        "preprocessors": ["openpose", "openpose_face", "openpose_faceonly", "openpose_full", "openpose_hand"]
    },
    "lineart": {
        "name": "Lineart",
        "model_url": "lllyasviel/control_v11p_sd15_lineart",
        "image_type": ["image"],
        "preprocessors": ["lineart_coarse", "lineart_realistic", "lineart_anime"]
    },
    "anime_lineart": {
        "name": "Anime Lineart",
        "model_url": "lllyasviel/control_v11p_sd15s2_lineart_anime",
        "image_type": ["image"],
        "preprocessors": ["lineart_coarse", "lineart_realistic", "lineart_anime"]
    },
    "instruct_pix2pix": {
        "name": "Instruct Pix2Pix",
        "model_url": "lllyasviel/control_v11e_sd15_ip2p",
        "image_type": ["image"],
        "preprocessors": [None]
    },
    "inpaint": {
        "name": "Inpaint",
        "model_url": "lllyasviel/control_v11p_sd15_inpaint",
        "image_type": ["image"],
        "preprocessors": [None]
    },
    "tile": {
        "name": "Tile",
        "model_url": "lllyasviel/control_v11f1e_sd15_tile",
        "image_type": ["image"],
        "preprocessors": [None]
    },
    "shuffle": {
        "name": "Shuffle",
        "model_url": "lllyasviel/control_v11e_sd15_shuffle",
        "image_type": ["image"],
        "preprocessors": ["shuffle"]
    },
    "brightness": {
        "name": "Brightness",
        "model_url": "ioclab/control_v1p_sd15_brightness",
        "image_type": ["image"],
        "preprocessors": [None]
    },
    "qrcode": {
        "name": "QRCode",
        "model_url": "DionTimmer/controlnet_qrcode-control_v1p_sd15",
        "image_type": ["image"],
        "preprocessor": [None]
    }
}

# Sort the model data
controlnet_models = {k: v for k, v in sorted(controlnet_models.items(), key=lambda item: item[1]["name"])}


def find_detector_classes(module):
    for name, cls in inspect.getmembers(module, inspect.isclass):
        if 'Detector' in name:
            yield cls


def get_call_params(cls):
    for name, member in inspect.getmembers(cls):
        if name == '__call__':
            sig = inspect.signature(member)
            return {name: {'default': str(param.default), 'type': str(param.annotation)} for name, param in
                    sig.parameters.items()}


def get_detectors_and_params(package):
    result = {}
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        try:
            module = importlib.import_module(package.__name__ + "." + modname)
            for detector in find_detector_classes(module):
                params = []
                call_params = get_call_params(detector)
                for name, param in call_params.items():
                    if name == "self" or name == "return_pil":
                        continue
                    params.append({
                        "name": name,
                        "default": param["default"],
                        "type": param["type"]
                    })
                result[detector.__name__] = params
        except ImportError:
            continue
    return result


# Usage:
def preprocess_image(
        images: List[PIL.Image.Image],
        prompt: List[str],
        model_name: str,
        width: int = 1024,
        height: int = 1024,
        process: bool = True,
        resize_mode: str = "resize",
        preprocess_mode: str = "default",
        handler: StatusHandler = None) -> object:
    """

    :param preprocess_mode:
    :param images: A list of PIL images to process
    :param prompt: A list of prompts to use if necessary
    :param model_name: The controlnet being used for preprocessor selection
    :param width: The target width of the image, if resizing
    :param height: The target height of the image, if resizing
    :param process: Whether to preprocess the image, or just resize
    :param resize_mode: The mode to use for resizing, can be "scale", "stretch", "crop", or "pad"
    :param handler: The status handler to update
    :return:
    """
    if not len(images):
        logger.warning("NO IMAGE, STUPID")
        return images, prompt

    converted = []
    status = {
        "progress_2_total": len(images),
        "progress_2_current": 0
    }

    processor = None
    image_types = []
    model = controlnet_models.get(model_name, None)
    if model is not None:
        image_types = model["image_type"]

    if process:
        if preprocess_mode == "default" or preprocess_mode not in controlnet_preprocessors:
            preprocess_mode = None
            if model is not None:
                preprocess_mode = model["preprocessors"][0]
            if preprocess_mode is None:
                logger.debug("No preprocessing model selected.")
            elif preprocess_mode not in controlnet_preprocessors:
                logger.debug("Invalid preprocessing model selected.")
            else:
                preprocessor_id = controlnet_preprocessors[preprocess_mode]
                try:
                    processor = Processor(preprocessor_id)
                except Exception as e:
                    logger.error(f"Failed to load preprocessor {preprocessor_id}: {e}")

    status["status_2"] = "Loading preprocessor: " + model["preprocessor"]

    handler.update(items=status)
    for img in images:
        converted.append(img.convert("RGB"))

    images = converted

    processor_args = {"detect_resolution": width, "image_resolution": width}

    output = []
    out_prompts = []
    img_idx = 0
    for img in images:
        handler.update(
            items={"progress_2_current": img_idx, "status_2": f"Processing control image {img_idx}/{len(images)}"})
        handler.send()
        try:
            if len(prompt) == len(images):
                out_prompts.append(prompt[img_idx])
            img_idx += 1
            img = scale_image(img, width, height, resize_mode)
            if processor:
                restore_res = False
                if processor.resize:
                    restore_res = img.size
                processed = processor(img, **processor_args) if processor_args else processor(img)
                if restore_res:
                    logger.debug(f"Restoring resolution to {restore_res}")
                    processed = processed.resize(restore_res, resample=PIL.Image.BICUBIC)
                output.append(processed.convert("RGB"))
            else:
                output.append(img.convert("RGB"))
        except:
            logger.warning("Failed to preprocess image")
            traceback.print_exc()
        handler.update("status_2", "")
    return output, out_prompts
