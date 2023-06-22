import base64
import hashlib
import json
import logging
import math
import os
import re
import traceback
from io import BytesIO
from typing import Tuple, List, Dict

import PIL
import numpy as np
from PIL import Image, PngImagePlugin
from PIL.Image import Resampling

from core.handlers.directories import DirectoryHandler
from core.handlers.file import FileHandler, is_image
from core.handlers.websocket import SocketHandler

logger = logging.getLogger(__name__)


async def _read_image_info(request):
    data = request["data"]
    image_data = {}
    if "image" in data:
        # data is a png file, read the png info
        image = Image.open(BytesIO(base64.b64decode(data["image"])))
        image_data = image.info
        image_data = decode_dict(image_data)
    return {"image_data": image_data}


def decode_dict(input_dict):
    decoded_dict = {}
    for key, value in input_dict.items():
        decoded_value = None
        try:
            decoded_value = json.loads(value)
        except:
            pass

        if decoded_value is not None:
            value = decoded_value
        # Remove the escape characters only if the value is a string
        if isinstance(value, str):
            decoded_value = value.encode('utf-8').decode('unicode_escape')

        # Convert strings "true" and "false" to boolean values True and False, respectively
        if decoded_value == "true":
            decoded_value = True
        elif decoded_value == "false":
            decoded_value = False
        else:
            # Check if the value can be parsed as an integer
            try:
                decoded_value = int(decoded_value)
            except:
                pass
            else:
                # If the value can be parsed as an integer, skip the float check
                decoded_dict[key] = decoded_value
                continue

            # Check if the value can be parsed as a float
            try:
                decoded_value = float(decoded_value)
            except:
                pass

        # Remove the escape characters from string values that include path elements
        if isinstance(decoded_value, str):
            if decoded_value.startswith('"') and decoded_value.endswith('"'):
                decoded_value = decoded_value[1:-1]
                decoded_value = decoded_value.replace("\\\\", "\\")
                decoded_value = decoded_value.replace("\\\"", "\"")

        # Add the decoded key-value pair to the new dictionary
        model_keys = ["loras", "model", "vae"]
        if key in model_keys:
            if isinstance(decoded_value, str):
                try:
                    decoded_value = json.loads(decoded_value)
                except:
                    logger.debug(f"Could not decode {key} value: {decoded_value}")

            logger.debug(f"Decoded {key} value: {decoded_value}")
            if isinstance(decoded_value, dict):
                decoded_value = decoded_value["hash"]
            elif isinstance(decoded_value, list):
                decoded_value = [d["hash"] for d in decoded_value]

        decoded_dict[key] = decoded_value

    return decoded_dict


