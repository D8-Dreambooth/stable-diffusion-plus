import base64
import json
import os.path
from dataclasses import dataclass


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
        self.active = False
        self.canceled = False
        self.images = []
        self.prompts = []
        self.descriptions = []

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
                        if os.path.exists(img):
                            with open(img, 'rb') as image_file:
                                image_data = base64.b64encode(image_file.read()).decode('utf-8')
                            images.append(image_data)
                    obj[attr] = images

            except TypeError:
                pass
        return obj