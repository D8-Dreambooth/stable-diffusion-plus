from controlnet_aux import OpenposeDetector, MLSDdetector, HEDdetector, CannyDetector, MidasDetector

model_data = [
    {
        "name": "ControlNet 1.1 Depth",
        "model_file": "control_v11p_sd15_depth.pth",
        "config_file": "control_v11p_sd15_depth.yaml",
        "acceptable_preprocessors": ["Depth_Midas"]
    },
    {
        "name": "ControlNet 1.1 Normal",
        "model_file": "control_v11p_sd15_normalbae.pth",
        "config_file": "control_v11p_sd15_normalbae.yaml",
        "acceptable_preprocessors": ["Normal"]
    },
    {
        "name": "ControlNet 1.1 Canny",
        "model_file": "control_v11p_sd15_canny.pth",
        "config_file": "control_v11p_sd15_canny.yaml",
        "acceptable_preprocessors": ["Canny"]
    },
    {
        "name": "ControlNet 1.1 MLSD",
        "model_file": "control_v11p_sd15_mlsd.pth",
        "config_file": "control_v11p_sd15_mlsd.yaml",
        "acceptable_preprocessors": ["MLSD"]
    },
    {
        "name": "ControlNet 1.1 Scribble",
        "model_file": "control_v11p_sd15_scribble.pth",
        "config_file": "control_v11p_sd15_scribble.yaml",
        "acceptable_preprocessors": []
    },
    {
        "name": "ControlNet 1.1 Soft Edge",
        "model_file": "control_v11p_sd15_softedge.pth",
        "config_file": "control_v11p_sd15_softedge.yaml",
        "acceptable_preprocessors": ["SoftEdge_HED"]
    },
    {
        "name": "ControlNet 1.1 Segmentation",
        "model_file": "control_v11p_sd15_seg.pth",
        "config_file": "control_v11p_sd15_seg.yaml",
        "acceptable_preprocessors": ["Seg_OFADE20K", "Seg_OFCOCO", "Seg_UFADE20K", "manually created masks"]
    },
    {
        "name": "ControlNet 1.1 Openpose",
        "model_file": "control_v11p_sd15_openpose.pth",
        "config_file": "control_v11p_sd15_openpose.yaml",
        "acceptable_preprocessors": ["Openpose", "Openpose Full"]
    },
    {
        "name": "ControlNet 1.1 Lineart",
        "model_file": "control_v11p_sd15_lineart.pth",
        "config_file": "control_v11p_sd15_lineart.yaml",
        "acceptable_preprocessors": ["Lineart", "Lineart_Coarse", "manually drawn linearts"]
    },
    {
        "name": "ControlNet 1.1 Anime Lineart",
        "model_file": "control_v11p_sd15s2_lineart_anime.pth",
        "config_file": "control_v11p_sd15s2_lineart_anime.yaml",
        "acceptable_preprocessors": ["real anime line drawings", "extracted line drawings"]
    },
    {
        "name": "ControlNet 1.1 Shuffle",
        "model_file": "control_v11e_sd15_shuffle.pth",
        "config_file": "control_v11e_sd15_shuffle.yaml",
        "acceptable_preprocessors": []
    },
    {
        "name": "ControlNet 1.1 Instruct Pix2Pix",
        "model_file": "control_v11e_sd15_ip2p.pth",
        "config_file": "control_v11e_sd15_ip2p.yaml",
        "acceptable_preprocessors": []
    },
    {
        "name": "ControlNet 1.1 Inpaint",
        "model_file": "control_v11p_sd15_inpaint.pth",
        "config_file": "control_v11p_sd15_inpaint.yaml",
        "acceptable_preprocessors": []
    },
    {
        "name": "ControlNet 1.1 Tile (Unfinished)",
        "model_file": "control_v11u_sd15_tile.pth",
        "config_file": "control_v11u_sd15_tile.yaml",
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
    if model is None:
        return None
    processors = model["acceptable_preprocessors"]
    if len(processors) == 0:
        return None
    scribble = False
    processor = None
    normal = False

    if processor_name is not None:
        if processor_name not in processors:
            return image
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
