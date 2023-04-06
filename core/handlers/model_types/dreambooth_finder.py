import logging
import os

from core.dataclasses.model_data import ModelData
from core.handlers.models import ModelHandler


logger = logging.getLogger(__name__)
mh = ModelHandler()


def get_db_models(data, handler: ModelHandler):
    logger.debug(f"Data {data}")
    output = []
    for mdir in handler.models_path:
        logger.debug(f"Checking dir: {mdir}")
        out_dir = os.path.join(mdir, "dreambooth")
        if os.path.exists(out_dir):
            for item in os.listdir(out_dir):
                full_item = os.path.join(out_dir, item)
                if os.path.isdir(full_item):
                    mi = ModelData(full_item)
                    if mi:
                        output.append(mi)
    return output


mh.register_finder("dreambooth", get_db_models)
