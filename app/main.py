import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.handlers.cache import CacheHandler
from core.handlers.config import ConfigHandler
from core.handlers.extensions import ExtensionHandler
from core.handlers.file import FileHandler
from core.handlers.images import ImageHandler
from core.handlers.models import ModelHandler
from core.handlers.modules import ModuleHandler
from core.handlers.websockets import SocketHandler
from dreambooth.dreambooth import shared
from dreambooth.scripts.api import dreambooth_api
from .library.helpers import *

clients = []
socket_callbacks = {}
active_modules = {}
active_extensions = {}
logger = logging.getLogger(__name__)


def get_files():
    css_files = []
    js_files = []
    js_files_ext = []
    custom_files = []
    html = []

    dict_idx = 0
    for active_dict in (active_modules, active_extensions):
        for module_name, module in active_dict.items():
            for dest, attr in [(css_files, "css_files"), (js_files, "js_files"), (custom_files, "custom_files")]:
                if attr == "js_files" and dict_idx == 1:
                    dest = js_files_ext
                dest_dir = attr.split("_")[0]
                for file_path in getattr(module, attr, []):
                    file = os.path.basename(file_path)
                    file_dir = os.path.dirname(file_path)
                    mount_dir = f"/modules/{module_name}/{dest_dir}"
                    mount_path = f"/modules/{module_name}/{dest_dir}/{file}"
                    dest.append(mount_path)
                    app.mount(mount_dir, StaticFiles(directory=file_dir), name="static")
            if os.path.exists(module.source):
                with open(module.source, "r") as file:
                    html.append(file.read())
            dict_idx +=1

    return css_files, js_files, js_files_ext, custom_files, html


path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
shared.script_path = path

launch_settings_path = os.path.join(shared.script_path, "launch_settings.json")

with open(launch_settings_path, "r") as ls:
    launch_settings = json.load(ls)

keys_to_check = ["cache", "config", "shared", "user", "models", "extensions"]
if "data_shared" in launch_settings:
    data_path = launch_settings["data_shared"]
    if not os.path.exists(data_path):
        os.mkdir(data_path)
else:
    data_path = os.path.join(path, "data_shared")

dirs = {"shared_data": data_path}
for key in keys_to_check:
    if launch_settings.get(f"{key}_dir"):
        val = launch_settings[key]
        if val != "" and os.path.exists(val):
            logger.debug(f"Appending path from settings: {val}")
            dirs[key] = val
    else:
        val = os.path.join(data_path, key)
        logger.debug(f"Appending path from datapath: {val}")
        dirs[key] = val

for name, c_dir in dirs.items():
    if not os.path.exists(c_dir):
        os.mkdir(c_dir)

shared.paths = dirs
shared.models_path = dirs["models"]

print(f"Launch settings: {launch_settings}")

app = FastAPI(
    title="Stable-Diffusion Plus",
    description="Stable Diffusion Done Right",
    version="0.0.1",
    contact={
        "name": "d8ahazard",
        "url": "https://github.com/d8ahazrd",
        "email": "donate.to.digitalhigh@gmail.com",
    },
    license_info={
        "name": "Non-Commercial 1.0",
        "url": "https://github.com/D8-Dreambooth/stable-diffusion-plus/blob/main/LICENSE.txt",
    },
)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

socket_handler = SocketHandler(app)

image_handler = ImageHandler(dirs["user"])
cache_handler = CacheHandler(dirs["cache"])
config_handler = ConfigHandler(dirs["config"])
module_handler = ModuleHandler(os.path.join(path, "core", "modules"))
extension_handler = ExtensionHandler(path, dirs["extensions"])
file_handler = FileHandler(dirs["user"])
models_handler = ModelHandler(dirs["models"])

active_modules = module_handler.get_modules()
active_extensions = extension_handler.get_extensions()

logging.basicConfig(level=logging.DEBUG)
logger.debug(f"Paths: {dirs}")

# Initialize API endpoints if the module has them.
dreambooth_api(None, app)
for module_name, module in active_modules.items():
    module.initialize_api(app)
    module.initialize_websocket(socket_handler)

for ext_name, extension in active_extensions.items():
    extension.initialize_api(app)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    css_files, js_files, js_files_ext, custom_files, html = get_files()
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "css_files": css_files,
            "js_files": js_files,
            "js_files_ext": js_files_ext,
            "custom_files": custom_files,
            "module_html": html
        }
    )
