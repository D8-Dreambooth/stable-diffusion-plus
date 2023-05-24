import logging
import os
import re
import traceback

from PIL import Image
from fastapi import FastAPI

from core.handlers.file import FileHandler
from core.handlers.models import ModelManager
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler
from core.helpers.captioners.blip2 import Blip2Captioner
from core.helpers.captioners.blip_large import BlipLargeCaptioner
from core.helpers.captioners.wolf import ConvCaptioner, Conv2Captioner, SwinCaptioner, VitCaptioner
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


class TaggerModule(BaseModule):

    def __init__(self):
        self.name: str = "Tagger"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.name, self.path)
        mm = ModelManager()

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)

    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("save_caption", _save_caption)
        handler.register("caption_image", self._tag_image)

    async def _tag_image(self, data):
        user = data["user"]
        sh = StatusHandler(user_name=user, target="tagProgressGroup")
        logger.debug(f"Data: {data}")
        image_path = data["data"]["path"]
        captioners = data["data"]["captioners"]
        threshold = data["data"]["threshold"]
        char_threshold = data["data"]["char_threshold"]
        keep_existing = data["data"]["append_existing"] if "append_existing" in data["data"] else False
        blacklist = data["data"]["blacklist"] if "blacklist" in data["data"] else []
        if isinstance(blacklist, str):
            if "," in blacklist:
                blacklist = blacklist.split(",")
            else:
                blacklist = [blacklist]
        nb = []
        for b in blacklist:
            nb.append(b.strip())
        blacklist = nb
        logger.debug(f"Blacklist: {blacklist}")
        status = None
        if len(image_path) == 0:
            status = "No images selected."

        cap_count = 0
        for captioner in captioners:
            if captioner:
                cap_count += 1

        if not cap_count:
            status = "No captioners selected."

        if status:
            return {"status": status}

        total = cap_count * len(image_path)
        sh.start(total, f"Tagging {len(image_path)} images with {cap_count} captioners...")
        start_prompts = {
            "is_person": "is the subject a person?",
            "is_animal": "is the subject an animal?",
            "is_object": "is the subject an inanimate object?",
        }
        person_prompts = {
            "gender": "Gender:",
            "age": "Age:",
            "pose": "Pose:",
            "race": "Ethnicity:",
            "hair_color": "Hair Color:",
            "hair_style": "Hair Style:",
            "clothing": "Clothing:",
        }

        animal_prompts = {
            "type": "Type:",
            "action": "Action:",
            "species": "Species:",
            "color": "Color:",
            "age": "Age:",
        }

        object_prompts = {
            "type": "Type:",
            "color": "Color:",
            "material": "Material:",
            "usage": "Usage:",
        }

        general_prompts = {
            "subject": "Subject:",
            "background": "Background:",
            "environment": "Environment:",
            "items": "Contains:",
            "lighting": "Lighting:",
            "color_palette": "Color Palette:",
            "composition": "Composition:",
            "medium": "Medium:",
            "dominant_colors": "Dominant Colors:",
            "accent_colors": "Accent Colors:",
        }

        outputs = {}

        if captioners["blip2"]:
            sh.update(items={"status": f"Loading BLIP2 model..."})
            blip_2 = Blip2Captioner()
            s_count = 1
            for image in image_path:
                sh.step(description=f"Tagging image {s_count}/{len(image_path)} image with Blip2...")
                s_count += 1
                base = os.path.basename(image)
                raw_image = Image.open(image).convert("RGB")
                try:
                    outputs[f"blip2--{base}"] = blip_2.caption(raw_image, {}, False)
                    for key, question in start_prompts.items():
                        # IF the key is the last one in start_prompts
                        response = blip_2.caption(raw_image, {"question": question}, False)
                        outputs[f"{key}--{base}"] = response
                except:
                    logger.warning("Exception loading stuff")
                    traceback.print_exc()

                questions = {}
                if outputs[f"is_person--{base}"] == ["yes"]:
                    questions = person_prompts
                elif outputs[f"is_animal--{base}"] == ["yes"]:
                    questions = animal_prompts
                elif outputs[f"is_object--{base}"] == ["yes"]:
                    questions = object_prompts

                del outputs[f"is_person--{base}"]
                del outputs[f"is_animal--{base}"]
                del outputs[f"is_object--{base}"]

                for key, generic in general_prompts.items():
                    questions[key] = generic

                for key, question in questions.items():
                    # ask a random question.
                    response = blip_2.caption(raw_image, {"question": question}, False)
                    if response != "yes":
                        outputs[f"{key}--{base}"] = response

        logger.debug(f"Results so far: {outputs}")
        # Construct a comprehensive caption for the image
        captionerz = {
            "blip_large": BlipLargeCaptioner,
            "conv": ConvCaptioner,
            "conv2": Conv2Captioner,
            "swin": SwinCaptioner,
            "vit": VitCaptioner
        }
        for key, captioner in captionerz.items():
            if captioners[key] is False:
                continue
            sh.update(items={"status": f"Loading {key} model..."})
            captioner = captioner()
            s_count = 1
            for image in image_path:
                sh.step(description=f"Tagging image {s_count}/{len(image_path)} image with {key}...")
                s_count += 1
                base = os.path.basename(image)
                raw_image = Image.open(image).convert("RGB")
                params = {}
                if key != "blip_large":
                    params["threshold"] = threshold
                    params["char_threshold"] = char_threshold
                caption = captioner.caption(raw_image, params, False)
                if key == "blip_large":
                    cap_check = caption.split(" ")
                    # If all of the elements in the caption are the same word
                    if len(set(cap_check)) == 1:
                        caption = cap_check[0]
                logger.debug(f"Response from {key}_{base}: {caption}")
                outputs[f"{key}--{base}"] = caption

        file_outputs = {}
        for key, caption in outputs.items():
            split = key.split("--")
            real_key = split[0]
            file_name = split[1]
            if file_name not in file_outputs:
                file_outputs[file_name] = {}
            file_outputs[file_name][real_key] = caption
        file_captions = {}
        logger.debug(f"File outputs: {file_outputs}")
        for file, data in file_outputs.items():
            caption_elements = []
            caption = ""
            for key, caption in data.items():
                logger.debug(f"Checking caption ({key}): {caption}")
                cap_parts = caption.split(",")
                for part in cap_parts:
                    stripped = re.sub(r'[^a-zA-Z0-9\s]+', '', part)
                    stripped = stripped.strip()
                    if stripped != "" and stripped not in caption_elements and stripped not in blacklist:
                        caption_elements.append(stripped)
            if len(caption_elements) > 1:
                cap_out = ", ".join(caption_elements)
            elif len(caption_elements) == 1:
                cap_out = caption_elements[0]
            else:
                cap_out = caption
            file_captions[file] = cap_out
            logger.debug(f"File captions: {cap_out}")
        await update_captions(file_captions, image_path, user, keep_existing)
        sh.end("Captioning complete.")


