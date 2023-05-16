import os

from core.dataclasses.model_data import ModelData
from core.handlers.models import ModelHandler

mh = ModelHandler()


async def get_lora_models(data, handler: ModelHandler):
    output = []
    for mdir in handler.models_path:
        lora_dir = os.path.join(mdir, "loras")
        if os.path.exists(lora_dir):
            files = os.listdir(lora_dir)
            for file in files:
                if os.path.isfile(os.path.join(lora_dir, file)):
                    if ".pt" in file and "_txt.pt" not in file:
                        output.append(ModelData(file))
    return output


mh.register_finder("lora", get_lora_models)
