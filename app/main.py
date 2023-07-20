import asyncio
import json
import logging
import os.path
import random
import time
import traceback
from typing import Dict

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.params import Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from app.auth.oauth2_password_bearer import OAuth2PasswordBearerCookie
from core.handlers.cache import CacheHandler
from core.handlers.config import ConfigHandler
from core.handlers.directories import DirectoryHandler
from core.handlers.extensions import ExtensionHandler
from core.handlers.file import FileHandler
from core.handlers.history import HistoryHandler
from core.handlers.images import ImageHandler
from core.handlers.models import ModelHandler
from core.handlers.modules import ModuleHandler
from core.handlers.queues import QueueHandler
from core.handlers.status import StatusHandler
from core.handlers.users import UserHandler, User, get_current_active_user
from core.handlers.websocket import SocketHandler
from core.helpers.model_watcher import ModelWatcher

# I think some of these can go away.
clients = []
socket_callbacks = {}
active_modules = {}
active_extensions = {}
active_sessions = {}
launch_settings = {}
shared_config = ""
protected_config = ""
config_handler = None
directory_handler = None
user_auth = True
model_watcher = ModelWatcher()

dirs = {}

logger = logging.getLogger(__name__)


def get_files(dir_handler: DirectoryHandler, theme_only=False, user_data: Dict = None):
    file_config_handler = ConfigHandler(user_name=user_data["name"] if user_data is not None else None)
    css_files = []
    js_files = []
    js_files_ext = []
    custom_files = []
    locales = {}
    html = []
    dict_idx = 0
    is_admin = False if user_data is None else user_data["admin"]

    theme = file_config_handler.get_item_protected("theme", default="theme-default")
    system_css = os.path.join(app_path, "static", "css")
    user_css = dir_handler.get_directory("css")[0]

    theme_file = os.path.join(system_css, f"{theme}.css")
    theme_file2 = os.path.join(user_css, f"{theme}.css")
    for theme_check in [theme_file, theme_file2]:
        if os.path.exists(theme_check):
            mount_path = f"/theme"
            file_dir = os.path.dirname(theme_check)
            css_files.append(os.path.join(mount_path, os.path.basename(theme_check)))
            app.mount(mount_path, StaticFiles(directory=file_dir), name="static")
    if theme_only:
        return css_files, js_files, js_files_ext, custom_files, html
    user_lang = file_config_handler.get_item_protected("language", "core", default="en")
    for active_dict in (active_modules, active_extensions):
        for module_name, module in active_dict.items():
            if module_name == "Settings" and not is_admin:
                continue
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
    locales = json.dumps(locales)
    return css_files, js_files, js_files_ext, custom_files, html


def load_settings():
    global launch_settings, user_auth, directory_handler, config_handler
    # Load our basic launch settings
    launch_settings_path = os.path.join(app_path, "launch_settings.json")

    with open(launch_settings_path, "r") as ls:
        launch_settings = json.load(ls)
    # Set the global debugging level

    directory_handler = DirectoryHandler(app_path, launch_settings)
    config_handler = ConfigHandler()
    cpu_only = config_handler.get_item_protected("cpu_only", "core", False)
    if cpu_only:
        from dreambooth import shared
        shared.force_cpu = True
    user_auth = config_handler.get_item_protected("user_auth", "core", False)


def initialize_app():
    global config_handler, active_modules, active_extensions
    # Create master config handler
    config_handler = ConfigHandler()
    _ = QueueHandler(4)
    user_handler = UserHandler(config_handler)
    socket_handler = SocketHandler(app, user_handler)

    # Register config handler callbacks
    socket_handler.register("get_all", config_handler.socket_get_all)
    socket_handler.register("get_config", config_handler.socket_get_config)
    socket_handler.register("set_config", config_handler.socket_set_config)
    socket_handler.register("get_config_item", config_handler.socket_get_config_item)
    socket_handler.register("set_config_item", config_handler.socket_set_config_item)

    sh = StatusHandler(socket_handler)
    sh.end("")
    # Now create the other handlers, which use our dirs vars from above
    FileHandler(app)
    ModelHandler(watcher=model_watcher)
    ImageHandler()
    CacheHandler()
    HistoryHandler()
    user_handler.initialize(app, socket_handler)
    # Now that all the other handlers are alive, initialize modules and extensions
    module_handler = ModuleHandler(os.path.join(app_path, "core", "modules"), socket_handler)
    extension_handler = ExtensionHandler()

    # Enumerate data for the UI from each module and extension
    active_modules = module_handler.get_modules()
    active_extensions = extension_handler.get_extensions()

    # Initialize extensions *first*, so if one happens to try and override a core socket/api method, it can't.
    for ext_name, extension in active_extensions.items():
        logger.info(f"Initializing extension: {ext_name}")
        extension.initialize(app, socket_handler)

    # Initialize modules last, so they always have precedence with registered methods.
    for module_name, module in active_modules.items():
        logger.info(f"Initializing module: {module_name}")
        module.initialize(app, socket_handler)

    return user_handler


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

