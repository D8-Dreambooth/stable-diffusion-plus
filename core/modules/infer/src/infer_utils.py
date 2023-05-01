import asyncio
import concurrent.futures
import logging
import os
import random
import re
import traceback

import torch
from compel import Compel
from tqdm import tqdm

from core.dataclasses.infer_data import InferSettings
from core.handlers.config import ConfigHandler
from core.handlers.file import FileHandler, is_image
from core.handlers.images import ImageHandler
from core.handlers.model_types.controlnet_processors import model_data as controlnet_data, preprocess_image
from core.handlers.models import ModelHandler
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler

socket_handler = SocketHandler()
logger = logging.getLogger(__name__)
preview_steps = 5
pipeline = None


async def start_inference(inference_settings: InferSettings, user, target: str = None):
    global pipeline, preview_steps
    model_handler = ModelHandler(user_name=user)
    status_handler = StatusHandler(user_name=user, target=target)
    image_handler = ImageHandler(user_name=user)
    ch = ConfigHandler()
    logger.debug(f"Infer the things: {inference_settings}")
    status_handler.start(inference_settings.num_images * inference_settings.steps, "Starting inference.")
    # Check if our selected model is loaded, if not, loaded it.
    preprocess_src = None

    # List of prompts and images to pass to the actual pipeline
    input_prompts = []
    negative_prompts = []
    control_images = []

    # Height and width to use if not overridden by controlnet
    gen_height = inference_settings.height
    gen_width = inference_settings.width

    # Model data, duh
    model_data = inference_settings.model

    # Total images to process?
    total_images = 0

    # If we're using controlnet, set up images and preprocessing
    if inference_settings.enable_controlnet and inference_settings.controlnet_type:
        for cd in controlnet_data:
            if cd["name"] == inference_settings.controlnet_type:
                preprocess_src = cd["image_type"]
                break

        logger.debug("Using controlnet.")

        if inference_settings.enable_sag:
            model_data.data = {"enable_sag": True}

        if inference_settings.controlnet_batch:
            # List files in the batch directory
            logger.debug("Controlnet batch, baby!")
            batch_dir = inference_settings.controlnet_batch_dir
            file_handler = FileHandler(user_name=user)
            files = file_handler.get_dir_content(batch_dir, True, False, None)

            # Check if the files are images
            images = []

            for file in files:
                if is_image(os.path.join(file_handler.user_dir, file)):
                    images.append(file)

            # Get the images and prompts
            for image in images:
                file_req = {"data": {"files": image, "return_pil": True}}
                image_data = await file_handler.get_file(file_req)
                logger.debug(f"mage data: {image_data}")
                image = image_data["files"][0]["image"]
                img_prompt = image_data["files"][0]["data"] if "data" in image_data["files"][0] else None
                if not img_prompt and inference_settings.controlnet_batch_use_prompt:
                    logger.warning("No prompt found for image, using UI prompt.")
                else:
                    if inference_settings.controlnet_batch_find and inference_settings.controlnet_batch_replace:
                        logger.debug("Prompt: " + img_prompt)
                        img_prompt = img_prompt.replace(inference_settings.controlnet_batch_find,
                                                        inference_settings.controlnet_batch_replace)
                        img_prompt = ",".join([img_prompt, inference_settings.prompt])
                        logger.debug("Swapped Prompt: " + img_prompt)

                control_images.append(image)
                prompt_in = img_prompt if img_prompt else inference_settings.prompt
                input_prompts.append(prompt_in)
                negative_prompts.append(inference_settings.negative_prompt)
        else:
            src_image = inference_settings.get_controlnet_image()
            src_mask = inference_settings.get_controlnet_mask()
            input_prompts = [inference_settings.prompt]
            if preprocess_src == "image":
                if not src_image:
                    logger.warning("No image to preprocess.")
                    return
                else:
                    logger.debug(f"Src res: {src_image.size}")
                    control_images.append(src_image)
            elif preprocess_src == "mask":
                if not src_mask:
                    logger.warning("No mask to preprocess.")
                    return
                else:
                    control_images.append(src_mask)
            else:
                control_images.append(src_image if src_image else src_mask)

        max_res = int(ch.get_item("max_resolution", "infer", 512))
        control_images, input_prompts = preprocess_image(control_images,
                                                         prompt=input_prompts,
                                                         model_name=inference_settings.controlnet_type,
                                                         max_res=max_res,
                                                         process=inference_settings.controlnet_preprocess)
        logger.debug(f"Control images: {control_images}, prompts: {input_prompts}")

        negative_prompts = [inference_settings.negative_prompt] * len(control_images)

        model_data.data = {"type": inference_settings.controlnet_type}
        status_handler.update("status", "Loading model.")

    else:
        input_prompts = [inference_settings.prompt]
        negative_prompts = [inference_settings.negative_prompt]

    if inference_settings.mode == "txt2img":
        pipeline = model_handler.load_model("diffusers", model_data)
    elif inference_settings.mode == "inpaint":
        pipeline = model_handler.load_model("diffusers_inpaint", model_data)
    elif inference_settings.mode == "img2img":
        pipeline = model_handler.load_model("diffusers_img2img", model_data)

    compel_proc = Compel(tokenizer=pipeline.tokenizer, text_encoder=pipeline.text_encoder, truncate_long_prompts=False)

    input_prompts = input_prompts * inference_settings.num_images
    negative_prompts = negative_prompts * inference_settings.num_images

    if len(control_images):
        logger.debug("Clearing user height, using control image dims.")
        gen_height = 0
        gen_width = 0
        control_images = control_images * inference_settings.num_images
    logger.debug(f"Final prompts: {input_prompts}")
    total_images = len(input_prompts)

    if pipeline is None:
        logger.warning("No model selected.")
        status_handler.update("status", "Unable to load inference pipeline.")
        return [], []

    out_images = []
    out_prompts = []
    original_controls = []
    try:
        status_handler.update(
            items={
                "status": f"Generating {len(out_images) + (1 * inference_settings.batch_size)}/{total_images} images."})
        initial_seed = inference_settings.seed
        # If the seed is a string, parse it
        if isinstance(inference_settings.seed, str):
            initial_seed = int(inference_settings.seed)

        pbar = tqdm(desc="Making images.", total=total_images)

        def update_progress(step: int, timestep: int, latents: torch.FloatTensor):
            # Move the latents tensor to CPU if it's on a different device
            latent = pipeline.decode_latents(latents)
            converted = pipeline.numpy_to_pil(latent)
            logger.debug(f"Images are: {type(converted)}")
            # Update the progress status handler with the new items
            status_handler.update(items={
                "images": converted,
            }, send=False)
            status_handler.step(preview_steps)

        total_images = len(input_prompts)
        logger.debug(f"We need {total_images} images.")
        original_controls = control_images
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

            embed_prompts = []
            use_embeds = False
            for bp in batch_prompts:
                parsed = parse_prompt(bp)
                if parsed != bp:
                    use_embeds = True
                embed_prompts.append(parsed)

            embed_negative_prompts = []
            for np in batch_negative:
                parsed = parse_prompt(np)
                if parsed != np:
                    use_embeds = True
                embed_negative_prompts.append(parsed)

            if control_images and len(control_images) > 0:
                batch_control = control_images[:batch_size]
                control_images = control_images[batch_size:]
            else:
                batch_control = []
            if initial_seed == -1:
                seed = int(random.randrange(21474836147))
            else:
                if len(out_images) > 0:
                    initial_seed = initial_seed + 1
                if initial_seed > 21474836147:
                    initial_seed = int(random.randrange(21474836147))
                seed = initial_seed
            inference_settings.seed = seed
            generator = torch.manual_seed(seed)
            loop = asyncio.get_event_loop()
            # Here's the magic sauce
            preview_steps = ch.get_item("preview_steps", default=5)
            if preview_steps > inference_settings.steps:
                preview_steps = inference_settings.steps
            with concurrent.futures.ThreadPoolExecutor() as pool:
                if use_embeds:
                    conditioning = compel_proc(embed_prompts)
                    negative_conditioning = compel_proc(embed_negative_prompts)
                    [conditioning, negative_conditioning] = compel_proc.pad_conditioning_tensors_to_same_length(
                        [conditioning, negative_conditioning])
                    kwargs = {"prompt_embeds": conditioning,
                              "num_inference_steps": inference_settings.steps,
                              "guidance_scale": inference_settings.scale,
                              "negative_prompt_embeds": negative_conditioning,
                              "generator": generator}
                else:
                    kwargs = {"prompt": batch_prompts,
                              "num_inference_steps": inference_settings.steps,
                              "guidance_scale": inference_settings.scale,
                              "negative_prompt": batch_negative,
                              "generator": generator}

                if len(batch_control):
                    kwargs["image"] = batch_control

                if preview_steps > 0:
                    kwargs["callback"] = update_progress
                    kwargs["callback_steps"] = preview_steps

                if gen_height > 0:
                    kwargs["height"] = gen_height
                if gen_width > 0:
                    kwargs["width"] = gen_width
                logger.debug(f"kwargs: {kwargs}")
                s_image = await loop.run_in_executor(pool, lambda: pipeline(**kwargs).images)

            pbar.update(len(s_image))
            paths = []
            prompts = []
            for i in range(len(s_image)):
                img = s_image[i]
                prompt = batch_prompts[i]
                infer_settings = inference_settings
                infer_settings.prompt = prompt
                img_path = image_handler.save_image(img, "inference", inference_settings, False)
                paths.extend(img_path)
                prompts.append(prompt)

            out_images.extend(paths)
            out_prompts.extend(prompts)
            current_total = len(out_images) + (1 * inference_settings.batch_size)
            if current_total > total_images:
                current_total = total_images
            status_handler.update(items={
                "status": f"Generating {current_total}/{total_images} images."},
                send=True)

    except Exception as e:
        logger.error(f"Exception inferring: {e}")
        traceback.print_exc()

    if original_controls is not None:
        out_images.extend(original_controls)
        for img in original_controls:
            out_prompts.append("Control image")
    status_handler.update(
        items={"status": f"Generation complete.", "images": out_images, "prompts": out_prompts})
    return out_images, out_prompts


