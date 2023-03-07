import hashlib
import logging
import os
import re

from PIL import Image, PngImagePlugin

from core.dataclasses.infer_data import InferSettings
from core.handlers.file import FileHandler
from core.handlers.websocket import SocketHandler

logger = logging.getLogger(__name__)


class ImageHandler:
    _instance = None
    user_dir = None
    current_dir = None
    socket_handler = None
    file_handler = None

    def __new__(cls, user_dir=None):
        if cls._instance is None and user_dir is not None:
            cls._instance = super(ImageHandler, cls).__new__(cls)
            cls._instance.user_dir = user_dir
            cls._instance.current_dir = user_dir
            cls._instance.file_handler = FileHandler()
            cls._socket_handler = SocketHandler()
            # socket_handler.register("images", cls._instance.get_image)

        return cls._instance

    def db_save_image(self, image: Image, directory: str, prompt_data: InferSettings = None, save_txt: bool = True,
                      custom_name: str = None):

        image_base = hashlib.sha1(image.tobytes()).hexdigest()

        file_name = image_base
        if custom_name is not None:
            file_name = custom_name

        file_name = re.sub(r"[^\w \-_.]", "", file_name)

        dest_dir = os.path.join(self.file_handler.user_dir, "outputs", directory)
        dest_dir = os.path.abspath(dest_dir)
        if self.file_handler.user_dir not in dest_dir:
            logger.debug("Exception saving to directory outside of user dir.")
            raise ValueError("Invalid directory for saving.")
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        image_filename = os.path.join(dest_dir, f"{file_name}.tmp")
        pnginfo_data = PngImagePlugin.PngInfo()
        if prompt_data is not None:
            size = (prompt_data.width, prompt_data.height)
            generation_params = {
                "Steps": prompt_data.steps,
                "CFG scale": prompt_data.scale,
                "Seed": prompt_data.seed,
                "Size": f"{size[0]}x{size[1]}",
                "Model": f"{prompt_data.model.display_name}"
            }

            generation_params_text = ", ".join(
                [k if k == v else f'{k}: {f"{v}" if "," in str(v) else v}' for k, v in generation_params.items()
                 if v is not None])

            prompt_string = f"{prompt_data.prompt}\nNegative prompt: {prompt_data.negative_prompt}\n{generation_params_text}".strip()
            pnginfo_data.add_text("parameters", prompt_string)

        image_format = Image.registered_extensions()[".png"]

        image.save(image_filename, format=image_format, pnginfo=pnginfo_data)

        if save_txt and prompt_data is not None:
            os.replace(image_filename, image_filename)
            txt_filename = image_filename.replace(".tmp", ".txt")
            with open(txt_filename, "w", encoding="utf8") as file:
                file.write(prompt_data.prompt)
        os.replace(image_filename, image_filename.replace(".tmp", ".png"))
        return image_filename.replace(".tmp", ".png")