user_handler = initialize_app()


def get_session(request: Request):
    return request.session


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.exception(f"Exception: {request.cookies}")
    traceback.print_exc()
    if exc.status_code == 403:
        logger.info("Redirecting to login")
        return RedirectResponse(url="/login")
    else:
        return exc


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user_data: Dict = Depends(get_current_active_user)):
    logger.debug(f"Incoming request: {request}")
    logger.debug(f"User data: {user_data}")
    current_user = user_data["name"] if user_data else None
    dh = DirectoryHandler(user_name=current_user)
    ch = ConfigHandler(user_name=current_user)
    page_title = ch.get_item_protected("title", "core", "Stable-Diffusion Plus")
    show_snark = ch.get_item_protected("snarky_loaders", "core", True)
    language = ch.get_item_protected("language", "core", "en")
    if show_snark:
        loaders = ch.get_locales("loading", language)
        # Select a random item from the loaders list
        loader = random.choice(loaders)
    else:
        loader = "Loading..."
    if "<br>" in loader:
        lines = loader.split("<br>")
        loader = f"{lines[0]}<br><div class='subLoader'>{lines[1]}</div>"
    logger.debug("Loading message: %s", loader)
    timestamp = int(time.time())

    if user_handler.user_auth:
        if current_user and not user_data["disabled"]:
            # User is logged in, show the usual home page
            css_files, js_files, js_files_ext, custom_files, html = get_files(dh, False, user_data)
            return templates.TemplateResponse(
                "base.html",
                {
                    "title": page_title,
                    "request": request,
                    "css_files": css_files,
                    "js_files": js_files,
                    "js_files_ext": js_files_ext,
                    "custom_files": custom_files,
                    "module_html": html,
                    "timestamp": timestamp,
                    "loader": loader
                }
            )
        else:
            logger.info("No login.")
            # User is not logged in, redirect to login page
            return RedirectResponse(url="/login")
    else:
        # Authentication not required, show the usual home page
        css_files, js_files, js_files_ext, custom_files, html = get_files(dh, False, None)
        return templates.TemplateResponse(
            "base.html",
            {
                "title": page_title,
                "request": request,
                "css_files": css_files,
                "js_files": js_files,
                "js_files_ext": js_files_ext,
                "custom_files": custom_files,
                "module_html": html,
                "timestamp": timestamp,
                "loader": loader
            }
        )


@app.post("/login")
async def handle_login(request: Request, response: Response, form_data: dict):
    username = form_data.get("username")
    password = form_data.get("password")

    if user_handler.authenticate_user(username, password):
        logger.debug("AUTHENTICATED")
        access_token = user_handler.create_access_token(data={"sub": username})
        logger.debug("TOKEN CREATED")
        response.set_cookie(key="access_token", value=access_token)
        response.set_cookie(key="user", value=username)
        logger.debug(f"COOKIE SET, returning: {access_token}")
        # Get the URL for the home page
        return JSONResponse({"access_token": access_token, "user": username})

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
    ch = ConfigHandler()
    page_title = ch.get_item_protected("title", "core", "Stable-Diffusion Plus")
    css_files, js_files, js_files_ext, custom_files, html = get_files(dh, True)
    return templates.TemplateResponse(
        "login.html",
        {
            "title": page_title,
            "request": request,
            "css_files": css_files
        }
    )


@app.post("/token")
async def token(
        grant_type: str = Form(...),
        username: str = Form(...),
        password: str = Form(...),
):
    if grant_type != "password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid grant_type",
        )
    logger.debug(f"Verifying: {username} and {password}")
    if user_handler.authenticate_user(username, password):
        access_token = user_handler.create_access_token(data={"sub": username})
        response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
        response.set_cookie(key="access_token", value=access_token)
        return response

    # Return a 401 if we don't return a token
    response = JSONResponse({"error": "invalid_grant", "error_description": "Invalid username or password"})
    response.status_code = 401
    return response


@app.get("/whoami")
async def whoami(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/logout")
async def del_session(response: Response):
    response.delete_cookie("Authorization")
    response.delete_cookie("access_token")
    response.delete_cookie("user")
    return RedirectResponse(url="/login")

@app.on_event("startup")
def startup_event():
    model_watcher.start()

@app.on_event("shutdown")
def shutdown_event():
    model_watcher.stop()