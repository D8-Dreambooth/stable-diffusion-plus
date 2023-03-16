import base64
import io
import json
from dataclasses import dataclass

from PIL import Image


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
        self.prompts = []
        self.descriptions = []

    def start(self):
        self.status = ""
        self.status_2 = ""
        self.progress_1_total = 0
        self.progress_1_current = 0
        self.progress_2_total = 0
        self.progress_2_current = 0
        self.active = True
        self.canceled = False
        self.images = []
        self.prompts = []
        self.descriptions = []

    def end(self):
        self.status = ""
        self.status_2 = ""
        self.progress_1_current = self.progress_1_total
        self.progress_2_current = self.progress_2_total
        self.active = False
        self.canceled = False

    def dict(self):
        obj = {}
        for attr, value in self.__dict__.items():
            try:
                if attr != "images":
                    json.dumps(value)
                    obj[attr] = value
                else:
                    images = []
                    for img in value:
                        if isinstance(img, str):
                            # If the item is a string, assume it's a file path
                            with open(img, 'rb') as image_file:
                                image_data = base64.b64encode(image_file.read()).decode('utf-8')
                            images.append(image_data)
                        elif isinstance(img, Image.Image):
                            # If the item is a PIL image, convert it to bytes and encode as base64
                            with io.BytesIO() as output:
                                img.save(output, format='JPEG')
                                image_data = base64.b64encode(output.getvalue()).decode('utf-8')
                            images.append(image_data)
                    obj[attr] = images

            except TypeError:
                pass
        return obj
