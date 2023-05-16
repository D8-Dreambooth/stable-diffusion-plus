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
        out_dir = os.path.join(mdir, "dreambooth")
        if os.path.exists(out_dir):
            for item in os.listdir(out_dir):
                full_item = os.path.join(out_dir, item)
                if os.path.isdir(full_item):
                    mi = ModelData(full_item)
                    config_path = os.path.join(full_item, "db_config.json")
                    if os.path.exists(config_path):
                        config = from_file(full_item)
                        mi.data["db_config"] = config.__dict__
                        model_src = ""
                        if "src" in mi.data["db_config"] and mi.data["db_config"]["src"]:
                            model_src = mi.data["db_config"]["src"]
                        if os.path.exists(model_src):
                            try:
                                src_model_data = await handler.find_model("diffusers", model_src)
                                if src_model_data is not None:
                                    mi.data["db_config"]["src"] = src_model_data.display_name
                            except:
                                pass
                        if mi:
                            output.append(mi)
    return output


mh.register_finder("dreambooth", get_db_models)
