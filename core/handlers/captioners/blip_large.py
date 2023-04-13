import logging
from typing import Dict

import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

from core.handlers.captioners.base import BaseCaptioner

logger = logging.getLogger(__name__)


class BlipLargeCaptioner(BaseCaptioner):
    model = None
    processor = None

    def __init__(self):
        super().__init__(None)
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large").to("cpu")
        self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large").to("cpu")

    def caption(self, image: Image, params: Dict, unload: bool = True):

        if torch.cuda.is_available() and self.model.device.type == "cpu":
            self.processor = self.processor.to("cuda")
            self.model = self.model.to("cuda")

        raw_image = image.convert('RGB')

        inputs = self.processor(raw_image, return_tensors="pt").to("cuda")

        out = self.model.generate(**inputs)
        caption = self.processor.decode(out[0], skip_special_tokens=True)
        logger.debug(f"Caption: {caption}")
        print(caption)

        if unload and torch.cuda.is_available():
            self.processor = self.processor.to("cpu")
            self.model = self.model.to("cpu")

        return caption
