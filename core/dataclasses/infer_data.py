from dataclasses import dataclass
from typing import Dict

from core.dataclasses.model_data import ModelData


@dataclass
class InferSettings:
    prompt: str = "foo"
    negative_prompt: str = "foo"
    steps: int = 20
    scale: float = 7.5
    num_images: int = 1
    batch_size: int = 1
    model: ModelData = "None"
    seed: int = -1
    width: int = 512
    height: int = 512

    def __init__(self, data: Dict):
        for key, value in data.items():
            if getattr(self, key, None):
                if key == "model":
                    md = ModelData(value["path"])
                    md.deserialize(value)
                    value = md
                    # Convert dict to ModelData class here

                setattr(self, key, value)
