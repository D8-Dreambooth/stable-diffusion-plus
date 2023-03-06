import os.path

from diffusers import DiffusionPipeline, DEISMultistepScheduler

from core.dataclasses.model_data import ModelData


def load_diffusers(model_data: ModelData):
    model_path = model_data.path
    pipeline = None
    if not os.path.exists(model_path):
        print(f"Unable to load model: {model_path}")
    else:
        print(f"Loading model: {model_path}")
        try:
            pipeline = DiffusionPipeline.from_pretrained(model_path)
            pipeline.set_use_memory_efficient_attention_xformers(True)
            pipeline.scheduler = DEISMultistepScheduler.from_config(pipeline.scheduler.config)
        except Exception as e:
            print(f"Exception loading pipeline: {e}")
    return pipeline


def register_function(model_handler):
    model_handler.register_loader("diffusers", load_diffusers)