async def _get_image(data):
    logger.debug(f"Data: {data}")
    user = data["user"]
    fh = FileHandler(user_name=user)
    image = fh.get_file(data)
    data["data"] = {"image": image}
    return data


async def update_captions(file_captions, image_path, user, append=False):
    fh = FileHandler(user_name=user)
    for image in image_path:
        base = os.path.basename(image)
        filename = os.path.splitext(base)[0] + ".txt"
        dest_dir = os.path.dirname(image)
        if base not in file_captions:
            logger.debug(f"Skipping {base} as it has no caption")
            continue
        tags = file_captions[base]
        existing = os.path.join(dest_dir, filename)
        if os.path.exists(existing) and append:
            with open(existing, "r") as f:
                existing_tags = f.read()
            tags = existing_tags + ", " + tags
        tag_items = tags.split(",")
        clean_tags = []
        for tag in tag_items:
            cleaned = tag.strip()
            if cleaned != "" and cleaned not in clean_tags:
                clean_tags.append(cleaned)
        tags = ", ".join(clean_tags) if len(clean_tags) > 1 else clean_tags[0] if len(clean_tags) == 1 else ""
        fh.save_file(dest_dir, filename, tags.encode())


async def _save_caption(data):
    logger.debug(f"Data: {data}")
    user = data["user"]
    fh = FileHandler(user_name=user)
    tags = data["data"]["caption"]
    filename = data["data"]["path"]
    dest_dir = os.path.dirname(filename)
    filename = os.path.basename(filename)
    # Replace file extension with .txt
    filename = os.path.splitext(filename)[0] + ".txt"
    # Sanitize tags
    tag_items = tags.split(",")
    clean_tags = []
    for tag in tag_items:
        cleaned = tag.strip()
        clean_tags.append(cleaned)
    tags = ", ".join(clean_tags)
    fh.save_file(dest_dir, filename, tags.encode())
    return {"status": "Saved", "caption": tags}
