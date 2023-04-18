import logging
from controlnet_aux import OpenposeDetector, MLSDdetector, HEDdetector, CannyDetector, MidasDetector

logger = logging.getLogger(__name__)

model_data = [
    {
        "name": "ControlNet 1.1 Depth",
        "model_file": "control_v11p_sd15_depth.pth",
        "config_file": "control_v11p_sd15_depth.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_depth",
        "image_type": "image",
        "acceptable_preprocessors": ["Depth_Midas"]
    },
    {
        "name": "ControlNet 1.1 Normal",
        "model_file": "control_v11p_sd15_normalbae.pth",
        "config_file": "control_v11p_sd15_normalbae.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_normalbae",
        "image_type": "image",
        "acceptable_preprocessors": ["Normal"]
    },
    {
        "name": "ControlNet 1.1 Canny",
        "model_file": "control_v11p_sd15_canny.pth",
        "config_file": "control_v11p_sd15_canny.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_canny",
        "image_type": "image",
        "acceptable_preprocessors": ["Canny"]
    },
    {
        "name": "ControlNet 1.1 MLSD",
        "model_file": "control_v11p_sd15_mlsd.pth",
        "config_file": "control_v11p_sd15_mlsd.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_mlsd",
        "image_type": "image",
        "acceptable_preprocessors": ["MLSD"]
    },
    {
        "name": "ControlNet 1.1 Scribble",
        "model_file": "control_v11p_sd15_scribble.pth",
        "config_file": "control_v11p_sd15_scribble.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_scribble",
        "image_type": "mask",
        "acceptable_preprocessors": []
    },
    {
        "name": "ControlNet 1.1 Soft Edge",
        "model_file": "control_v11p_sd15_softedge.pth",
        "config_file": "control_v11p_sd15_softedge.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_softedge",
        "image_type": "image",
        "acceptable_preprocessors": ["SoftEdge_HED"]
    },
    {
        "name": "ControlNet 1.1 Segmentation",
        "model_file": "control_v11p_sd15_seg.pth",
        "config_file": "control_v11p_sd15_seg.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_seg",
        "image_type": "image",
        "acceptable_preprocessors": ["Seg_OFADE20K", "Seg_OFCOCO", "Seg_UFADE20K", "manually created masks"]
    },
    {
        "name": "ControlNet 1.1 Openpose",
        "model_file": "control_v11p_sd15_openpose.pth",
        "config_file": "control_v11p_sd15_openpose.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_openpose",
        "image_type": "image",
        "acceptable_preprocessors": ["Openpose", "Openpose Full"]
    },
    {
        "name": "ControlNet 1.1 Lineart",
        "model_file": "control_v11p_sd15_lineart.pth",
        "config_file": "control_v11p_sd15_lineart.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_lineart",
        "image_type": "image",
        "acceptable_preprocessors": ["Lineart", "Lineart_Coarse", "manually drawn linearts"]
    },
    {
        "name": "ControlNet 1.1 Anime Lineart",
        "model_file": "control_v11p_sd15s2_lineart_anime.pth",
        "config_file": "control_v11p_sd15s2_lineart_anime.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15s2_lineart_anime",
        "image_type": "image",
        "acceptable_preprocessors": ["real anime line drawings", "extracted line drawings"]
    },
    {
        "name": "ControlNet 1.1 Shuffle",
        "model_file": "control_v11e_sd15_shuffle.pth",
        "config_file": "control_v11e_sd15_shuffle.yaml",
        "model_url": "lllyasviel/control_v11f1e_sd15_shuffle",
        "image_type": "image",
        "acceptable_preprocessors": []
    },
    {
        "name": "ControlNet 1.1 Instruct Pix2Pix",
        "model_file": "control_v11e_sd15_ip2p.pth",
        "config_file": "control_v11e_sd15_ip2p.yaml",
        "model_url": "lllyasviel/control_v11f1e_sd15_ip2p",
        "image_type": "image",
        "acceptable_preprocessors": []
    },
    {
        "name": "ControlNet 1.1 Inpaint",
        "model_file": "control_v11p_sd15_inpaint.pth",
        "config_file": "control_v11p_sd15_inpaint.yaml",
        "model_url": "lllyasviel/control_v11f1p_sd15_inpaint",
        "image_type": "image",
        "acceptable_preprocessors": []
    },
    {
        "name": "ControlNet 1.1 Tile (Unfinished)",
        "model_file": "control_v11u_sd15_tile.pth",
        "config_file": "control_v11u_sd15_tile.yaml",
        "model_url": "lllyasviel/control_v11f1u_sd15_tile",
        "image_type": "image",
        "acceptable_preprocessors": []
    }
]


def get_model_data(model_name):
    for model in model_data:
        if model["name"] == model_name:
            return model
    return None


def preprocess_image(image, model_name, param_a, param_b, processor_name: str = None):
    model = get_model_data(model_name)
    if image is None:
        logger.warning("NO IMAGE STUPID")
        return image
    if model is None:
        logger.warning("Couldn't get model.")
        return model
    processors = model["acceptable_preprocessors"]
    if len(processors) == 0:
        logger.warning("No preprocessors")
        return None
    scribble = False
    processor = None
    normal = False
    if processor_name is None and len(processors):
        processor_name = processors[0]
        logger.debug(f"Set processor name to {processor_name}")

    if processor_name is not None:
        if processor_name not in processors:
            return None
        if processor_name == "Depth_Midas":
            processor = MidasDetector.from_pretrained("lllyasviel/ControlNet")
        if processor_name == "Canny":
            processor = CannyDetector()
        if processor_name == "MLSD":
            processor = MLSDdetector.from_pretrained("lllyasviel/ControlNet")
        if processor_name == "SoftEdge_HED":
            processor = HEDdetector.from_pretrained("lllyasviel/ControlNet")
        if processor_name == "SoftEdge_HED_safe":
            processor = HEDdetector.from_pretrained("lllyasviel/ControlNet")
        if processor_name == "Openpose":
            processor = OpenposeDetector.from_pretrained("lllyasviel/ControlNet")
        if processor_name == "Openpose Full":
            processor = OpenposeDetector.from_pretrained("lllyasviel/ControlNet")
    if "Scribble" in model_name:
        processor = HEDdetector.from_pretrained("lllyasviel/ControlNet")
        scribble = True
    if "Normal" in model_name:
        processor = MidasDetector.from_pretrained("lllyasviel/ControlNet")
        normal = True

    if processor:
        if normal or processor_name == "Depth_Midas":
            img_1, img_2 = processor(image, param_a, param_b)
            return img_1 if not normal else img_2
        if scribble:
            return processor(image, param_a, param_b, scribble=True)
        else:
            return processor(image, param_a, param_b)

    return image
