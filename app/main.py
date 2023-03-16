import asyncio
import json
import logging
import os.path
from asyncio import Queue

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
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler
from core.modules.dreambooth.dreambooth import shared
from .library.helpers import *

logging.basicConfig(format='[%(asctime)s][%(levelname)s][%(name)s] - %(message)s', level=logging.DEBUG)

# I think some of these can go away.
clients = []
socket_callbacks = {}
active_modules = {}
active_extensions = {}


# Enumerate files in modules. This should probably be in a class somewhere
def get_files():
    css_files = []
    js_files = []
    js_files_ext = []
    custom_files = []
    html = []
    dict_idx = 0

    theme = config_handler.get_item("theme", default="theme-default")
    system_css = os.path.join(path, "static", "css")
    user_css = os.path.join(dirs["user"], "css")

    theme_file = os.path.join(system_css, f"{theme}.css")
    theme_file2 = os.path.join(user_css, f"{theme}.css")
    for theme_check in [theme_file, theme_file2]:
        if os.path.exists(theme_check):
            logger.debug(f"Mounting {theme_check}")
            mount_path = f"/theme"
            file_dir = os.path.dirname(theme_check)
            css_files.append(os.path.join(mount_path, os.path.basename(theme_check)))
            app.mount(mount_path, StaticFiles(directory=file_dir), name="static")

    for active_dict in (active_modules, active_extensions):
        for module_name, module in active_dict.items():
            logger.debug(f"Listing files for module: {module_name}")

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


# Determine our absolute path
path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
shared.script_path = path


# Load our basic launch settings
launch_settings_path = os.path.join(shared.script_path, "launch_settings.json")

with open(launch_settings_path, "r") as ls:
    launch_settings = json.load(ls)


# Set the global debugging level
debug_level = launch_settings.get("debug_level", "debug")
if debug_level == "debug":
    logging.basicConfig(level=logging.DEBUG)
elif debug_level == "info":
    logging.basicConfig(level=logging.INFO)
elif debug_level == "warning":
    logging.basicConfig(level=logging.WARNING)
elif debug_level == "error":
    logging.basicConfig(level=logging.ERROR)
elif debug_level == "critical":
    logging.basicConfig(level=logging.CRITICAL)
else:
    logging.basicConfig(level=logging.DEBUG)
    logging.warning(f"Unknown debug_level value: {debug_level}. Defaulting to DEBUG level.")

logger = logging.getLogger(__name__)


# Check/set shared directories based on launch settings
keys_to_check = ["cache", "config", "shared", "user", "models", "extensions"]

if "data_shared" in launch_settings:
    shared_path = launch_settings["data_shared"]
    if not os.path.exists(shared_path):
        os.mkdir(shared_path)
else:
    shared_path = os.path.join(path, "data_shared")
    
if "data_protected" in launch_settings:
    protected_path = launch_settings["data_protected"]
    if not os.path.exists(protected_path):
        os.mkdir(protected_path)
else:
    protected_path = os.path.join(path, "data_protected")


# Enumerate and create shared directories. We probably need to also do this for protected dirs.
dirs = {"shared_data": shared_path}
for key in keys_to_check:
    if launch_settings.get(f"{key}_dir"):
        val = launch_settings[key]
        if val != "" and os.path.exists(val):
            dirs[key] = val
    else:
        val = os.path.join(shared_path, key)
        dirs[key] = val

for name, c_dir in dirs.items():
    if not os.path.exists(c_dir):
        os.mkdir(c_dir)


# Set final config directories
shared_config = dirs["config"]
protected_config = os.path.join(protected_path, "config")

if not os.path.exists(protected_config):
    os.makedirs(protected_config)

# Create master config handler
config_handler = ConfigHandler(shared_config, protected_config, path)

# TODO: Remove this and make dreambooth use our system-wide stuff
shared.paths = dirs
shared.models_path = dirs["models"]


# Create our base webserver
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

app.message_queue = asyncio.Queue()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Initialize our handlers

# Socket handler after config handler
socket_handler = SocketHandler(app)

# Register config handler callbacks
socket_handler.register("get_config", config_handler.socket_get_config)
socket_handler.register("set_config", config_handler.socket_set_config)
socket_handler.register("get_config_item", config_handler.socket_get_config_item)
socket_handler.register("set_config_item", config_handler.socket_set_config_item)
status_handler = StatusHandler(socket_handler)
# Now create the other handlers, which use our dirs vars from above
file_handler = FileHandler(dirs["user"])
models_handler = ModelHandler(dirs["models"])
image_handler = ImageHandler(dirs["user"])
cache_handler = CacheHandler(dirs["cache"])

# Now that all the other handlers are alive, initialize modules and extensions
module_handler = ModuleHandler(os.path.join(path, "core", "modules"))
extension_handler = ExtensionHandler(path, dirs["extensions"])

# Enumerate data for the UI from each module and extension
active_modules = module_handler.get_modules()
active_extensions = extension_handler.get_extensions()

# Initialize extensions *first*, so if one happens to try and override a core socket/api method, it can't.
for ext_name, extension in active_extensions.items():
    logger.debug(f"Initializing extension: {ext_name}")
    extension.initialize(app, socket_handler)

# Initialize modules last, so they always have precedence with registered methods.
for module_name, module in active_modules.items():
    logger.debug(f"Initializing module: {module_name}")
    module.initialize(app, socket_handler)


# Add our home endpoint (and others)?
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
