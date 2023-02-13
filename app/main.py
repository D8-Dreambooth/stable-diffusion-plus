import json

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import settings
from dreambooth.dreambooth import shared
from dreambooth.scripts.api import dreambooth_api
from .library.helpers import *


def load_extensions():
    print("Load extensions or something")


# Install extensions first
load_extensions()

path = os.path.join(os.path.dirname(__file__), "..")
shared.script_path = path

with open(os.path.join(path, "launch_settings.json"), "r") as ls:
    launch_settings = json.load(ls)

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

app.include_router(settings.router)

dreambooth_api(None, app)

clients = []


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    data = openfile("home.md")
    return templates.TemplateResponse("page.html", {"request": request, "data": data})


@app.get("/page/{page_name}", response_class=HTMLResponse)
async def show_page(request: Request, page_name: str):
    data = openfile(page_name + ".md")
    return templates.TemplateResponse("page.html", {"request": request, "data": data})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    clients.append(websocket)
    await websocket.accept()
    while True:
        await websocket.send_json({})
        data = await websocket.receive_json()


async def broadcast(message: str):
    for client in clients:
        await client.send_text(message)