def create_image_grid(images):
    image_objects = []
    if isinstance(images, PIL.Image.Image):
        return images
    # Load image objects from input
    for img in images:
        if isinstance(img, str):
            image_objects.append(Image.open(img))
        elif isinstance(img, Image.Image):
            image_objects.append(img)
        else:
            # Print img type
            raise ValueError(f"Invalid input: list must contain strings with paths to images or PIL images: {type(img)}")

    n_images = len(image_objects)

    if n_images <= 1:
        return image_objects[0] if n_images == 1 else None

    # Calculate grid dimensions
    grid_size = math.ceil(math.sqrt(n_images))
    max_width = max([img.width for img in image_objects])
    max_height = max([img.height for img in image_objects])

    # Create an empty image to paste the input images onto
    grid_image = Image.new('RGB', (grid_size * max_width, grid_size * max_height))

    # Paste input images onto the grid
    for i, img in enumerate(image_objects):
        x = (i % grid_size) * max_width
        y = (i // grid_size) * max_height
        grid_image.paste(img, (x, y))

    return grid_image


def scale_image(img: Image.Image, width: int, height: int, resize_mode: str = "scale", is_mask: bool = False, origin: str = "center") -> Image.Image:
    """
    :param img: The image to scale
    :param width: Target width, based on the resize_mode
    :param height: Target height, based on the resize_mode
    :param resize_mode: Can be one of the following: "scale", "crop", "pad", "fit"
    :param is_mask: If true, image is treated as a mask and padded with black pixels
    :param origin: Determines the crop's starting point. Can be one of the following: "top-left", "top-center", "top-right", "center-left", "center", "center-right", "bottom-left", "bottom-center", "bottom-right"
    :return: PIL.Image.Image
    """
    img_width, img_height = img.size

    logger.debug("Initial image size: %s x %s", img_width, img_height)

    if is_mask:
        resize_mode = "pad"

    if resize_mode == "scale":
        logger.debug("Resize mode: scale")
        # Resize the image while maintaining aspect ratio
        aspect_ratio = img_width / img_height
        if width / aspect_ratio > height:
            width = int(height * aspect_ratio)
        else:
            height = int(width / aspect_ratio)
        img = img.resize((width, height), Image.ANTIALIAS)
    elif resize_mode == "crop":
        logger.debug("Resize mode: crop")
        # Crop the image to fit the target dimensions
        img.thumbnail((width, height))
        width_start = (img.width - width) // 2
        height_start = (img.height - height) // 2
        img = img.crop((width_start, height_start, width_start + width, height_start + height))
    elif resize_mode == "pad":
        logger.debug("Resize mode: pad")
        # Add padding to the image to fit the target dimensions
        img.thumbnail((width, height), Image.ANTIALIAS)
        if is_mask:
            # Create new image with black pixels and append the mask
            new_img = Image.new("L", (width, height), 0)
        else:
            # Create new image with random noise
            noise_array = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
            new_img = Image.fromarray(noise_array, 'RGB')

        if origin == "top-left":
            ulc = (0, 0)
        elif origin == "top-center":
            ulc = ((width - img.width) // 2, 0)
        elif origin == "top-right":
            ulc = (width - img.width, 0)
        elif origin == "center-left":
            ulc = (0, (height - img.height) // 2)
        elif origin == "center":
            ulc = ((width - img.width) // 2, (height - img.height) // 2)
        elif origin == "center-right":
            ulc = (width - img.width, (height - img.height) // 2)
        elif origin == "bottom-left":
            ulc = (0, height - img.height)
        elif origin == "bottom-center":
            ulc = ((width - img.width) // 2, height - img.height)
        elif origin == "bottom-right":
            ulc = (width - img.width, height - img.height)
        else:
            raise ValueError(f"Invalid origin: {origin}")

        new_img.paste(img, ulc)
        img = new_img
    elif resize_mode == "fit":
        logger.debug("Resize mode: fit")
        # Resize the image to exactly fit the target dimensions without cropping
        img = img.resize((width, height), Image.ANTIALIAS)

    # Ensure that final output image dimensions are multiples of 8 and crop from the center if not
    if img.size[0] % 8 != 0 or img.size[1] % 8 != 0:
        logger.debug("Adjusting image size to be multiples of 8")
        new_width = (img.size[0] // 8) * 8
        new_height = (img.size[1] // 8) * 8
        left = (img.size[0] - new_width) / 2
        top = (img.size[1] - new_height) / 2
        right = (img.size[0] + new_width) / 2
        bottom = (img.size[1] + new_height) / 2
        img = img.crop((left, top, right, bottom))

    logger.debug("Final image size: %s x %s", img.size[0], img.size[1])

    return img


class ImageHandler:
    _instance = None
    _instances = {}
    user_dir = None
    current_dir = None
    socket_handler = None
    file_handler = None
    infer_keys = []

    def __new__(cls, user_name=None):
        try:
            from core.dataclasses.infer_settings import InferSettings
        except Exception as e:
            logger.debug("Exception importing: %s", e)
            traceback.print_exc()

        if cls._instance is None:
            dir_handler = DirectoryHandler()
            user_dir = dir_handler.get_directory("users")[0]
            cls._instance = super(ImageHandler, cls).__new__(cls)
            cls._instance.infer_keys = InferSettings({}).__dict__.keys()
            cls._instance.user_dir = user_dir
            cls._instance.current_dir = user_dir
            cls._instance.file_handler = FileHandler()
            cls.socket_handler = SocketHandler()
            cls.socket_handler.register("get_images", cls._instance._get_image)
            cls.socket_handler.register("read_image_info", _read_image_info)
        if user_name is not None:
            if user_name in cls._instances:
                return cls._instances[user_name]
            else:
                dir_handler = DirectoryHandler(user_name=user_name)
                user_dir = dir_handler.get_directory(user_name)[0]
                user_instance = super(ImageHandler, cls).__new__(cls)
                user_instance.user_dir = user_dir
                user_instance.current_dir = user_dir
                user_instance.infer_keys = InferSettings({}).__dict__.keys()
                user_instance.file_handler = FileHandler(user_name=user_name)
                user_instance.socket_handler = cls._instance.socket_handler
                user_instance.socket_handler.register("get_images", user_instance._get_image, user=user_name)
                user_instance.socket_handler.register("read_image_info", _read_image_info, user=user_name)
                cls._instances[user_name] = user_instance
                return user_instance
        else:
            return cls._instance

    def save_image(self, image, directory: str, prompt_data=None, save_txt: bool = True, custom_name: str = None):
        image_filenames = []

        if isinstance(image, list):
            for idx, img in enumerate(image):
                if isinstance(prompt_data, list):
                    prompt = prompt_data[idx] if idx < len(prompt_data) else None
                else:
                    prompt = prompt_data
                image_filenames.append(self._save_single_image(img, directory, prompt, save_txt, custom_name))
        else:
            image_filenames.append(self._save_single_image(image, directory, prompt_data, save_txt, custom_name))

        return image_filenames

    def _save_single_image(self, image: Image, directory: str, prompt_data = None, save_txt: bool = True,
                           custom_name: str = None):

        image_base = hashlib.sha1(image.tobytes()).hexdigest()

        file_name = image_base
        if custom_name is not None:
            file_name = custom_name

        file_name = re.sub(r"[^\w \-_.]", "", file_name)
        if self.user_dir not in directory:
            dest_dir = os.path.join(self.user_dir, "outputs", directory)
            dest_dir = os.path.abspath(dest_dir)
        else:
            dest_dir = os.path.abspath(directory)

        if self.user_dir not in dest_dir:
            logger.error("Exception saving to directory outside of user dir.")
            raise ValueError("Invalid directory for saving.")
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        image_filename = os.path.join(dest_dir, f"{file_name}.tmp")
        pnginfo_data = PngImagePlugin.PngInfo()
        if prompt_data is not None:
            for k, v in prompt_data.__dict__.items():
                try:
                    if "image" in k:
                        continue
                    if k == "model":
                        v = v.__dict__
                    val = json.dumps(v)
                    pnginfo_data.add_text(k, val)
                except TypeError:
                    pass
        image_format = Image.registered_extensions()[".png"]

        image.save(image_filename, format=image_format, pnginfo=pnginfo_data)

        if save_txt and prompt_data is not None:
            os.replace(image_filename, image_filename)
            txt_filename = image_filename.replace(".tmp", ".txt")
            with open(txt_filename, "w", encoding="utf8") as file:
                file.write(prompt_data.prompt)
        os.replace(image_filename, image_filename.replace(".tmp", ".png"))
        return image_filename.replace(".tmp", ".png")

    async def _get_image(self, request):
        data = request["data"]
        directory = data.get("directory")
        thumb_size = data.get("thumb_size", 256)
        return_thumb = data.get("return_thumb", False)
        recurse = data.get("recurse", False)
        if "user" in request:
            dir_handler = DirectoryHandler(user_name=request["user"])
            user_dir = dir_handler.get_directory(request["user"])[0]
            self.user_dir = user_dir
        filename = None
        if os.path.isfile(directory):
            filename = os.path.basename(directory)
            directory = os.path.dirname(directory)
        images, image_data = self.load_image(directory, filename=filename, recurse=recurse)
        img_idx = 0
        for image in images:
            img = Image.open(image)
            if return_thumb:
                width, height = img.size
                aspect_ratio = width / height
                if aspect_ratio >= 1:
                    new_width = thumb_size
                    new_height = round(thumb_size / aspect_ratio)
                else:
                    new_width = round(thumb_size * aspect_ratio)
                    new_height = thumb_size
                img = img.resize((new_width, new_height))

                # Crop the image to a square with dimensions of thumb_size x thumb_size
                width, height = img.size
                left = (width - thumb_size) / 2
                top = (height - thumb_size) / 2
                right = (width + thumb_size) / 2
                bottom = (height + thumb_size) / 2
                img = img.crop((left, top, right, bottom))
            with BytesIO() as output:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(output, format="JPEG")
                contents = output.getvalue()
                image_data[img_idx]["src"] = f"data:image/png;base64,{base64.b64encode(contents).decode()}"
            img_idx += 1
        sorted_image_data = sorted(image_data, key=lambda x: x["filename"])
        return {"image_data": sorted_image_data}

    def load_image(self, directory: str = None, filename: str = None, recurse: bool = False) -> Tuple[
        List[Image.Image], List[Dict]]:
        # If no filename specified, enumerate all images in directory

        if directory is None:
            directory = os.path.join(self.user_dir, "outputs")
        else:
            if self.user_dir not in directory:
                directory = os.path.abspath(os.path.join(self.user_dir, directory))

        images = []
        data = []
        if filename is None:
            for file in os.listdir(directory):
                full_file = os.path.join(directory, file)
                if is_image(full_file):
                    images.append(full_file)
                if os.path.isdir(full_file) and recurse:
                    sub_images, sub_data = self.load_image(full_file, recurse=recurse)
                    images.extend(sub_images)
                    data.extend(sub_data)
        else:
            full_file = os.path.join(directory, filename)
            if os.path.exists(full_file) and is_image(full_file):
                images.append(full_file)
            if os.path.isdir(full_file) and recurse:
                sub_images, sub_data = self.load_image(full_file, recurse=recurse)
                images.extend(sub_images)
                data.extend(sub_data)

        for image_file in images:
            image_data = {"path": image_file, "filename": os.path.basename(image_file)}
            with Image.open(image_file) as img:
                extension = os.path.splitext(image_file)[1]
                png_info = img.info
                for k in self.infer_keys:
                    if png_info.get(k):
                        try:
                            val = json.loads(png_info.get(k))
                            image_data[k] = val
                        except (TypeError, ValueError):
                            pass

                txt_file = image_file.replace(extension, ".txt")
                if os.path.exists(txt_file):
                    with open(txt_file, "r", encoding="utf8") as file:
                        prompt = file.read()
                else:
                    prompt = None

                if prompt is not None and len(prompt):
                    image_data["prompt"] = prompt
                data.append(image_data)

        return images, data
