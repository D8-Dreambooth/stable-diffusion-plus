import base64
import logging
import os
import shutil
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
            socket_handler.register("handleFile", cls._instance.handle_file)
        if user_name is not None:
            if user_name in cls._instances:
                return cls._instances[user_name]
            else:
                user_instance = super(FileHandler, cls).__new__(cls)
                user_instance.logger = logging.getLogger(f"{__name__}-{user_name}")
                dir_handler = DirectoryHandler(user_name=user_name)
                user_dir = dir_handler.get_directory(user_name)[0]
                user_instance.logger.debug(f"USER DIR: {user_dir}")
                user_instance.user_dir = user_dir
                user_instance.app = cls._instance.app
                user_instance.current_dir = user_dir
                socket_handler = SocketHandler()
                socket_handler.register("files", user_instance.pass_dir_content, user_name)
                socket_handler.register("file", user_instance.get_file, user_name)
                socket_handler.register("handleFile", user_instance.handle_file, user_name)
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

    async def handle_file(self, request: Dict):
        # This is the actual data from js
        data = request["data"]
        # This is the root in which our current path can be combined
        base_dir = self.user_dir.rstrip(os.path.sep)
        self.logger.debug(f"Base dir: {base_dir}")
        method = data["method"]
        files = data["files"]
        directory = data["dir"].lstrip(os.path.sep)

        # Combine the base dir with the directory to get the full path
        full_path = os.path.join(base_dir, directory)
        self.logger.debug(f"Full path is: {full_path}, method is {method}")

        if method == "delete":
            for file in files:
                file_path = os.path.join(full_path, file)
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                except OSError:
                    pass
        elif method == "rename":
            if len(files) != 1:
                # Show error message that too many files are selected for rename
                print("Error: too many files selected for rename.")
            else:
                old_file_path = os.path.join(full_path, files[0])
                new_file_name = data["newName"]
                if new_file_name:
                    new_file_path = os.path.join(full_path, new_file_name)
                    try:
                        os.rename(old_file_path, new_file_path)
                    except OSError:
                        # Show
                        # error message that file could not be renamed
                        print("Error: file could not be renamed.")

        elif method == "new":
            for file in files:
                file_path = os.path.join(full_path, file)
                self.logger.debug(f"Making: {file_path}")

                if not os.path.exists(file_path):
                    os.makedirs(file_path)

        data["status"] = "successful"
        return data

    async def get_file(self, request: Dict):
        pil_features = list_features()
        data = request["data"]
        self.logger.debug(f"File request: {data}")
        file = data["files"]
        files = []
        if isinstance(file, str):
            full_file = os.path.join(self.current_dir, file)
            self.logger.debug(f"Full file: {full_file}")
            if os.path.exists(full_file):
                files.append(full_file)
        if isinstance(file, list):
            for check in file:
                full_file = os.path.join(self.current_dir, check)
                self.logger.debug(f"Full file: {full_file}")
                if os.path.exists(full_file):
                    files.append(full_file)

        if not files:
            return {"error": "File not found"}

        def sizeof_fmt(num, suffix='B'):
            for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
                if abs(num) < 1024.0:
                    return f"{num:.1f} {unit}{suffix}"
                num /= 1024.0
            return f"{num:.1f} Yi{suffix}"

        def get_file_size(path):
            if os.path.isfile(path):
                return os.path.getsize(path)
            elif os.path.isdir(path):
                size = 0
                with os.scandir(path) as entries:
                    for entry in entries:
                        if entry.is_file():
                            size += entry.stat().st_size
                        elif entry.is_dir():
                            size += get_file_size(entry.path)
                return size
            else:
                return 0

        urls = []
        for filename in files:

            file_dict = {
                "filename": os.path.basename(filename),
                "date_created": datetime.fromtimestamp(os.path.getctime(filename)).strftime("%Y-%m-%d %H:%M:%S"),
                "date_modified": datetime.fromtimestamp(os.path.getmtime(filename)).strftime("%Y-%m-%d %H:%M:%S"),
                "size": sizeof_fmt(get_file_size(filename))
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
                    tag_data = ""
                    with Image.open(filename) as img:
                        if filename.endswith(".png"):
                            png_info = img.info

                            # Check if "parameters" field is set
                            if "parameters" in png_info:
                                # Extract generation parameters from text
                                tag_data = png_info["parameters"]
                        with BytesIO() as output:
                            img.save(output, format="JPEG")
                            contents = output.getvalue()
                            file_dict["src"] = f"data:image/jpeg;base64,{base64.b64encode(contents).decode()}"

                    txt_filename = os.path.splitext(filename)[0] + ".txt"
                    txt_data = ""
                    if os.path.exists(txt_filename) and os.path.isfile(txt_filename):
                        try:
                            with open(txt_filename, "r") as f:
                                txt_data = f.read()
                        except:
                            pass
                    data_data = ""
                    if tag_data and txt_data:
                        data_data = "\n\n".join([tag_data, txt_data])
                    elif tag_data:
                        data_data = tag_data
                    elif txt_data:
                        data_data = txt_data
                    if data_data:
                        file_dict["data"] = data_data

                except:
                    pass

            urls.append(file_dict)

        return {"files": urls}

    def save_file(self, dest_dir, file_name, file_contents):
        self.logger.debug(f"User dir: {self.user_dir}")
        dir_handler = DirectoryHandler(user_name=self.user_name)
        self.user_dir = dir_handler.get_directory(self.user_name)[0]

        # Normalize the dest_dir parameter before joining it with the user directory
        dest_dir = os.path.normpath(dest_dir)
        file_path = os.path.join(f"{self.user_dir}{dest_dir}", file_name)
        self.logger.debug(f"We need to save a file from {dest_dir}: {file_path}")

        # Open the file and write the contents to it
        with open(file_path, "wb") as f:
            f.write(file_contents)

    def get_dir_content(self, start_dir: str = None, include_files: bool = False, recursive: bool = False,
                        filter: Union[str, List[str]] = None) -> Dict[str, Tuple[str, int, str, Union[None, Dict]]]:
        if start_dir is not None:
            start_dir = os.path.normpath(start_dir).strip(os.pathsep)
            self.logger.debug(f"Trying to join {self.user_dir} and {start_dir}")
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
            entry_data = (entry.stat().st_mtime, entry.stat().st_size,
                          os.path.splitext(entry.path)[1] if entry.is_file() else "directory",
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
