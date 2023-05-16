import gc
import os
import time

import torch
from diffusers import DiffusionPipeline
from diffusers.models.attention_processor import AttnProcessor2_0

from dreambooth.utils.image_utils import get_scheduler_class

num_images = 1
prompt = "a cat wearing a hat"
resolution = 1024
torch.backends.cuda.matmul.allow_tf32 = True


def test_pipe():
    results = {}
    optimizer_methods = [["enable_vae_tiling", "enable_vae_slicing", "enable_xformers_memory_efficient_attention"],
                         ["enable_vae_tiling", "enable_xformers_memory_efficient_attention"],
                         ["enable_vae_slicing", "enable_xformers_memory_efficient_attention"]
                         ]

    model_path = os.path.abspath(os.path.join("..", "data_shared", "models", "diffusers", "v1-5-pruned.safetensors"))
    print(f"Model path: {model_path}")
    prompts = [prompt] * num_images

    for method_list in optimizer_methods:
        print(f"Testing methods: {method_list}")
        torch.cuda.empty_cache()
        gc.collect()
        cached = torch.cuda.memory_cached() / 1024 / 1024 / 1024
        # Truncate cached to 2 decimal places
        cached = int(cached * 100) / 100
        print(f"Current VRAM cache: {cached} GB")
        s_pipeline = DiffusionPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16
        )
        s_pipeline.unet.set_attn_processor(AttnProcessor2_0())
        print("Loaded pipeline")
        s_pipeline.scheduler = get_scheduler_class("UniPCMultistep").from_config(
            s_pipeline.scheduler.config
        )
        s_pipeline.scheduler.config.solver_type = "bh2"

        generator = torch.manual_seed(420420)
        to_gpu = True
        for method in method_list:
            if "offload" in method:
                to_gpu = False
            if method == "enable_sequential_cpu_offload":
                s_pipeline.enable_sequential_cpu_offload()
            elif method == "enable_sequential_cpu_offload":
                s_pipeline.enable_sequential_cpu_offload()
                s_pipeline.enable_attention_slicing(1)
            else:
                getattr(s_pipeline, method)()
        if to_gpu:
            s_pipeline.to("cuda")

        # Get a timestamp for the current time
        start_time = time.time()
        images = s_pipeline(
            prompt=prompts,
            num_inference_steps=20,
            width=resolution,
            height=resolution,
            generator=generator,
            guidance_scale=7.5
        ).images[0]

        # Calculate the elapsed time in milliseconds
        elapsed = int((time.time() - start_time) * 1000)

        cached = torch.cuda.memory_cached() / 1024 / 1024 / 1024
        # Truncate cached to 2 decimal places
        cached = int(cached * 100) / 100
        results["_".join(method_list)] = [cached, elapsed]
        print(f"Results for method:{'_'.join(method_list)} - {cached}GB {elapsed / 1000}s")
        del s_pipeline
        del images
    print("Results:")
    results = {k: v for k, v in sorted(results.items(), key=lambda item: item[1][0])}

    for key, value in results.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_pipe()
