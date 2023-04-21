import asyncio
import concurrent.futures
import logging
import math
import os
import random
import traceback

import torch
from PIL.Image import Image, Resampling
from tqdm import tqdm

from core.dataclasses.infer_data import InferSettings
from core.handlers.config import ConfigHandler
from core.handlers.file import FileHandler, list_features, is_image
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
    process_image = False
    preprocess_src = None
    control_image = None
    input_prompts = []
    negative_prompts = []
    control_images = []
    gen_height = inference_settings.height
    gen_width = inference_settings.width

    model_data = inference_settings.model
    total_images = 0

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
        if process_image:
            control_image = None
            if not inference_settings.controlnet_batch:
                if process_image:
                    if preprocess_src == "image":
                        if not src_image:
                            logger.warning("No image to preprocess.")
                            return
                        else:
                            control_image = preprocess_image(src_image, inference_settings.controlnet_type, 100, 300)
                    if preprocess_src == "mask":
                        if not src_mask:
                            logger.warning("No mask to preprocess.")
                            return
                        else:
                            control_image = preprocess_image(src_mask, inference_settings.controlnet_type, 100, 300)
                else:
                    control_image = src_image if src_image else src_mask
                control_images.append(control_image)
                input_prompts.append(inference_settings.prompt)
                negative_prompts.append(inference_settings.negative_prompt)
            else:
                logger.debug("Controlnet batch, baby!")
                gen_width = 0
                gen_height = 0
                batch_dir = inference_settings.controlnet_batch_dir
                file_handler = FileHandler(user_name=user)
                files = file_handler.get_dir_content(batch_dir, True, False, None)
                images = []
                pil_features = list_features()

                for file in files:
                    logger.debug(f"Checking: {file}")
                    if is_image(os.path.join(file_handler.user_dir, file), pil_features):
                        logger.debug(f"Adding: {file}")
                        images.append(file)

                for image in images:
                    file_req = {"data": {"files": image, "return_pil": True}}
                    image_data = await file_handler.get_file(file_req)
                    logger.debug(f"mage data: {image_data}")
                    image = image_data["files"][0]["image"]
                    try:
                        control_image = preprocess_image(image, inference_settings.controlnet_type, 100, 300)
                        control_image = control_image.convert("RGB")
                        control_images.append(control_image)
                        prompt = image_data["files"][0]["data"]
                        if not prompt and inference_settings.controlnet_batch_use_prompt:
                            logger.warning("No prompt found for image, using UI prompt.")
                        else:
                            if inference_settings.controlnet_batch_find and inference_settings.controlnet_batch_replace:
                                logger.debug("Prompt: " + prompt)
                                prompt = prompt.replace(inference_settings.controlnet_batch_find,
                                                        inference_settings.controlnet_batch_replace)
                                logger.debug("Swapped Prompt: " + prompt)
                        input_prompts.append(prompt)
                        negative_prompts.append(inference_settings.negative_prompt)
                    except Exception as e:
                        logger.warning(f"Failed to preprocess image: {e}")
                        traceback.print_exc()
                        continue
        else:
            control_images.append(src_image if src_image else src_mask)
            input_prompts.append(inference_settings.prompt)
            negative_prompts.append(inference_settings.negative_prompt)

        input_prompts = input_prompts * inference_settings.num_images
        negative_prompts = negative_prompts * inference_settings.num_images
        control_images = control_images * inference_settings.num_images
        model_data.data = {"type": inference_settings.controlnet_type}

        pipeline = model_handler.load_model("diffusers_controlnet", model_data)
    else:
        input_prompts = [inference_settings.prompt] * inference_settings.num_images
        negative_prompts = [inference_settings.negative_prompt] * inference_settings.num_images
        pipeline = model_handler.load_model("diffusers", model_data)

    if pipeline is None:
        logger.warning("No model selected.")
        return [], []

    out_images = []
    out_prompts = []

    try:
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

        total_images = len(input_prompts)
        while len(out_images) < total_images:
            batch_size = inference_settings.batch_size
            required_images = total_images - len(out_images)
            if inference_settings.batch_size > 1 and required_images < inference_settings.batch_size:
                batch_size = required_images

            if status_handler.status.canceled:
                logger.debug("Canceled!")
                break

            batch_prompts = input_prompts[:batch_size]
            input_prompts = input_prompts[batch_size:]

            batch_negative = negative_prompts[:batch_size]
            negative_prompts = negative_prompts[batch_size:]

            if control_images and len(control_images) > 0:
                batch_control = control_images[:batch_size]
                control_images = control_images[batch_size:]
            else:
                batch_control = None
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
                kwargs = {"input_prompts": batch_prompts,
                          "num_inference_steps": inference_settings.steps,
                          "guidance_scale": inference_settings.scale,
                          "negative_prompt": batch_negative,
                          "generator": generator}

                if inference_settings.enable_controlnet and inference_settings.controlnet_type:
                    kwargs["image"] = batch_control

                if preview_steps > 0:
                    kwargs["callback"] = update_progress
                    kwargs["callback_steps"] = preview_steps

                if gen_height:
                    kwargs["height"] = gen_height
                if gen_width:
                    kwargs["width"] = gen_width

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    s_image = await loop.run_in_executor(pool, lambda: pipeline(**kwargs).images)

            pbar.update(len(s_image))
            paths = []
            prompts = []
            for i in range(len(s_image)):
                img = s_image[i]
                prompt = input_prompts[i]
                infer_settings = inference_settings
                infer_settings.prompt = prompt
                img_path = image_handler.db_save_image(img, "inference", inference_settings, False)
                paths.append(img_path)
                prompts.append(prompt)

            out_images.extend(paths)
            out_prompts.extend(prompts)

            status_handler.update(items={
                "status": f"Generating {len(out_images) + (1 * inference_settings.batch_size)}/{inference_settings.num_images} images."},
                send=True)


    except Exception as e:
        logger.error(f"Exception inferring: {e}")
        traceback.print_exc()
    if control_image is not None:
        out_images.append(control_image)
        out_prompts.append("Control image")
    status_handler.update(
        items={"status": f"Generation complete.", "images": out_images, "prompts": out_prompts})
    return out_images, out_prompts
