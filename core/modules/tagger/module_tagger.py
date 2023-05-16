import gc
import logging
import os

import torch
from PIL import Image
from fastapi import FastAPI
from lavis.models import load_model_and_preprocess
from torchvision import transforms
from torchvision.transforms import InterpolationMode

from core.handlers.file import FileHandler
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule

logger = logging.getLogger(__name__)


class TaggerModule(BaseModule):

    def __init__(self):
        self.name: str = "Tagger"
        self.path = os.path.abspath(os.path.dirname(__file__))
        self.blip_model = None
        self.blip_proc = None
        self.vision_model = None
        self.vision_proc = None
        self.txt_processors = None

        super().__init__(self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_websocket(handler)

    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("save_caption", _save_caption)
        handler.register("caption_image", self._tag_image)

    async def _tag_image(self, data):
        logger.debug(f"Data: {data}")
        image_path = data["data"]["path"]
        raw_image = Image.open(image_path).convert("RGB")
        logger.debug("Loading processor.")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # loads BLIP caption base model, with finetuned checkpoints on MSCOCO captioning dataset.
        # this also loads the associated image processors
        if not self.blip_model:
            self.blip_model, self.blip_proc, _ = load_model_and_preprocess(name="blip_caption", model_type="large_coco", is_eval=True,
                                                       device=device)

        if not self.vision_model:
            self.vision_model, self.vision_proc, self.txt_processors = load_model_and_preprocess(name="blip_vqa", model_type="vqav2",
                                                                              is_eval=True, device=device)

        raw_image = raw_image.resize((512, 512))
        # preprocess the image
        image = self.blip_proc["eval"](raw_image).unsqueeze(0).to(device)
        # Describe the raw image
        logger.debug("Generating caption.")
        # generate caption
        base = self.blip_model.generate({"image": image})
        start_prompts = {
            "is_person": "is the subject a person?",
            "is_animal": "is the subject an animal?",
            "is_object": "is the subject an inanimate object?",
        }
        
        person_prompts = {
            "gender": "What is the subject's gender?",
            "age": "Is the subject young, middle-aged, or old?",
            "pose": "Is the subject sitting, standing, laying down, crawling, crouching, kneeling, or jumping?",
            "race": "What ethnicity is the subject?",
            "hair_color": "What is the color of the subject's hair?",
            "hair_style": "What is the style of the subject's hair?",
            "clothing": "What is the subject wearing?",
        }
        animal_prompts = {
            "type": "What type of animal is the subject?",
            "action": "What is the subject doing?",
            "species": "What species is the subject?",
            "color": "What color is the subject?",
            "age": "Is the subject a juvenile or adult?",
        }
        
        object_prompts = {
            "type": "What type of object is the subject?",
            "color": "What color is the subject?",
            "material": "What material is the subject made from?",
            "usage": "What is the subject used for?",            
        }
        general_prompts = {
            "subject": "describe the primary subject of the image",
            "background": "describe the background of the image",
            "environment": "describe the environment of the image",
            "items": "describe the items in the image",
            "lighting": "describe the lighting of the image",
            "color_palette": "Is the image in color, black and white, or sepia?",
            "composition": "describe the composition of the image",
            "medium": "Is the image a photograph, painting, drawing, or render?",            
        }

        outputs = {}
        
        tests = {}
        for key, question in start_prompts.items():
            # ask a random question.
            image = self.vision_proc["eval"](raw_image).unsqueeze(0).to(device)
            question = self.txt_processors["eval"](question)
            response = self.vision_model.predict_answers(samples={"image": image, "text_input": question},
                                                         inference_method="generate")
            tests[key] = response
            
        questions = {}
        if tests["is_person"] == ["yes"]:
            questions = person_prompts
        elif tests["is_animal"] == ["yes"]:
            questions = animal_prompts
        elif tests["is_object"] == ["yes"]:
            questions = object_prompts

        outputs = tests
        for key, generic in general_prompts.items():
            questions[key] = generic
            
        for key, question in questions.items():
            # ask a random question.
            image = self.vision_proc["eval"](raw_image).unsqueeze(0).to(device)
            question = self.txt_processors["eval"](question)
            response = self.vision_model.predict_answers(samples={"image": image, "text_input": question},
                                                         inference_method="generate")
            outputs[key] = response
            
        # Construct a comprehensive caption for the image
        attributes = [f"{key}: {value}" for key, value in outputs.items() if value is not None and value != '']
        caption = ', '.join(attributes)

        data = {"caption": outputs, "path": image_path, "base": base, "comprehensive_caption": caption}

        return data


async def _get_image(data):
    logger.debug(f"Data: {data}")
    user = data["user"]
    fh = FileHandler(user_name=user)
    image = fh.get_file(data)
    data["data"] = {"image": image}
    return data





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
        clean_tags.append(tag.strip())
    tags = ", ".join(clean_tags)
    fh.save_file(dest_dir, filename, tags.encode())
    return {"status": "Saved", "caption": tags}
