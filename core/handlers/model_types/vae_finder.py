import json
import logging
import os

from core.dataclasses.model_data import ModelData
from core.handlers.models import ModelHandler
from dreambooth.dataclasses.db_config import from_file

logger = logging.getLogger(__name__)
mh = ModelHandler()


async def get_db_models(data, handler: ModelHandler):
    logger.debug(f"Data {data}")
    output = []
    for mdir in handler.models_path:
        logger.debug(f"Checking dir: {mdir}")
        out_dir = os.path.join(mdir, "vae")
        if os.path.exists(out_dir):
            for item in os.listdir(out_dir):
                full_item = os.path.join(out_dir, item)
                if os.path.isdir(full_item):
                    mi = ModelData(full_item)
                    config_path = os.path.join(full_item, "config.json")
                    if not os.path.exists(config_path):
                        continue
                    config_json = json.load(open(config_path, "r"))
                    class_name = config_json.get("_class_name", None)
                    if class_name == "AutoencoderKL":
                        if mi:
                            output.append(mi)
    return output


mh.register_finder("vae", get_db_models)
