import os

from core.handlers.models import ModelHandler

mh = ModelHandler()


def get_db_models(data):
    output = [""]
    out_dir = os.path.join(mh.models_path, "dreambooth")
    if os.path.exists(out_dir):
        for item in os.listdir(out_dir):
            if os.path.isdir(os.path.join(out_dir, item)):
                output.append(item)
    return output


mh.register_finder("dreambooth", get_db_models)
