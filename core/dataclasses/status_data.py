import base64
import io
import json
import os.path
from dataclasses import dataclass

from PIL import Image

from core.handlers.images import create_image_grid
from dreambooth import shared


@dataclass
class StatusData:
    status: str = ""
    status_2: str = ""
    progress_1_total: int = 0
    progress_1_current: int = 0
    progress_2_total: int = 0
    progress_2_current: int = 0
    active: bool = False
    canceled: bool = False
    images: list = None
    latents: list = None
    prompts: list = None
    descriptions: list = None

    def __init__(self):
        self.status = ""
        self.status_2 = ""
        self.progress_1_total = 0
        self.progress_1_current = 0
        self.progress_2_total = 0
        self.progress_2_current = 0
        self.active = False
        self.canceled = False
        self.images = []
        self.latents = []
        self.prompts = []
        self.descriptions = []

    def start(self):
        shared.status.interrupted = False
        self.status = ""
        self.status_2 = ""
        self.progress_1_total = 0
        self.progress_1_current = 0
        self.progress_2_total = 0
        self.progress_2_current = 0
        self.active = True
        self.canceled = False
        self.images = []
        self.latents = []
        self.prompts = []
        self.descriptions = []

    def end(self):
        self.status = ""
        self.status_2 = ""
        self.latents = []
        self.progress_1_current = 0
        self.progress_1_total = 0
        self.progress_2_current = 0
        self.progress_2_total = 0
        self.active = False

    def dict(self):
        obj = {}
        for attr, value in self.__dict__.items():
            try:
                if attr != "images" and attr != "latents":
                    json.dumps(value)
                    obj[attr] = value
                else:
                    if attr == "latents" and value is not None:
                        # Make a grid of images from the list of images in latents if the length is > 1
                        img = create_image_grid(value)
                        if img:
                            with io.BytesIO() as output:
                                img = img.convert('RGB')
                                img.save(output, format='JPEG')
                                image_data = base64.b64encode(output.getvalue()).decode('utf-8')
                                value = f"data:image/jpeg;base64,{image_data}"
                            obj[attr] = value
                        else:
                            obj[attr] = None
                    else:
                        images = []
                        for img in value:
                            if isinstance(img, str):
                                # If the item is a string, assume it's a file path
                                try:
                                    if os.path.exists(img):
                                        with open(img, 'rb') as image_file:
                                            image_data = base64.b64encode(image_file.read()).decode('utf-8')
                                        images.append(f"data:image/jpeg;base64,{image_data}")
                                except:
                                    pass
                            elif isinstance(img, Image.Image):
                                # If the item is a PIL image, convert it to bytes and encode as base64
                                with io.BytesIO() as output:
                                    img = img.convert('RGB')
                                    img.save(output, format='JPEG')
                                    image_data = base64.b64encode(output.getvalue()).decode('utf-8')
                                images.append(f"data:image/jpeg;base64,{image_data}")

                        obj[attr] = images

            except TypeError:
                pass
        return obj