def parse_prompt(input_string):
    input_string = input_string.replace(" ", "_")
    tokens = input_string.split(",")
    new_tokens = []
    for token in tokens:
        words = token.split("_")
        new_words = []
        for word in words:
            matched = False
            stripped = word.strip()
            if stripped == "":
                continue
            weight = 1.0
            raw_word = stripped
            if "(" in stripped and ")" in stripped:
                if ":" in stripped:
                    try:
                        weight = float(stripped.split(":")[1].replace(")", ""))
                        raw_word = stripped.replace(f":{weight}", "").replace("(", "").replace(")", "")
                    except:
                        raw_word = stripped
                else:
                    matched = True
                    # Set the weight to 1.1 to the power of the number of open parens
                    weight = 1.1 ** stripped.count("(")
                    raw_word = stripped.replace("(", "").replace(")", "")
            if "[" in stripped and "]" in stripped:
                weight = 0.9 ** stripped.count("[")
                raw_word = stripped.replace("[", "").replace("]", "")
            weight = max(0.0, min(2.0, weight))
            if matched:
                logger.debug(f"Matched {stripped} to {raw_word} with weight {weight}")
            if weight != 1.0:
                new_words.append(f"({raw_word}){weight}")
            else:
                new_words.append(raw_word)
        new_tokens.append("_".join(new_words))
    output_string = ", ".join(new_tokens)
    output_string = output_string.replace("_", " ")

    return output_string
