import asyncio
import logging
import random
import traceback
import concurrent.futures

import torch
from tqdm import tqdm

from app.syncio import sync
from core.dataclasses.infer_data import InferSettings
from core.handlers.images import ImageHandler
from core.handlers.models import ModelHandler
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler

socket_handler = SocketHandler()
model_handler = ModelHandler()
status_handler = StatusHandler()
image_handler = ImageHandler()

logger = logging.getLogger(__name__)

pipeline = None


async def start_inference(inference_settings: InferSettings):
    global pipeline
    logger.debug(f"Infer the things: {inference_settings}")
    status_handler.start(inference_settings.num_images * inference_settings.steps, "Starting inference.")
    # Check if our selected model is loaded, if not, loaded it.
    loaded_models = model_handler.loaded_models
    logger.debug(f"Loaded: {loaded_models}")
    model_info, diff_model = loaded_models.get("diffusers", (None, None))
    if diff_model is None:
        logger.info(f"Loading model: {model_info}")
        diff_model = model_handler.load_model("diffusers", inference_settings.model)
    else:
        loaded_models = model_handler.loaded_models
        model_info, diff_model = loaded_models.get("diffusers", None)

    out_images = []
    out_prompts = []

    if diff_model is None:
        logger.warning("No model selected.")

    else:
        pipeline = diff_model
        try:
            prompts = [inference_settings.prompt] * inference_settings.batch_size
            negative_prompts = [inference_settings.negative_prompt] * inference_settings.batch_size
            status_handler.update(
                items={"status": f"Generating {len(out_images)}/{inference_settings.num_images} images."})
            initial_seed = inference_settings.seed
            pbar = tqdm(desc="Making images.", total=inference_settings.num_images)
            while len(out_images) < inference_settings.num_images:
                if initial_seed == -1:
                    seed = int(random.randrange(21474836147))
                else:
                    initial_seed = initial_seed + 1
                    if initial_seed > 21474836147:
                        initial_seed = int(random.randrange(21474836147))
                    seed = initial_seed
                generator = torch.manual_seed(int(seed))
                loop = asyncio.get_event_loop()
                # Here's the magic sauce
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    s_image = await loop.run_in_executor(pool, lambda: diff_model(prompts,
                                                                                  num_inference_steps=inference_settings.steps,
                                                                                  guidance_scale=inference_settings.scale,
                                                                                  negative_prompt=negative_prompts,
                                                                                  height=inference_settings.width,
                                                                                  width=inference_settings.height,
                                                                                  callback=update_progress,
                                                                                  generator=generator).images)
                pbar.update(len(s_image))
                paths = []
                for img in s_image:
                    img_path = image_handler.db_save_image(img, "testing", inference_settings, False)
                    paths.append(img_path)
                out_images.extend(paths)
                out_prompts.extend(prompts)
                status_handler.update(items={"images": out_images, "prompts": out_prompts,
                                             "status": f"Generating {len(out_images)}/{inference_settings.num_images} images."},
                                      send=False)
                status_handler.step(len(s_image))
                remaining = inference_settings.num_images - len(out_images)
                if remaining <= inference_settings.batch_size:
                    logger.debug(f"Remaining: {remaining}")
                    prompts = [inference_settings.prompt] * remaining
                    negative_prompts = [inference_settings.negative_prompt] * remaining

        except Exception as e:
            logger.error(f"Exception inferring: {e}")
            traceback.print_exc()
    status_handler.update(
        items={"status": f"Generation complete."})
    return out_images, out_prompts


def update_progress(step: int, timestep: int, latents: torch.FloatTensor):
    global pipeline
    # Move the latents tensor to CPU if it's on a different device
    image = pipeline.decode_latents(latents)
    images = pipeline.numpy_to_pil(image)
    logger.debug(f"Images are: {type(images)}")
    # Update the progress status handler with the new items
    status_handler.update(items={
        "progress_1_current": step,
        "images": images,
    }, send=True)
