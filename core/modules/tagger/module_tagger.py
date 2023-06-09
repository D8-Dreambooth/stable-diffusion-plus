import base64
import io
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
from core.modules.tagger.src.cloud_builder import make_cloud

logger = logging.getLogger(__name__)


class TaggerModule(BaseModule):

    def __init__(self):
        self.id = "tagger"
        self.name: str = "Tagger"
        self.path = os.path.abspath(os.path.dirname(__file__))
        super().__init__(self.id, self.name, self.path)
        mm = ModelManager()

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)

    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("save_caption", _save_caption)
        handler.register("caption_image", self._tag_image)
        handler.register("tag_cloud", self._tag_cloud)
        handler.register("tag_delete", self._tag_delete)

    async def _tag_delete(self, data):
        image_dir = data["data"]["path"]
        recurse = data["data"]["recurse"]
        tag = data["data"]["tag"]
        logger.debug(f"Deleting tag {tag} from {image_dir}")
        updated = {}
        for root, dirs, files in os.walk(image_dir):
            for file in files:
                if file.endswith(".txt"):
                    file_path = os.path.join(root, file)
                    logger.debug(f"Checking {file_path}")
                    # Read the whole file, split by "," and remove whitespace
                    with open(file_path, "r") as f:
                        contents = f.read()
                        tags = [t.strip() for t in contents.split(",")]
                    if tag in tags:
                        logger.debug(f"Removing {tag} from {file_path}")
                        tags.remove(tag)
                        with open(file_path, "w") as f:
                            f.write(", ".join(tags))
                        updated[file_path] = ", ".join(tags)
            if not recurse:
                dirs.clear()

        output = {}
        for updated_file, tags in updated.items():
            # Find the image file, regardless of extension, by checking the parent directory for names that match
            # the file name
            parent_dir = os.path.dirname(updated_file)
            file_name = os.path.basename(updated_file)
            for file in os.listdir(parent_dir):
                if file.startswith(file_name) and ".txt" not in file:
                    image_file = os.path.join(parent_dir, file)
                    output[image_file] = tags
                    break

        return {"updated": output}

    async def _tag_cloud(self, data):
        image_dir = data["data"]["path"]
        recurse = data["data"]["recurse"]
        img, tags = make_cloud(image_dir, recurse)

        # Convert the PIL Image to a byte stream
        cloud_dict = {}
        with io.BytesIO() as output:
            img.save(output, format="JPEG")
            contents = output.getvalue()
            cloud_dict["src"] = f"data:image/jpeg;base64,{base64.b64encode(contents).decode()}"
        cloud_dict["tags"] = tags

        return cloud_dict

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
        whitelist = data["data"]["whitelist"] if "whitelist" in data["data"] else []
        my_lists = [blacklist, whitelist]
        for list_idx in range(len(my_lists)):
            check_list = my_lists[list_idx]
            out_list = []
            if isinstance(check_list, str):
                if "\n" in check_list:
                    out_list = check_list.split("\n")
                else:
                    out_list.append(check_list)
            elif isinstance(check_list, list):
                out_list = check_list
            cleaned = []
            for line in out_list:
                if "," in line:
                    lines = line.split(",")
                else:
                    lines = [line]
                for l in lines:
                    stripped = l.strip()
                    if stripped:
                        cleaned.append(stripped)

            check_list = cleaned
            my_lists[list_idx] = check_list
        blacklist, whitelist = my_lists

        logger.debug(f"Whitelist: {whitelist}")
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
                    new_caption = [cap_check[0]]  # Start with the first word
                    for i in range(1, len(cap_check)):
                        if cap_check[i] != cap_check[i - 1]:
                            new_caption.append(cap_check[i])
                    caption = ' '.join(new_caption)

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
                        if len(whitelist) and stripped not in whitelist:
                            continue
                        caption_elements.append(stripped)
            if len(caption_elements) > 1:
                cap_out = ", ".join(caption_elements)
            elif len(caption_elements) == 1:
                cap_out = caption_elements[0]
            else:
                cap_out = caption
            file_captions[file] = cap_out
            logger.debug(f"File captions: {cap_out}")
        await update_captions(file_captions, image_path, user, keep_existing, blacklist)
        sh.end("Captioning complete.")


async def _get_image(data):
    logger.debug(f"Data: {data}")
    user = data["user"]
    fh = FileHandler(user_name=user)
    image = fh.get_file(data)
    data["data"] = {"image": image}
    return data


async def update_captions(file_captions, image_path, user, append=False, blacklist=None):
    if blacklist is None:
        blacklist = []
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
            if cleaned != "" and cleaned not in clean_tags and cleaned not in blacklist:
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
