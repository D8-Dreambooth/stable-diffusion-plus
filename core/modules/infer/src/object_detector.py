import torch
from lavis.models import load_model_and_preprocess
from PIL import Image
import numpy as np

from core.handlers.models import ModelManager


class ObjectDetector:
    """
    A class that performs object detection and creates masks for the detected objects.
    Initializes the BlipCaption class with the specified name and model type.
    Loads the model and preprocesses the data.
    Registers the _to_cpu and _to_gpu methods with the ModelManager.
    Detects and creates a mask for the specified object in the raw image.
    Preprocesses the image and generates a caption using the model.
    If the object_name is present in the caption, creates a mask for the detected object with the specified padding.
    Returns the mask.
    Creates a mask for the detected object with the specified padding.
    Returns the mask.
    @param name: str
    @param model_type: str
    @return: None
    """

    def __init__(self, name="blip_caption", model_type="base_coco"):
        """
        Initializes the BlipCaption class with the specified name and model type.
        Loads the model and preprocesses the data.
        Registers the _to_cpu and _to_gpu methods with the ModelManager.
        @param name: str
        @param model_type: str
        @return: None
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model, self.vis_processors, _ = load_model_and_preprocess(name=name, model_type=model_type, is_eval=True,
                                                                       device=self.device)
        self.model = self.model.to(self.device)
        mm = ModelManager()
        mm.register(self._to_cpu, self._to_gpu)

    def _to_cpu(self):
        self.model = self.model.to("cpu")

    def _to_gpu(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to("cuda")

    def detect_and_create_mask(self, raw_image, object_name, padding=0):
        """
        Detects and creates a mask for the specified object in the raw image.
        Preprocesses the image and generates a caption using the model.
        If the object_name is present in the caption, creates a mask for the detected object with the specified padding.
        Returns the mask.
        @param raw_image: PIL.Image
        @param object_name: str
        @param padding: int
        @return: PIL.Image or None
        """
        self._to_gpu()
        # Preprocess the image
        image = self.vis_processors["eval"](raw_image).unsqueeze(0).to(self.device)

        # Generate caption
        caption = self.model.generate({"image": image})

        # Check if the object_name is in the caption
        if object_name in caption[0]:
            # Create a mask for the detected object
            mask = self.create_mask(raw_image, padding)
        else:
            mask = None

        return mask

    def create_mask(self, raw_image, padding=0):
        # Create a blank mask with the same dimensions as the input image
        mask = np.zeros(raw_image.size, dtype=np.uint8)

        # Assuming the object detection gives us a bounding box of (x1, y1, x2, y2)
        # Here, we're just creating a fake bounding box for the sake of the example
        x1, y1, x2, y2 = 10, 10, 50, 50

        # Apply padding
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(raw_image.width, x2 + padding)
        y2 = min(raw_image.height, y2 + padding)

        # Set the mask to 255 (white) for the area of the detected object
        mask[y1:y2, x1:x2] = 255

        return mask
