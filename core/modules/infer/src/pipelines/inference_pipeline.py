from typing import Dict, Any

from core.handlers.models import ModelHandler
from core.pipelines.base_pipeline import BasePipeline


class InferencePipeline(BasePipeline):
    def __init__(self):
        super().__init__()
        self.model_handler = ModelHandler()

    def load(self, src_pipe: Any, params: Dict):
        loaded_models = self.model_handler.loaded_models
        diff_model = loaded_models.get("diffusers", None)
        if diff_model is None:
            self.pipe = self.model_handler.load_model("diffusers", params["model"])
        else:
            loaded_models = self.model_handler.loaded_models
            self.pipe = loaded_models.get("diffusers", None)

        if diff_model is None:
            print("NOTHING TO INFER WITH.")
        pass

    def unload(self):
        pass

    def process(self, params: Dict = None) -> Dict:
        pass
