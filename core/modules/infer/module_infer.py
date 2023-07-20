import asyncio
import logging
import os.path

import controlnet_aux
from fastapi import FastAPI, Query
from starlette.responses import JSONResponse

from core.dataclasses.infer_settings import InferSettings
from core.handlers.model_types.controlnet_processors import controlnet_models, get_detectors_and_params
from core.handlers.model_types.diffusers_loader import get_pipeline_parameters
from core.handlers.websocket import SocketHandler
from core.modules.base.module_base import BaseModule
from core.modules.infer.src.infer_utils import start_inference

logger = logging.getLogger(__name__)


class InferenceModule(BaseModule):

    def __init__(self):
        """
        Initializes an instance of the Inference class.

        The function initializes the name and path attributes of the class. It also creates an instance of the ObjectDetector class and assigns it to the object_detector attribute. Finally, it calls the __init__() method of the parent class with the name and path attributes as arguments.

        Args: None

        Returns: None

        """
        self.id = "infer"
        self.name = "Inference"
        self.path = os.path.abspath(os.path.dirname(__file__))

        super().__init__(self.id, self.name, self.path)

    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_api(app)
        self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
        """

        Initializes the API for the FastAPI app. Defines a GET route for inference/infer endpoint.
        If an API key is set, it must be present in the request.
        Returns a JSON response with a message indicating that the job has started.
        @return: JSONResponse

        """

        @app.get(f"/inference/infer")
        async def create_image(
                api_key: str = Query("", description="If an API key is set, this must be present.", )) -> \
                JSONResponse:
            """
            Check the current state of Dreambooth processes.
            foo
            @return:
            """
            return JSONResponse(content={"message": f"Job started."})

    def _initialize_websocket(self, handler: SocketHandler):
        handler.register("start_inference", _start_inference)
        handler.register("get_controlnets", _get_controlnets)
        handler.register("mask_image", _mask_image)
        handler.register("get_pipelines", _get_pipelines)
        handler.register("get_params", self._get_params)

    async def _get_params(self, msg):
        defaults = self.get_defaults()
        settings = InferSettings({})
        params = settings.get_params()
        for key, value in defaults.items():
            if key in params:
                data = params[key]
                data["value"] = value
                data["default"] = value
                params[key] = data
        return {"params": params}


async def _start_inference(msg):
    """
    Starts the inference process asynchronously.

    The function receives a message containing data, message ID, user and target information. It creates an instance of the InferSettings class with the data and calls the start_inference() function in a separate thread using asyncio.create_task(). It then immediately returns a reply to the websocket with a status message indicating that the inference has started.

    Args:
        msg (dict): A dictionary containing data, message ID, user and target information.

    Returns:
        dict: A dictionary containing a status message indicating that the inference has started.
    """
    data = msg["data"]
    msg_id = msg["id"]
    user = msg["user"] if "user" in msg else None
    target = msg.pop("target") if "target" in msg else None
    infer_data = InferSettings(data)
    # Call start_inference() in a separate thread using asyncio.create_task()
    asyncio.create_task(start_inference(infer_data, user, target))

    # Immediately return a reply to the websocket
    return {"name": "status", "message": "Inference started.", "id": msg_id}


async def _get_controlnets(msg):
    """
    Returns a dictionary containing the controlnets.

    The function receives a message and returns a dictionary containing the controlnets. It retrieves the controlnets from the model_data and returns them in the "nets" key of the dictionary.

    Args:
        msg (dict): A dictionary containing the message.

    Returns:
        dict: A dictionary containing the controlnets.
    """
    detectors = get_detectors_and_params(controlnet_aux)

    return {"nets": controlnet_models, "detectors": detectors}


async def _get_pipelines(msg):
    """
    Returns a dictionary containing the pipelines.

    The function receives a message and returns a dictionary containing the pipelines. It retrieves the pipelines from the model_data and returns them in the "pipelines" key of the dictionary.

    Args:
        msg (dict): A dictionary containing the message.

    Returns:
        dict: A dictionary containing the pipelines.
    """
    diffusers_data = get_pipeline_parameters()
    logger.debug("Listing pipelines!")
    return {"pipelines": diffusers_data}


async def _mask_image(msg):
    """
    Masks the input image based on the objects detected.

    The function receives a message containing data, message ID, user and target information. It extracts the image and the objects to be detected from the data and calls the detect_and_create_mask() method of the object_detector attribute to create a mask for the detected objects. It then immediately returns a reply to the websocket with a status message indicating that the inference has started.

    Args:
        msg (dict): A dictionary containing data, message ID, user and target information.

    Returns:
        dict: A dictionary containing a status message indicating that the inference has started.
    """
    data = msg["data"]
    msg_id = msg["id"]
    user = msg["user"] if "user" in msg else None
    target = msg.pop("target") if "target" in msg else None
    image = data["image"]
    find_objects = data["find_objects"]
    if "," in find_objects:
        find_objects = find_objects.split(",")
    else:
        find_objects = [find_objects]
    # Immediately return a reply to the websocket
    return {"name": "status", "message": "Inference started.", "id": msg_id}
