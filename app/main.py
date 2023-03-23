import asyncio
import json
import logging
import os.path
import traceback
from typing import Dict

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import URL
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from core.handlers.cache import CacheHandler
from core.handlers.config import ConfigHandler
from core.handlers.directories import DirectoryHandler
from core.handlers.extensions import ExtensionHandler
from core.handlers.file import FileHandler
from core.handlers.images import ImageHandler
from core.handlers.models import ModelHandler
from core.handlers.modules import ModuleHandler
from core.handlers.queues import QueueHandler
from core.handlers.status import StatusHandler
from core.handlers.websocket import SocketHandler
from .auth_helpers import User, get_current_active_user, authenticate_user, create_access_token
from .library.helpers import *
from .oauth2_password_bearer import OAuth2PasswordBearerCookie

logging.basicConfig(format='[%(asctime)s][%(levelname)s][%(name)s] - %(message)s', level=logging.DEBUG)

# I think some of these can go away.
clients = []
socket_callbacks = {}
active_modules = {}
active_extensions = {}
active_sessions = {}
launch_settings = {}
shared_config = ""
protected_config = ""
directory_handler = None
user_auth = False
logger = logging.getLogger(__name__)


def get_files(dir_handler: DirectoryHandler, theme_only=False, is_admin=False):
    css_files = []
    js_files = []
    js_files_ext = []
    custom_files = []
    html = []
    dict_idx = 0

    theme = config_handler.get_item("theme", default="theme-default")
    system_css = os.path.join(app_path, "static", "css")
    user_css = dir_handler.get_directory("css")[0]

    theme_file = os.path.join(system_css, f"{theme}.css")
    theme_file2 = os.path.join(user_css, f"{theme}.css")
    for theme_check in [theme_file, theme_file2]:
        if os.path.exists(theme_check):
            logger.debug(f"Mounting {theme_check}")
            mount_path = f"/theme"
            file_dir = os.path.dirname(theme_check)
            css_files.append(os.path.join(mount_path, os.path.basename(theme_check)))
            app.mount(mount_path, StaticFiles(directory=file_dir), name="static")
    if theme_only:
        return css_files, js_files, js_files_ext, custom_files, html

    for active_dict in (active_modules, active_extensions):
        for module_name, module in active_dict.items():
            if module_name == "Settings" and not is_admin:
                continue
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
            dict_idx += 1

    return css_files, js_files, js_files_ext, custom_files, html


def load_settings():
    global launch_settings, user_auth, dirs, shared_config, protected_config, directory_handler
    # Load our basic launch settings
    launch_settings_path = os.path.join(app_path, "launch_settings.json")

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

    user_auth = launch_settings.get("user_auth", True)
    directory_handler = DirectoryHandler(app_path, launch_settings)


def initialize_app():
    global config_handler, active_modules, active_extensions
    # Create master config handler
    config_handler = ConfigHandler()
    users = config_handler.get_config_protected("users")

    queue_handler = QueueHandler(10)
    socket_handler = SocketHandler(app, user_auth)

    # Register config handler callbacks
    socket_handler.register("get_config", config_handler.socket_get_config)
    socket_handler.register("set_config", config_handler.socket_set_config)
    socket_handler.register("get_config_item", config_handler.socket_get_config_item)
    socket_handler.register("set_config_item", config_handler.socket_set_config_item)

    status_handler = StatusHandler(socket_handler)
    # Now create the other handlers, which use our dirs vars from above
    file_handler = FileHandler(app)
    models_handler = ModelHandler()
    image_handler = ImageHandler()
    cache_handler = CacheHandler()

    for user in users.keys():
        logger.debug(f"Creating handlers for user: {user}")
        DirectoryHandler(user_name=user)
        StatusHandler(user_name=user)
        FileHandler(user_name=user)
        ModelHandler(user_name=user)
        ImageHandler(user_name=user)

    # Now that all the other handlers are alive, initialize modules and extensions
    module_handler = ModuleHandler(os.path.join(app_path, "core", "modules"))
    extension_handler = ExtensionHandler()

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


# Determine our absolute path
app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

load_settings()

oauth2_scheme = OAuth2PasswordBearerCookie(token_url="/token")

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

session_secret = launch_settings.get("session_secret")
if session_secret is None:
    session_secret = "123ABC"

app.add_middleware(SessionMiddleware, secret_key=session_secret)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

initialize_app()


def get_session(request: Request):
    return request.session


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.exception(f"Exception: {request.cookies}")
    traceback.print_exc()
    if exc.status_code == 403:
        logger.debug("Redirecting to login")
        return RedirectResponse(url="/login")
    else:
        return exc


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user_data: Dict = Depends(get_current_active_user)):
    global user_auth
    current_user = user_data.get("name", None)
    logger.debug(f"Current user: {user_data}")
    dh = DirectoryHandler(current_user)
    if user_auth:
        if current_user:
            # User is logged in, show the usual home page
            css_files, js_files, js_files_ext, custom_files, html = get_files(dh, False, user_data["admin"])
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
        else:
            logger.debug("No login.")
            # User is not logged in, redirect to login page
            return RedirectResponse(url="/login")
    else:
        logger.debug("Noauth required.")
        fh = FileHandler()

        # Authentication not required, show the usual home page
        css_files, js_files, js_files_ext, custom_files, html = get_files(dh, False, True)
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


@app.post("/login")
async def handle_login(request: Request, response: Response, form_data: dict):
    username = form_data.get("username")
    password = form_data.get("password")

    if authenticate_user(username, password):
        access_token = create_access_token(data={"sub": username})
        response.set_cookie(key="access_token", value=access_token)

        # Get the URL for the home page
        home_url = request.url_for("home")
        redirect_url = URL(home_url)
        home_url = redirect_url.__str__()
        logger.debug(f"Redirecting to: {home_url}")

        return JSONResponse({"url": home_url, "access_token": access_token})

    else:
        html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login Failed</title>
            </head>
            <body>
                <h1>Login Failed</h1>
                <p>Invalid username or password. Please try again.</p>
            </body>
            </html>
        """
        return HTMLResponse(content=html)


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    # If user is not logged in, show login page
    # User is logged in, show the usual home page
    dh = DirectoryHandler()
    css_files, js_files, js_files_ext, custom_files, html = get_files(dh, True)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "css_files": css_files
        }
    )


@app.get("/whoami")
async def whoami(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/logout")
async def del_session(response: Response):
    response.delete_cookie("Authorization")
    return RedirectResponse(url="/login")
