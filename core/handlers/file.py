import base64
import logging
import os
from datetime import datetime
from io import BytesIO, StringIO
from typing import Dict, List, Tuple, Union

from PIL import Image, features
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from core.handlers.directories import DirectoryHandler
from core.handlers.websocket import SocketHandler


class FileHandler:
    _instance = None
    _instances = {}
    user_dir = None
    user_name = None
    current_dir = None
    socket_handler = None
    logger = None
    templates = Jinja2Templates(directory="templates")
    app = None

    def __new__(cls, app=None, user_name=None):
        if cls._instance is None and app:
            dir_handler = DirectoryHandler()
            cls._instance = super(FileHandler, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(f"{__name__}-shared")
            app.mount("/static", StaticFiles(directory="static"), name="static")
            cls._instance.app = app
            user_dir = dir_handler.get_directory("users")[0]
            cls._instance.logger.debug(f"USER DIR: {user_dir}")
            cls._instance.user_dir = user_dir
            cls._instance.current_dir = user_dir
            socket_handler = SocketHandler()
            socket_handler.register("files", cls._instance.pass_dir_content)
            socket_handler.register("file", cls._instance.get_file)
        if user_name is not None:
            if user_name in cls._instances:
                return cls._instances[user_name]
            else:
                dir_handler = DirectoryHandler(user_name=user_name)
                user_instance = super(FileHandler, cls).__new__(cls)
                user_instance.logger = logging.getLogger(f"{__name__}-{user_name}")
                user_dir = dir_handler.get_directory(user_name)[0]
                user_instance.logger.debug(f"USER DIR: {user_dir}")
                user_instance.user_dir = user_dir
                user_instance.app = cls._instance.app
                user_instance.current_dir = user_dir
                socket_handler = SocketHandler()
                socket_handler.register("files", user_instance.pass_dir_content, user_name)
                socket_handler.register("file", user_instance.get_file, user_name)
                user_instance.user_name = user_name
                cls._instances[user_name] = user_instance
                return user_instance
        else:
            return cls._instance

    async def pass_dir_content(self, request):
        data = request["data"]
        self.logger.debug(f"Dir request: {data}")
        res = self.get_dir_content(data["start_dir"], data["include_files"], data["recursive"], data["filter"])
        current_path = self.current_dir.replace(self.user_dir, "")
        if current_path == "":
            current_path = os.path.sep
        result = {
            "items": res,
            "current": current_path,
            "separator": os.path.sep
        }
        return result

    async def get_file(self, request: Dict):
        pil_features = list_features()
        data = request["data"]
        self.logger.debug(f"File request: {data}")
        file = data["files"]
        files = []
        if isinstance(file, str):
            fullfile = os.path.join(self.current_dir, file)
            self.logger.debug(f"Full file: {fullfile}")
            if os.path.exists(fullfile):
                files.append(fullfile)
        if isinstance(file, list):
            for check in file:
                fullfile = os.path.join(self.current_dir, check)
                self.logger.debug(f"Full file: {fullfile}")
                if os.path.exists(fullfile):
                    files.append(fullfile)

        if not files:
            return {"error": "File not found"}

        urls = []
        for filename in files:
            file_dict = {
                "filename": os.path.basename(filename),
                "date_created": datetime.fromtimestamp(os.path.getctime(filename)).isoformat(),
                "date_modified": datetime.fromtimestamp(os.path.getmtime(filename)).isoformat(),
                "size": os.path.getsize(filename)
            }

            # Retrieve relevant EXIF data
            if is_image(filename, pil_features):
                try:
                    pass
                except:
                    pass

            # Retrieve relevant pngInfo data
            if filename.endswith(".png"):
                try:
                    pass
                except:
                    pass

            # Read plaintext file contents if file is human-readable and less than 50MB
            if filename.endswith(".txt") or filename.endswith(".json"):
                try:
                    size = os.path.getsize(filename)
                    if size < 50 * 1024 * 1024:
                        with open(filename, "r") as f:
                            file_dict["data"] = f.read()
                except:
                    pass

            # Encode image data in base64 if image can be opened with PIL
            if is_image(filename, pil_features):
                try:
                    with Image.open(filename) as img:
                        with BytesIO() as output:
                            img.save(output, format="JPEG")
                            contents = output.getvalue()
                            file_dict["src"] = f"data:image/jpeg;base64,{base64.b64encode(contents).decode()}"

                    txt_filename = os.path.splitext(filename)[0] + ".txt"
                    if os.path.exists(txt_filename) and os.path.isfile(txt_filename):
                        try:
                            with open(txt_filename, "r") as f:
                                file_dict["data"] = f.read()
                        except:
                            pass
                except:
                    pass

            urls.append(file_dict)

        return {"files": urls}

    def get_dir_content(self, start_dir: str = None, include_files: bool = False, recursive: bool = False,
                        filter: Union[str, List[str]] = None) -> Dict[str, Tuple[str, int, str, Union[None, Dict]]]:
        if start_dir is not None:
            start_dir = os.path.abspath(os.path.join(self.current_dir, start_dir))
            if not start_dir.startswith(self.user_dir):
                self.logger.error(f"INVALID PATH SPECIFIED: {start_dir}")
            else:
                self.current_dir = start_dir

        if not os.path.isdir(self.current_dir):
            return {}

        result = {}
        for entry in os.scandir(self.current_dir):
            if filter is not None:
                if isinstance(filter, str):
                    if not entry.name.endswith(filter):
                        continue
                elif isinstance(filter, list) and len(filter):
                    if not any(entry.name.endswith(ext) for ext in filter):
                        continue
            entry_data = (entry.stat().st_mtime, entry.stat().st_size, os.path.splitext(entry.path)[1] if entry.is_file() else "directory",
                          None if not entry.is_dir() else self.get_dir_content(entry.path, include_files, recursive,
                                                                               filter) if recursive else None)
            if include_files or entry.is_dir():
                ui_path = str(entry.path)
                ui_path = ui_path.replace(self.current_dir, "")
                ui_path = ui_path.lstrip("/\\")  # Removes leading forward or backward slashes
                result[ui_path] = entry_data
        return result

    def change_dir(self, path: str, recursive: bool = False, filter: Union[str, List[str]] = None) -> Dict[
        str, Tuple[str, int, str, Union[None, Dict]]]:
        full_path = os.path.abspath(os.path.join(self.current_dir, path))
        if not full_path.startswith(self.user_dir):
            return {}
        if not os.path.isdir(full_path):
            return {}
        self.current_dir = full_path
        return self.get_dir_content(include_files=True, recursive=recursive, filter=filter)

    def go_back(self, num_levels: int = 1, recursive: bool = False, filter: Union[str, List[str]] = None) -> Dict[
        str, Tuple[str, int, str, Union[None, Dict]]]:
        path = self.current_dir
        for _ in range(num_levels):
            path = os.path.dirname(path)
            if path == self.user_dir or path == "":
                break
        if path != self.user_dir:
            return {}
        self.current_dir = path
        return self.get_dir_content(include_files=True, recursive=recursive, filter=filter)

    def reset_dir(self, recursive: bool = False, filter: Union[str, List[str]] = None) -> Dict[
        str, Tuple[str, int, str, Union[None, Dict]]]:
        self.current_dir = self.user_dir
        return self.get_dir_content(include_files=True, recursive=recursive, filter=filter)


def list_features():
    # Create buffer for pilinfo() to write into rather than stdout
    buffer = StringIO()
    features.pilinfo(out=buffer)
    pil_features = []
    # Parse and analyse lines
    for line in buffer.getvalue().splitlines():
        if "Extensions:" in line:
            ext_list = line.split(": ")[1]
            extensions = ext_list.split(", ")
            for extension in extensions:
                if extension not in pil_features:
                    pil_features.append(extension)
    return pil_features


def is_image(path: str, feats=None):
    if feats is None:
        feats = []
    if not len(feats):
        feats = list_features()
    is_img = os.path.isfile(path) and os.path.splitext(path)[1].lower() in feats
    return is_img
