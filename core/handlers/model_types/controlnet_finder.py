import logging
import os

from core.dataclasses.model_data import ModelData
from core.handlers.models import ModelHandler

logger = logging.getLogger(__name__)
mh = ModelHandler()


async def get_controlnet_models(data, handler: ModelHandler):
    model_names = []
    output = []
    for mdir in handler.models_path:
        out_dir = os.path.join(mdir, "controlnet")
        if os.path.exists(out_dir):
            for item in os.listdir(out_dir):
                full_item = os.path.join(out_dir, item)
                if os.path.isdir(full_item):
                    mi = ModelData(full_item)
                    output.append(mi)
                    model_names.append(item)

    return output


mh.register_finder("controlnet", get_controlnet_models)
