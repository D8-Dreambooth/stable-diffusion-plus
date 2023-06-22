import asyncio
import base64
import concurrent.futures
import gc
import importlib
import inspect
import logging
import math
import pkgutil
import random
import traceback
from io import BytesIO

import numpy as np
import torch
from PIL import Image, ImageFilter, ImageDraw
from compel import Compel

import core.helpers.upscalers
from core.dataclasses.infer_settings import InferSettings
from core.handlers.config import ConfigHandler
from core.handlers.images import ImageHandler, scale_image
from core.handlers.model_types.controlnet_processors import controlnet_models as controlnet_data, preprocess_image
from core.handlers.model_types.diffusers_loader import get_pipeline_parameters
from core.handlers.models import ModelHandler
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler
from core.helpers.upscalers.base_upscaler import BaseUpscaler
from core.helpers.upscalers.img2img_upscaler import Img2ImgUpscaler
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
    max_res = int(ch.get_item_protected("max_resolution", "infer", 512))

    logger.debug(f"Starting inference with settings: {inference_settings}")
    status_handler.start(inference_settings.num_images * inference_settings.steps, "Starting inference.")
    await status_handler.send_async()
    # Check if our selected model is loaded, if not, loaded it.
    preprocess_src = None

    # List of prompts and images to pass to the actual pipeline
    input_prompts = []
    negative_prompts = []
    control_images = []

    # Height and width to use if not overridden by controlnet
    ui_height = inference_settings.height
    ui_width = inference_settings.width
    logger.debug(f"UI height: {ui_height}, width: {ui_width}")
    # Model data, duh
    model_data = inference_settings.model
    pipeline_type = inference_settings.pipeline
    pipe_settings = inference_settings.pipeline_settings

    processor = None
    return_latents = False
    if inference_settings.postprocess:
        processor = Img2ImgUpscaler(inference_settings.postprocess_scale, model_data, pipeline)

    logger.debug(f"Pipeline settings: {pipe_settings}")
    pipe_params = {}
    if pipeline_type != "auto":
        pipe_data = get_pipeline_parameters()
        pipe_params = pipe_data.get(pipeline_type, {})
    model_data.data["pipeline"] = pipeline_type
    logger.debug(f"Pipe params: {pipe_params}")
    # If we're using controlnet, set up images and preprocessing
    if "ControlNet" in pipeline_type and inference_settings.controlnet_type:
        for key, cd in controlnet_data.items():
            if cd["name"] == inference_settings.controlnet_type:
                preprocess_src = cd["image_type"][0]
                logger.debug(f"Using controlnet: {cd} and {preprocess_src}")
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
                    logger.debug("Appending source image")
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
        logger.debug(f"Control images-pre-preprocess: {len(control_images)}")
        control_images, input_prompts = preprocess_image(control_images,
                                                         prompt=input_prompts,
                                                         model_name=inference_settings.controlnet_type,
                                                         width=inference_settings.width,
                                                         height=inference_settings.height,
                                                         process=inference_settings.controlnet_preprocess,
                                                         resize_mode=inference_settings.controlnet_scale_mode,
                                                         handler=status_handler)
        prompt_count = len(input_prompts)
        logger.debug("Control images post-preprocess: %s", len(control_images))
        negative_prompts = [inference_settings.negative_prompt] * len(control_images)
    else:
        # If newlines are in the prompt, split it up
        if "\n" in inference_settings.prompt:
            prompts = inference_settings.prompt.split("\n")
            for p in prompts:
                if p.strip() != "":
                    input_prompts.append(p.strip())
            prompt_count = len(prompts)
        else:
            input_prompts = [inference_settings.prompt]
            prompt_count = 1
        # If newlines are in the negative prompt, split it up
        if "\n" in inference_settings.negative_prompt:
            prompts = inference_settings.negative_prompt.split("\n")
            for p in prompts:
                if p.strip() != "":
                    negative_prompts.append(p.strip())
        else:
            negative_prompts = [inference_settings.negative_prompt]

    logger.debug(f"We have {len(control_images)} control images.")

    # Make sure we have the same number of prompts as negative prompts
    if len(input_prompts) > len(negative_prompts):
        for i in range(len(input_prompts) - len(negative_prompts)):
            negative_prompts.append(inference_settings.negative_prompt)
    elif len(negative_prompts) > len(input_prompts):
        for i in range(len(negative_prompts) - len(input_prompts)):
            input_prompts.append(inference_settings.prompt)

    status_handler.update("status", "Loading model.")
    logger.debug("Sending status(2)")

    await status_handler.send_async()
    if len(inference_settings.loras):
        model_data.data["loras"] = inference_settings.loras
        model_data.data["lora_weight"] = inference_settings.lora_weight

    if "ControlNet" in inference_settings.pipeline and inference_settings.controlnet_type:
        model_data.data["controlnet_type"] = inference_settings.controlnet_type

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

    if ui_height > 768 or ui_width > 768:
        try:
            pipeline.vae.enable_tiling()
        except Exception as e:
            logger.warning(f"Unable to enable VAE tiling: {e}")
            pass
    compel_proc = Compel(tokenizer=pipeline.tokenizer, text_encoder=pipeline.text_encoder, truncate_long_prompts=False)
    input_prompts = [val for val in input_prompts for _ in range(inference_settings.num_images)]
    negative_prompts = [val for val in negative_prompts for _ in range(inference_settings.num_images)]

    if len(control_images) and "ControlNet" in inference_settings.pipeline:
        ui_height = 0
        ui_width = 0
        control_images = [val for val in control_images for _ in range(inference_settings.num_images)]

    total_images = len(input_prompts)
    logger.debug(f"Input prompts: {input_prompts}")
    out_images = []
    out_prompts = []
    used_controls = []
    try:
        if inference_settings.postprocess and processor is not None:
            total_steps = inference_settings.steps + inference_settings.postprocess_steps
        else:
            total_steps = inference_settings.steps

        status_handler.update(
            items={
                "status": f"Generating {len(out_images) + (1 * inference_settings.batch_size)}/{total_images} images.",
                "progress_2_total": total_steps
            })
        initial_seed = inference_settings.seed
        # If the seed is a string, parse it
        if isinstance(inference_settings.seed, str):
            initial_seed = int(inference_settings.seed)

        if initial_seed is None:
            initial_seed = -1
        if initial_seed == -1:
            initial_seed = int(random.randrange(21474836147))
        logger.debug("Initial seed: %s", initial_seed)

        pbar = mytqdm(
            desc="Making images.",
            total=total_images,
            user=user,
            target="infer",
            index=1,
        )

        def update_progress(step: int, timestep: int, latents: torch.FloatTensor):
            """
            Updates the progress status of the Dreambooth processes. Converts the latents tensor to a numpy array and then to a PIL image.
            Updates the progress status handler with the new items, including the converted latents, total number of steps and current step.
            @param step: int
            @param timestep: int
            @param latents: torch.FloatTensor
            @return: None
            """
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
            status_handler.step(preview_steps, True)
            status_handler.update(items={
                "latents": converted
            }, send=True)

        total_images = len(input_prompts)
        used_controls = []
        use_embeds = "prompt_embeds" in pipe_params

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
            embed_negative_prompts = []

            if use_embeds:
                for bp in batch_prompts:
                    parsed = parse_prompt(bp)
                    if parsed != bp:
                        embed_prompts.append(parsed)

                for np in batch_negative:
                    parsed = parse_prompt(np)
                    if parsed != np or len(embed_prompts) != 0:
                        embed_negative_prompts.append(parsed)

            if not len(embed_prompts) and not len(embed_negative_prompts):
                use_embeds = False

            if control_images and len(control_images) > 0:
                batch_control = control_images[:batch_size]
                control_images = control_images[batch_size:]
                used_controls.extend(batch_control)
            else:
                batch_control = []

            infer_seed = initial_seed
            if len(out_images) % prompt_count == 0 and len(out_images) > 0:
                infer_seed = infer_seed + int(len(out_images) / prompt_count)
            if infer_seed > 21474836147:
                infer_seed = 21474836147 - infer_seed
            logger.debug("Using seed: %s", infer_seed)
            inference_settings.seed = infer_seed
            generator = torch.Generator(device='cuda')
            generator.manual_seed(infer_seed)
            # Set the generator to the same device as inference pipe

            loop = asyncio.get_event_loop()
            # Here's the magic sauce
            preview_steps = ch.get_item("preview_steps", default=5)
            if preview_steps > inference_settings.steps:
                preview_steps = inference_settings.steps
            with concurrent.futures.ThreadPoolExecutor() as pool:
                kwargs = {"prompt": batch_prompts,
                          "num_inference_steps": inference_settings.steps,
                          "guidance_scale": inference_settings.scale,
                          "negative_prompt": batch_negative,
                          "generator": generator}
                if use_embeds:
                    conditioning = compel_proc(embed_prompts)
                    negative_conditioning = compel_proc(embed_negative_prompts)
                    [conditioning, negative_conditioning] = compel_proc.pad_conditioning_tensors_to_same_length(
                        [conditioning, negative_conditioning])
                    kwargs["prompt_embeds"] = conditioning
                    kwargs["negative_prompt_embeds"] = negative_conditioning

                if preview_steps > 0:
                    kwargs["callback"] = update_progress
                    kwargs["callback_steps"] = preview_steps

                for key, value in pipe_settings.items():
                    if key == "controlnet_conditioning_scale":
                        logger.debug("Converting conditioning scale to float")
                        value = [float(value)]
                        kwargs[key] = value

                    kwargs[key] = value

                if len(batch_control) and "ControlNet" in inference_settings.pipeline:
                    control_keys = ["controlnet_conditioning_image", "control_image", "image"]
                    img_key = "image"
                    for key in control_keys:
                        if key in pipe_params:
                            logger.debug(f"Using {key} for control image")
                            kwargs[img_key] = batch_control
                            if inference_settings.use_control_resolution and not inference_settings.use_input_resolution:
                                ui_width, ui_height = batch_control[0].size
                            break

                logger.debug(f"Mode: {inference_settings.pipeline}")

                if "mask_image" in pipe_params and inference_settings.mask != "":
                    mask_data = base64.b64decode(inference_settings.mask.split(",")[1])
                    mask_data = Image.open(BytesIO(mask_data))
                    mask = process_mask(mask_data, inference_settings.invert_mask)
                    mask = scale_image(mask, inference_settings.width, inference_settings.height,
                                       resize_mode=inference_settings.scale_mode)
                    for check in ["control_image", "controlnet_conditioning_image", "image"]:
                        if check in kwargs:
                            if isinstance(kwargs[check], list):
                                mask = [mask]
                                break
                    kwargs["mask_image"] = mask

                if "image" in pipe_params and inference_settings.image != "" and "image" not in kwargs:
                    logger.debug("Using infer_image from input params for image, dimensions.")
                    image_data = base64.b64decode(inference_settings.image.split(",")[1])
                    image = Image.open(BytesIO(image_data))
                    mask = None
                    # if "mask_image" in kwargs:
                    #     mask = kwargs["mask_image"]
                    #     if isinstance(mask, list):
                    #         mask = mask[0]
                    # image, new_mask = fill_image(image, mask=mask, fill_mode="noise")
                    # if mask is not None:
                    #     kwargs["mask_image"] = new_mask if not isinstance(new_mask, list) else [new_mask]
                    if inference_settings.use_input_resolution and image is not None:
                        ui_width, ui_height = image.size

                    if "control_image" in kwargs:
                        if isinstance(kwargs["control_image"], list):
                            image = [image]
                    if "controlnet_conditioning_image" in kwargs:
                        if isinstance(kwargs["controlnet_conditioning_image"], list):
                            image = [image]

                    kwargs["image"] = image

                if "height" in pipe_params and "width" in pipe_params or inference_settings.pipeline == "auto":
                    if ui_height > 0:
                        kwargs["height"] = ui_height
                    if ui_width > 0:
                        kwargs["width"] = ui_width

                for key, value in pipe_params.items():
                    if key not in kwargs and key not in ["negative_prompt", "prompt_embeds",
                                                         "negative_prompt_embeds"]:
                        if isinstance(value, dict):
                            real_value = value.get("value", None)
                        else:
                            real_value = value
                        logger.debug(f"Adding missing param: {key} with value: {real_value}")
                        kwargs[key] = real_value

                keys_to_remove = ["cls"]
                common_keys = ["generator", "num_inference_steps", "guidance_scale", "callback", "callback_steps",
                               "prompt"]
                for key, value in kwargs.items():
                    if (key not in pipe_params and key not in common_keys) or key == "DOCSTRING":
                        if (
                                key == "height" or key == "width" or key == "negative_prompt") and inference_settings.pipeline == "auto":
                            continue
                        logger.debug("Deleting extra key: " + key)
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    if key in kwargs:
                        del kwargs[key]

                if "negative_prompt_embeds" in kwargs and "negative_prompt" in kwargs:
                    del kwargs["negative_prompt"]

                if "prompt_embeds" in kwargs and "prompt" in kwargs:
                    del kwargs["prompt"]

                if "Inpaint" in inference_settings.pipeline and "Legacy" not in inference_settings.pipeline:
                    logger.debug("Inpainting mode, Fixng lists.")
                    if not isinstance(kwargs["image"], list):
                        kwargs["image"] = [kwargs["image"]]
                    if not isinstance(kwargs["mask_image"], list):
                        kwargs["mask_image"] = [kwargs["mask_image"]]

                if inference_settings.postprocess and processor is not None and return_latents:
                    kwargs["output_type"] = "latent"

                logger.debug(f"KWARGS: {kwargs}")

                s_image = await loop.run_in_executor(pool, lambda: pipeline(**kwargs).images)

            pbar.update(len(s_image))
            paths = []
            prompts = []
            images = []
            processed = []
            for i in range(len(s_image)):
                img = s_image[i]
                prompt = batch_prompts[i]
                infer_settings = inference_settings
                infer_settings.prompt = prompt
                if inference_settings.postprocess and processor is not None:
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        status_items = {
                            "status": f"Postprocessing image {i + 1} of {len(s_image)}",
                            "progress_2_current": inference_settings.steps
                        }
                        if not return_latents:
                            status_items["latents"] = img

                        status_handler.update(items=status_items, send=False)
                        logger.debug("Upscaling")
                        img = await loop.run_in_executor(pool,
                                                         lambda: processor.upscale(img, infer_settings, update_progress,
                                                                                   preview_steps))
                        logger.debug(f"Image {i} type is: " + str(type(img)))
                logger.debug(f"Appending image {i}.")
                images.append(img)
                img_path = image_handler.save_image(img, "inference", inference_settings, False)
                paths.extend(img_path)
                prompts.append(prompt)
            out_images.extend(images)
            out_prompts.extend(prompts)
            if "mask_image" in kwargs:
                out_images.extend(kwargs["mask_image"])
            current_total = len(out_images) + (1 * inference_settings.batch_size)
            if current_total > total_images:
                current_total = total_images
            if status_handler.status.canceled:
                logger.debug("Canceled!")
                break

            status_handler.update(items=
            {
                "status": f"Generating {current_total}/{total_images} images.",
                "images": images,
                "prompts": prompts,
                "progress_1_total": total_images,
                "progress_1_current": current_total,
                "latents": s_image,
                "progress_2_total": total_steps,
                "progress_2_current": total_steps,
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


def list_postprocessors():
    postprocessors = {}

    package = core.helpers.upscalers
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f'{package.__name__}.{modname}')
        for name, obj in inspect.getmembers(module):
            logger.debug(f"Checking {name}")
            if inspect.isclass(obj) and issubclass(obj, BaseUpscaler) and obj != BaseUpscaler:
                postprocessors[name] = obj

    return postprocessors


def fill_image(image: Image, mask: Image = None, fill_mode: str = "noise"):
    # Convert the image into an array
    image_array = np.array(image)

    # Check if the image has an alpha channel
    if image_array.shape[-1] == 4:
        mask_array = image_array[..., 3] == 0
    else:
        if mask is not None:
            # Convert the mask into an array
            mask_array = np.array(mask)
        else:
            logger.warning("Image does not have an alpha channel, fill mode will be ignored.")
            return image.convert("RGB"), None

    # Generate a new random mask
    new_mask = random_mask(image_array.shape[0])  # Assuming image is square

    # Combine the new mask with the existing mask if provided
    if mask is not None:
        # If the existing mask is not binary, adjust this part accordingly
        combined_mask = np.logical_or(mask_array, new_mask)
    else:
        combined_mask = new_mask

    if fill_mode == "black":
        # Set RGB values to 0 for masked pixels
        image_array[combined_mask] = 0
        image_array[..., 3][combined_mask] = 255
    elif fill_mode == "random":
        # Generate random RGB values for masked pixels
        for i in range(3):
            image_array[..., i][combined_mask] = np.random.randint(0, 256, np.sum(combined_mask))
        image_array[..., 3][combined_mask] = 255
    elif fill_mode == "noise":
        # Generate Gaussian noise for masked pixels
        for i in range(3):
            image_array[..., i][combined_mask] = np.clip(np.random.normal(128, 50, np.sum(combined_mask)), 0,
                                                         255).astype(np.uint8)
        image_array[..., 3][combined_mask] = 255
    else:
        raise ValueError(f"Invalid fill_mode: {fill_mode}")

    # Convert the arrays back to images and return them
    return Image.fromarray(image_array).convert("RGB"), Image.fromarray(combined_mask * 255).convert(
        "RGB") if mask is not None else None


def random_brush(
        max_tries: int,
        s: int,
        min_num_vertex: int = 4,
        max_num_vertex: int = 18,
        mean_angle: float = 2 * math.pi / 5,
        angle_range: float = 2 * math.pi / 15,
        min_width: int = 12,
        max_width: int = 48) -> np.ndarray:
    H, W = s, s
    average_radius = math.sqrt(H * H + W * W) / 8
    mask = Image.new('L', (W, H), 0)

    for _ in range(np.random.randint(max_tries)):
        num_vertex = np.random.randint(min_num_vertex, max_num_vertex)
        angle_min = mean_angle - np.random.uniform(0, angle_range)
        angle_max = mean_angle + np.random.uniform(0, angle_range)
        angles = []
        vertex = []

        for i in range(num_vertex):
            if i % 2 == 0:
                angles.append(2 * math.pi - np.random.uniform(angle_min, angle_max))
            else:
                angles.append(np.random.uniform(angle_min, angle_max))

        h, w = mask.size
        vertex.append((int(np.random.randint(0, w)), int(np.random.randint(0, h))))

        for i in range(num_vertex):
            r = np.clip(np.random.normal(loc=average_radius, scale=average_radius // 2), 0, 2 * average_radius)
            new_x = np.clip(vertex[-1][0] + r * math.cos(angles[i]), 0, w)
            new_y = np.clip(vertex[-1][1] + r * math.sin(angles[i]), 0, h)
            vertex.append((int(new_x), int(new_y)))

        draw = ImageDraw.Draw(mask)
        width = int(np.random.uniform(min_width, max_width))
        draw.line(vertex, fill=1, width=width)

        for v in vertex:
            draw.ellipse((v[0] - width // 2, v[1] - width // 2, v[0] + width // 2, v[1] + width // 2), fill=1)

        if np.random.random() > 0.5:
            mask.transpose(Image.FLIP_LEFT_RIGHT)

        if np.random.random() > 0.5:
            mask.transpose(Image.FLIP_TOP_BOTTOM)

        mask = np.asarray(mask, np.uint8)

        if np.random.random() > 0.5:
            mask = np.flip(mask, 0)

        if np.random.random() > 0.5:
            mask = np.flip(mask, 1)

    return mask


def random_mask(s: int, hole_range=None) -> np.ndarray:
    if hole_range is None:
        hole_range = [0, 1]
    coef = min(hole_range[0] + hole_range[1], 1.0)

    while True:
        mask = np.ones((s, s), np.uint8)

        def fill(max_size):
            w, h = np.random.randint(max_size), np.random.randint(max_size)
            ww, hh = w // 2, h // 2
            x, y = np.random.randint(-ww, s - w + ww), np.random.randint(-hh, s - h + hh)
            mask[max(y, 0): min(y + h, s), max(x, 0): min(x + w, s)] = 0

        def multi_fill(max_tries, max_size):
            for _ in range(np.random.randint(max_tries)):
                fill(max_size)

        multi_fill(int(4 * coef), s // 2)
        multi_fill(int(2 * coef), s)

        mask = np.logical_and(mask, 1 - random_brush(int(8 * coef), s))  # hole denoted as 0, reserved as 1
        hole_ratio = 1 - np.mean(mask)

        if hole_range is not None and (hole_ratio <= hole_range[0] or hole_ratio >= hole_range[1]):
            continue

        return mask[np.newaxis, ...].astype(np.float32)


def process_mask(mask_data, invert_mask=False):
    """
    Processes the mask data by converting the image to RGBA format to ensure an alpha channel exists.
    Changes all white pixels to yellow if invert_mask is True, otherwise changes all transparent pixels to white.
    Converts the image to greyscale and applies a Gaussian blur.
    Creates a new black image and pastes the white layer onto it.
    @param mask_data: PIL.Image
    @param invert_mask: bool
    @return: PIL.Image
    """
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
    """
    Parses the input string by replacing spaces with underscores and splitting the string by commas.
    For each token, splits it by underscores and processes each word.
    If the word contains parentheses, sets the weight to 1.1 raised to the power of the number of open parentheses.
    If the word contains square brackets, sets the weight to 0.9 raised to the power of the number of square brackets.
    Returns the output string with spaces instead of underscores.
    @param input_string: str
    @return: str
    """
    input_string = input_string.replace(" ", "_")
    tokens = input_string.split(",")
    new_tokens = []
    for token in tokens:
        words = token.split("_")
        new_words = []
        for word in words:
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
