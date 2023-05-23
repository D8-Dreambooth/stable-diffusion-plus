import asyncio
import base64
import concurrent.futures
import logging
import random
import traceback
from io import BytesIO

import torch
from PIL import Image, ImageFilter
from compel import Compel
from diffusers import StableDiffusionInpaintPipeline, StableDiffusionImg2ImgPipeline, \
    StableDiffusionInpaintPipelineLegacy, DDIMScheduler

from core.dataclasses.infer_data import InferSettings
from core.handlers.config import ConfigHandler
from core.handlers.images import ImageHandler
from core.handlers.model_types.controlnet_processors import model_data as controlnet_data, preprocess_image
from core.handlers.models import ModelHandler
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler
from core.modules.dreambooth.helpers.mytqdm import mytqdm

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
    status_handler.start(inference_settings.num_images * inference_settings.steps, "Starting inference.")
    await status_handler.send_async()
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

    if inference_settings.use_sag:
        model_data.data = {"use_sag": True}

    # If we're using controlnet, set up images and preprocessing
    if inference_settings.enable_controlnet and inference_settings.controlnet_type:
        for cd in controlnet_data:
            if cd["name"] == inference_settings.controlnet_type:
                preprocess_src = cd["image_type"]
                break

        if inference_settings.controlnet_batch:
            # List files in the batch directory
            batch_dir = inference_settings.controlnet_batch_dir
            image_handler = ImageHandler(user_name=user)
            images, image_data = image_handler.load_image(batch_dir, None, True)

            # Get the images and prompts
            img_idx = 0

            for image_path in images:
                image = Image.open(image_path)
                img_prompt = None
                if len(image_data) > img_idx:
                    img_prompt = image_data[img_idx]["prompt"] if "prompt" in image_data[img_idx] else None
                if not img_prompt and inference_settings.controlnet_batch_use_prompt:
                    logger.warning("No prompt found for image, using UI prompt.")
                else:
                    if inference_settings.controlnet_batch_find and inference_settings.controlnet_batch_replace:
                        find = inference_settings.controlnet_batch_find
                        find_phrases = [f"a {find}", f"an {find}", f"the {find}", f"{find}"]
                        img_prompt = ",".join([img_prompt, inference_settings.prompt])
                        for phrase in find_phrases:
                            img_prompt = img_prompt.replace(phrase, inference_settings.controlnet_batch_replace)

                control_images.append(image)
                img_idx += 1
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
                    control_images.append(src_image)
            elif preprocess_src == "mask":
                if not src_mask:
                    logger.warning("No mask to preprocess.")
                    return
                else:
                    control_images.append(src_mask)
            else:
                control_images.append(src_image if src_image else src_mask)
        status_handler.update("status", "Preprocessing control images.")
        await status_handler.send_async()
        logger.debug("Sending status(1)")
        status_handler.send()
        max_res = int(ch.get_item("max_resolution", "infer", 512))
        control_images, input_prompts = preprocess_image(control_images,
                                                         prompt=input_prompts,
                                                         model_name=inference_settings.controlnet_type,
                                                         max_res=max_res,
                                                         process=inference_settings.controlnet_preprocess,
                                                         handler=status_handler)

        negative_prompts = [inference_settings.negative_prompt] * len(control_images)
    else:
        input_prompts = [inference_settings.prompt]
        negative_prompts = [inference_settings.negative_prompt]

    status_handler.update("status", "Loading model.")
    logger.debug("Sending status(2)")

    await status_handler.send_async()
    if len(inference_settings.loras):
        model_data.data["loras"] = inference_settings.loras
        model_data.data["lora_weight"] = inference_settings.lora_weight
    if inference_settings.vae is not None:
        try:
            model_data.data["vae"] = inference_settings.vae["path"]
            logger.debug(f"Set custom VAE: {inference_settings.vae['path']}")
        except Exception as e:
            logger.debug(f"Unable to parse VAE JSON: {e}")
    logger.debug("Sent")
    pipeline = model_handler.load_model("diffusers", model_data)

    if not pipeline:
        logger.warning("No model selected.")
        status_handler.update("status", "Unable to load inference pipeline.")
        return [], []

    compel_proc = Compel(tokenizer=pipeline.tokenizer, text_encoder=pipeline.text_encoder, truncate_long_prompts=False)
    input_prompts = input_prompts * inference_settings.num_images
    negative_prompts = negative_prompts * inference_settings.num_images

    if len(control_images):
        gen_height = 0
        gen_width = 0
        control_images = control_images * inference_settings.num_images
    total_images = len(input_prompts)

    out_images = []
    out_prompts = []
    original_controls = []
    used_controls = []
    try:
        status_handler.update(
            items={
                "status": f"Generating {len(out_images) + (1 * inference_settings.batch_size)}/{total_images} images."})
        initial_seed = inference_settings.seed
        # If the seed is a string, parse it
        if isinstance(inference_settings.seed, str):
            initial_seed = int(inference_settings.seed)

        pbar = mytqdm(desc="Making images.", total=total_images, user=user, target="infer", index=1)

        def update_progress(step: int, timestep: int, latents: torch.FloatTensor):
            # Move the latents tensor to CPU if it's on a different device
            converted = None
            try:
                latent = pipeline.decode_latents(latents)
                if torch.is_tensor(latent):  # Check if it's a PyTorch tensor
                    latent = latent.squeeze().permute(1, 2, 0).cpu().numpy()
                    latent = (latent.max() - latent) * 255  # Adjust the range of values
                    latent = latent.round().clip(0, 255).astype("uint8")
                converted = pipeline.numpy_to_pil(latent)
            except Exception as e:
                logger.debug(f"Unable to convert latents to image: {e}")
                traceback.print_exc()
            # Update the progress status handler with the new items
            status_handler.update(items={
                "latents": converted,
                "progress_2_total": inference_settings.steps,
                "progress_2_current": step,
            }, send=True)

        total_images = len(input_prompts)
        used_controls = []
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
                used_controls.extend(batch_control)
                use_embeds = False
            else:
                batch_control = []
            if initial_seed is None:
                initial_seed = -1
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

                if inference_settings.use_sag:
                    kwargs["sag_scale"] = 1.0
                logger.debug(f"Mode: {inference_settings.mode}")
                skip_modes = ["img2img", "inpaint", "depth2img"]
                if inference_settings.mode in skip_modes and inference_settings.infer_image is not None:
                    # Load PIL Image from data:image/png
                    image_data = base64.b64decode(inference_settings.infer_image.split(",")[1])
                    # Create PIL Image object
                    image = Image.open(BytesIO(image_data)).convert("RGB")
                    kwargs["image"] = image
                    if inference_settings.mode == "img2img":
                        kwargs["strength"] = inference_settings.denoise_strength
                else:
                    if gen_height > 0:
                        kwargs["height"] = gen_height
                    if gen_width > 0:
                        kwargs["width"] = gen_width
                if inference_settings.mode == "inpaint":
                    if inference_settings.infer_mask is not None:
                        mask_data = base64.b64decode(inference_settings.infer_mask.split(",")[1])
                        mask_data = Image.open(BytesIO(mask_data))
                        mask = process_mask(mask_data, inference_settings.invert_mask)
                        kwargs["mask_image"] = mask
                logger.debug(f"KWARGS: {kwargs}")
                if inference_settings.mode == "inpaint":
                    pipeline = StableDiffusionInpaintPipeline(**pipeline.components)
                elif inference_settings.mode == "img2img":
                    pipeline = StableDiffusionImg2ImgPipeline(**pipeline.components)
                    pipeline.scheduler = DDIMScheduler().from_config(pipeline.scheduler.config)

                s_image = await loop.run_in_executor(pool, lambda: pipeline(**kwargs).images)

            pbar.update(len(s_image))
            paths = []
            prompts = []
            images = []
            for i in range(len(s_image)):
                img = s_image[i]
                images.append(img)
                prompt = batch_prompts[i]
                infer_settings = inference_settings
                infer_settings.prompt = prompt
                img_path = image_handler.save_image(img, "inference", inference_settings, False)
                paths.extend(img_path)
                prompts.append(prompt)

            out_images.extend(images)
            out_prompts.extend(prompts)
            current_total = len(out_images) + (1 * inference_settings.batch_size)
            if current_total > total_images:
                current_total = total_images
            if status_handler.status.canceled:
                logger.debug("Canceled!")
                break

            status_handler.update(items=
            {
                "status": f"Generating {current_total}/{total_images} images.",
                "images": s_image,
                "prompts": prompts,
                "progress_1_total": total_images,
                "progress_1_current": current_total,
                "latents": s_image,
                "progress_2_total": inference_settings.steps,
                "progress_2_current": inference_settings.steps,
            },
                send=True)

    except Exception as e:
        logger.error(f"Exception inferring: {e}")
        traceback.print_exc()

    if len(used_controls) > 0:
        out_images.extend(used_controls)
        out_prompts.extend([f"Control image {i}" for i in range(len(used_controls))])

    status_handler.update(
        items={
            "status": f"Generation complete.",
            "images": out_images,
            "prompts": out_prompts,
            "progress_2_total": 0,
            "progress_2_current": 0
        }, send=False)
    status_handler.end("Generation complete.")
    return out_images, out_prompts


def process_mask(mask_data, invert_mask):
    # Convert image to RGBA to ensure there's an alpha (transparency) channel
    data = mask_data.getdata()

    new_data = []
    for item in data:
        # change all white (also shades of whites)
        # pixels to yellow
        if invert_mask:
            if item[3] != 0:  # non-transparent pixels
                new_data.append((255, 255, 255, 255))  # white pixel
            else:
                new_data.append(item)  # original pixel
        else:
            if item[3] == 0:  # transparent pixels
                new_data.append((255, 255, 255, 255))  # white pixel
            else:
                new_data.append(item)  # original pixel

    mask_data.putdata(new_data)

    # convert image to greyscale
    mask_data = mask_data.convert("L")

    # apply Gaussian blur
    mask_data = mask_data.filter(ImageFilter.GaussianBlur(5))

    # create a new black image
    black_background = Image.new('L', mask_data.size)
    # paste the white layer onto a black background
    black_background.paste(mask_data)

    return black_background


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
            if weight != 1.0:
                new_words.append(f"({raw_word}){weight}")
            else:
                new_words.append(raw_word)
        new_tokens.append("_".join(new_words))
    output_string = ", ".join(new_tokens)
    output_string = output_string.replace("_", " ")

    return output_string
