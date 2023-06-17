import json
import logging
import os

from core.dataclasses.model_data import ModelData
from core.handlers.model_types.controlnet_processors import controlnet_models
from core.handlers.models import ModelHandler
from dreambooth.dataclasses.db_config import from_file, DreamboothConfig
from dreambooth.dataclasses.finetune_config import FinetuneConfig

logger = logging.getLogger(__name__)
mh = ModelHandler()


async def get_controlnet_models(data, handler: ModelHandler):
    logger.debug(f"Data {data}")
    model_names = []
    output = []
    for mdir in handler.models_path:
        logger.debug(f"Checking dir: {mdir}")
        out_dir = os.path.join(mdir, "controlnet")
        if os.path.exists(out_dir):
            for item in os.listdir(out_dir):
                full_item = os.path.join(out_dir, item)
                if os.path.isdir(full_item):
                    logger.debug(f"Found model: {full_item}")
                    mi = ModelData(full_item)
                    output.append(mi)
                    model_names.append(item)
    preset_models = controlnet_models

    return output


mh.register_finder("controlnet", get_controlnet_models)
