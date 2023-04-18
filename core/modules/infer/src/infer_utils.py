import asyncio
import concurrent.futures
import logging
import random
import traceback

import torch
from tqdm import tqdm

from core.dataclasses.infer_data import InferSettings
from core.handlers.config import ConfigHandler
from core.handlers.images import ImageHandler
from core.handlers.model_types.controlnet_processors import model_data as controlnet_data, preprocess_image
from core.handlers.models import ModelHandler
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler

socket_handler = SocketHandler()
logger = logging.getLogger(__name__)
preview_steps = 5
pipeline = None


async def start_inference(inference_settings: InferSettings, user):
    global pipeline, preview_steps
    model_handler = ModelHandler(user_name=user)
    status_handler = StatusHandler(user_name=user)
    image_handler = ImageHandler(user_name=user)
    ch = ConfigHandler()
    logger.debug(f"Infer the things: {inference_settings}")
    status_handler.start(inference_settings.num_images * inference_settings.steps, "Starting inference.")
    # Check if our selected model is loaded, if not, loaded it.
    load_controlnet = False
    process_image = False
    preprocess_src = None
    control_image = None
    if inference_settings.enable_controlnet and inference_settings.controlnet_type:
        for cd in controlnet_data:
            if cd["name"] == inference_settings.controlnet_type:
                if len(cd["acceptable_preprocessors"]) > 0:
                    process_image = True
                preprocess_src = cd["image_type"]
                break

        logger.debug("Using controlnet?")
        src_image = inference_settings.get_image()
        src_mask = inference_settings.get_mask()
        control_image = None

        if process_image:
            if preprocess_src == "image":
                if not src_image:
                    logger.warning("No image to preprocess.")
                    return
                else:
                    control_image = preprocess_image(src_image, inference_settings.controlnet_type, 100, 300)
                    control_image = control_image.convert("RGB")
                    logger.debug("Control image type is " + str(type(control_image)))

            if preprocess_src == "mask":
                if not src_mask:
                    logger.warning("No mask to preprocess.")
                    return
                else:
                    control_image = preprocess_image(src_mask, inference_settings.controlnet_type, 100, 300)
                    control_image = control_image.convert("RGB")

        else:
            control_image = src_image if src_image else src_mask

        if process_image and not control_image:
            logger.warning("NO CONTROL IMAGE!")
            return

        load_controlnet = True
    model_data = inference_settings.model

    if load_controlnet:
        model_data.data = {"type": inference_settings.controlnet_type}
        # Add controlnet to model_data data dict
        pipeline = model_handler.load_model("diffusers_controlnet", model_data)
    else:
        pipeline = model_handler.load_model("diffusers", model_data)

    out_images = []
    out_prompts = []

    if pipeline is None:
        logger.warning("No model selected.")

    else:
        try:
            prompts = [inference_settings.prompt] * inference_settings.batch_size
            negative_prompts = [inference_settings.negative_prompt] * inference_settings.batch_size
            status_handler.update(
                items={
                    "status": f"Generating {len(out_images) + (1 * inference_settings.batch_size)}/{inference_settings.num_images} images."})
            initial_seed = inference_settings.seed
            pbar = tqdm(desc="Making images.", total=inference_settings.num_images)

            def update_progress(step: int, timestep: int, latents: torch.FloatTensor):
                # Move the latents tensor to CPU if it's on a different device
                image = pipeline.decode_latents(latents)
                images = pipeline.numpy_to_pil(image)
                logger.debug(f"Images are: {type(images)}")
                # Update the progress status handler with the new items
                status_handler.update(items={
                    "images": images,
                }, send=False)
                status_handler.step(preview_steps)

            while len(out_images) < inference_settings.num_images:
                if status_handler.status.canceled:
                    logger.debug("Canceled!")
                    break
                if initial_seed == -1:
                    seed = int(random.randrange(21474836147))
                else:
                    initial_seed = initial_seed + 1
                    if initial_seed > 21474836147:
                        initial_seed = int(random.randrange(21474836147))
                    seed = initial_seed
                inference_settings.seed = seed
                generator = torch.manual_seed(int(seed))
                loop = asyncio.get_event_loop()
                # Here's the magic sauce
                preview_steps = ch.get_item("preview_steps", default=5)
                if preview_steps > inference_settings.steps:
                    preview_steps = inference_settings.steps
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    if inference_settings.enable_controlnet and inference_settings.controlnet_type:
                        if preview_steps > 0:
                            s_image = await loop.run_in_executor(pool, lambda: pipeline(prompts,
                                                                                        image=control_image,
                                                                                        num_inference_steps=inference_settings.steps,
                                                                                        guidance_scale=inference_settings.scale,
                                                                                        negative_prompt=negative_prompts,
                                                                                        height=inference_settings.height,
                                                                                        width=inference_settings.width,
                                                                                        callback=update_progress,
                                                                                        callback_steps=preview_steps,
                                                                                        generator=generator).images)
                        else:
                            s_image = await loop.run_in_executor(pool, lambda: pipeline(prompts,
                                                                                        image=control_image,
                                                                                        num_inference_steps=inference_settings.steps,
                                                                                        guidance_scale=inference_settings.scale,
                                                                                        negative_prompt=negative_prompts,
                                                                                        height=inference_settings.height,
                                                                                        width=inference_settings.width,
                                                                                        generator=generator).images)
                    else:
                        if preview_steps > 0:
                            s_image = await loop.run_in_executor(pool, lambda: pipeline(prompts,
                                                                                        num_inference_steps=inference_settings.steps,
                                                                                        guidance_scale=inference_settings.scale,
                                                                                        negative_prompt=negative_prompts,
                                                                                        height=inference_settings.height,
                                                                                        width=inference_settings.width,
                                                                                        callback=update_progress,
                                                                                        callback_steps=preview_steps,
                                                                                        generator=generator).images)
                        else:
                            s_image = await loop.run_in_executor(pool, lambda: pipeline(prompts,
                                                                                        num_inference_steps=inference_settings.steps,
                                                                                        guidance_scale=inference_settings.scale,
                                                                                        negative_prompt=negative_prompts,
                                                                                        height=inference_settings.height,
                                                                                        width=inference_settings.width,
                                                                                        generator=generator).images)
                pbar.update(len(s_image))
                paths = []
                for img in s_image:
                    img_path = image_handler.db_save_image(img, "testing", inference_settings, False)
                    paths.append(img_path)

                out_images.extend(paths)
                out_prompts.extend(prompts)
                status_handler.update(items={
                    "status": f"Generating {len(out_images) + (1 * inference_settings.batch_size)}/{inference_settings.num_images} images."},
                    send=True)
                remaining = inference_settings.num_images - len(out_images)
                if remaining <= inference_settings.batch_size:
                    logger.debug(f"Remaining: {remaining}")
                    prompts = [inference_settings.prompt] * remaining
                    negative_prompts = [inference_settings.negative_prompt] * remaining

        except Exception as e:
            logger.error(f"Exception inferring: {e}")
            traceback.print_exc()
    if control_image is not None:
        out_images.append(control_image)
        out_prompts.append("Control image")
    status_handler.update(
        items={"status": f"Generation complete.", "images": out_images, "prompts": out_prompts})
    return out_images, out_prompts
