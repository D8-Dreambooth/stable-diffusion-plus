import base64
import json
import logging
import os
import shutil
import traceback
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple, Union

from PIL import Image
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from core.handlers.directories import DirectoryHandler
from core.handlers.users import get_user
from core.handlers.websocket import SocketHandler


class FileHandler:
    _instance = None
    _instances = {}
    user_dir = None
    shared_dir = None
    protected_dir = None
    user_name = None
    current_dir = None
    socket_handler = None
    logger = None
    show_protected = False
    show_shared = True
    templates = Jinja2Templates(directory="templates")
    app = None

    def __new__(cls, app=None, user_name=None):
        if cls._instance is None and app:
            dir_handler = DirectoryHandler()
            cls._instance = super(FileHandler, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(f"{__name__}-shared")
            app.mount("/static", StaticFiles(directory="static"), name="static")
            cls._instance.app = app
            user_dir = None
            cls._instance.shared_dir = dir_handler.shared_path
            cls._instance.user_dir = user_dir
            socket_handler = SocketHandler()
            socket_handler.register("files", cls._instance.pass_dir_content)
            socket_handler.register("file", cls._instance.get_file)
            socket_handler.register("handleFile", cls._instance.handle_file)
            socket_handler.register("saveFile", cls._instance.save_file_async)

        if user_name is not None:
            if user_name in cls._instances:
                return cls._instances[user_name]
            else:
                user_instance = super(FileHandler, cls).__new__(cls)
                user_instance.logger = logging.getLogger(f"{__name__}-{user_name}")
                dir_handler = DirectoryHandler(user_name=user_name)
                user_data = get_user(user_name)
                if user_data:
                    if user_data["admin"] and not user_data["disabled"]:
                        user_instance.show_protected = True
                        user_instance.protected_dir = dir_handler.protected_path
                user_instance.shared_dir = dir_handler.shared_path
                user_dir = dir_handler.get_directory(user_name)[0]
                user_instance.user_dir = user_dir
                user_instance.app = cls._instance.app
                socket_handler = SocketHandler()
                socket_handler.register("files", user_instance.pass_dir_content, user_name)
                socket_handler.register("file", user_instance.get_file, user_name)
                socket_handler.register("handleFile", user_instance.handle_file, user_name)
                socket_handler.register("saveFile", user_instance.save_file_async, user_name)
                user_instance.user_name = user_name
                cls._instances[user_name] = user_instance
                return user_instance
        else:
            return cls._instance

    async def pass_dir_content(self, request):
        data = request["data"]
        self.logger.debug(f"Passing dir content: {data}")
        protected = data["protected"] if "protected" in data else False
        shared = data["shared"] if "shared" in data else False
        user = request["user"] if "user" in request else None
        user_data = get_user(user)
        show_protected = user_data["admin"] if user_data else False
        show_shared = True
        base_path = self.user_dir
        if shared:
            base_path = self.shared_dir
        elif protected:
            if user is None:
                return {"error": "User not specified, required for protected directories."}
            if user_data is None:
                return {"error": "User not found, required for protected directories."}
            if not user_data["admin"]:
                return {"error": "User is not admin, required for protected directories."}
            base_path = self.protected_dir
        self.logger.debug(f"Base path: {base_path}")
        thumbs = data["thumbs"] if "thumbs" in data else False
        thumb_size = data["thumb_size"] if "thumb_size" in data else 128
        res = self.get_dir_content(base_path, data["start_dir"], data["include_files"], data["recursive"], data["filter"])
        current_path = os.path.abspath(os.path.join(base_path, data["start_dir"])) if data["start_dir"] else base_path

        if current_path == "" or current_path == base_path:
            current_path = ""
        if thumbs:
            new_res = {}
            for item_path, value in res.items():
                full_path = os.path.join(base_path, item_path)
                if is_image(full_path):
                    value["thumb"], value["tag"] = await self.get_thumbnail(full_path, thumb_size)
                new_res[item_path] = value
            res = new_res
        result = {
            "items": res,
            "current": current_path.replace(f"{base_path}{os.path.sep}", ""),
            "separator": os.path.sep,
            "show_protected": show_protected,
            "show_shared": show_shared,
        }
        return result

    async def handle_file(self, request: Dict):
        # This is the actual data from js
        data = request["data"]
        protected = data["protected"] if "protected" in data else False
        shared = data["shared"] if "shared" in data else False
        user = request["user"] if "user" in request else None
        base_path = self.user_dir
        if protected or shared:
            if user is None:
                return {"error": "User not specified, required for protected/shared directories."}
            user_data = get_user(user)
            if user_data is None:
                return {"error": "User not found, required for protected/shared directories."}
            if not user_data["admin"]:
                return {"error": "User is not admin, required for protected directories."}
            base_path = self.protected_dir if protected else self.shared_dir
        # This is the root in which our current path can be combined
        base_dir = base_path.rstrip(os.path.sep)
        method = data["method"]
        files = data["files"]
        directory = data["dir"].lstrip(os.path.sep)

        # Combine the base dir with the directory to get the full path
        full_path = os.path.join(base_dir, directory)

        if method == "delete":
            for file in files:
                file_path = os.path.join(base_path, file)
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                except OSError as e:
                    print("Exception deleting: ", e)
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

                if not os.path.exists(file_path):
                    os.makedirs(file_path)
        data["status"] = "successful"
        return data

    async def get_file(self, request: Dict):
        data = request["data"]
        protected = data["protected"] if "protected" in data else False
        shared = data["shared"] if "shared" in data else False
        user = request["user"] if "user" in request else None
        base_path = self.user_dir
        if shared:
            base_path = self.shared_dir
        if protected:
            if user is None:
                return {"error": "User not specified, required for protected directories."}
            user_data = get_user(user)
            if user_data is None:
                return {"error": "User not found, required for protected directories."}
            if not user_data["admin"]:
                return {"error": "User is not admin, required for protected directories."}
            base_path = self.protected_dir

        file = data["files"]
        thumbs = data["thumbs"] if "thumbs" in data else False
        thumb_size = data["thumb_size"] if "thumb_size" in data else 128
        return_pil = data["return_pil"] if "return_pil" in data else False
        files = []
        if isinstance(file, str):
            file = [file]

        if isinstance(file, list):
            for check in file:
                full_file = os.path.abspath(os.path.join(base_path, check))
                if os.path.exists(full_file) and full_file.startswith(base_path):
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
            if is_image(filename):
                try:
                    tag_data = ""
                    with Image.open(filename) as img:
                        img = img.convert("RGB")
                        if thumbs:
                            # Scale the image while preserving aspect ratio
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

                        if return_pil:
                            file_dict["image"] = img
                        else:
                            with BytesIO() as output:
                                img.save(output, format="JPEG")
                                contents = output.getvalue()
                                file_dict["src"] = f"data:image/jpeg;base64,{base64.b64encode(contents).decode()}"

                            if filename.endswith(".png"):
                                png_info = img.info

                                # Check if "parameters" field is set
                                if "parameters" in png_info:
                                    # Extract generation parameters from text
                                    tag_data = png_info["parameters"]

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

                except Exception as e:
                    self.logger.warning(f"Unable to fetch png info: {e}")
                    traceback.print_exc()
                    pass

            urls.append(file_dict)

        return {"files": urls}

    async def save_file_async(self, request):
        data = request["data"]
        self.logger.debug(f"Saving file: {data}")
        path = data["path"]
        file_data = data["file_data"]
        protected = data["protected"]
        shared = data["shared"]

        user = request["user"] if "user" in request else None
        user_data = get_user(user)
        show_protected = user_data["admin"] if user_data else False
        show_shared = True
        base_path = self.user_dir
        if shared:
            base_path = self.shared_dir
        elif protected:
            if user is None:
                return {"error": "User not specified, required for protected directories."}
            if user_data is None:
                return {"error": "User not found, required for protected directories."}
            if not user_data["admin"]:
                return {"error": "User is not admin, required for protected directories."}
            base_path = self.protected_dir
        if base_path not in path:
            self.logger.warning(f"Invalid path: {path}")
            return {"error": "Invalid path."}
        with open(path, "w") as f:
            json.dump(file_data, f, indent=4)
        return {"saved": "true"}

    def save_file(self, dest_dir, file_name, file_contents):
        dir_handler = DirectoryHandler(user_name=self.user_name)
        self.user_dir = dir_handler.get_directory(self.user_name)[0]
        # Normalize the dest_dir parameter before joining it with the user directory
        dest_dir = os.path.normpath(dest_dir)
        file_path = os.path.join(self.user_dir, dest_dir, file_name)

        # Open the file and write the contents to it
        with open(file_path, "wb") as f:
            f.write(file_contents)
        return file_path

    async def get_thumbnail(self, filename, thumb_size):
        tag_data = ""
        img_src = ""
        try:
            with Image.open(filename) as img:
                img = img.convert("RGB")
                if filename.endswith(".png"):
                    png_info = img.info

                    # Check if "parameters" field is set
                    if "parameters" in png_info:
                        # Extract generation parameters from text
                        tag_data = png_info["parameters"].split("\n")[0]

                # Crop the image to a square with dimensions of thumb_size x thumb_size
                width, height = img.size
                short_side = width if width < height else height
                new_ratio = thumb_size / short_side
                img.thumbnail((width * new_ratio, height * new_ratio), Image.ANTIALIAS)
                width, height = img.size
                left = (width - thumb_size) / 2
                top = (height - thumb_size) / 2
                right = (width + thumb_size) / 2
                bottom = (height + thumb_size) / 2
                img = img.crop((left, top, right, bottom))
                with BytesIO() as output:
                    img.save(output, format="JPEG")
                    contents = output.getvalue()
                    img_src = f"data:image/jpeg;base64,{base64.b64encode(contents).decode()}"

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
                data_data = ", ".join([tag_data, txt_data])
            elif tag_data:
                data_data = tag_data
            elif txt_data:
                data_data = txt_data
            if data_data:
                tag_data = data_data
        except:
            pass
        return img_src, tag_data

    def get_dir_content(self, base_path, start_dir: str, include_files: bool = False, recursive: bool = False,
                        filter: Union[str, List[str]] = None) -> Dict[str, Tuple[str, int, str, Union[None, Dict]]]:

        start_dir = os.path.join(base_path, start_dir)
        start_dir = os.path.abspath(start_dir)
        if not start_dir.startswith(base_path) or not os.path.isdir(start_dir):
            start_dir = base_path

        result = {}

        for entry in os.scandir(start_dir):
            if filter is not None and entry.is_file():
                if isinstance(filter, str):
                    if not entry.name.endswith(filter):
                        continue
                elif isinstance(filter, list) and len(filter):
                    if not any(entry.name.endswith(ext) for ext in filter):
                        continue

            if include_files or entry.is_dir():
                entry_data_2 = {
                    "time": entry.stat().st_mtime,
                    "size": entry.stat().st_size,
                    "type": os.path.splitext(entry.path)[1] if entry.is_file() else "directory",
                    "fullPath": entry.path
                }

                if entry.is_dir() and recursive:
                    sub_res = self.get_dir_content(base_path, entry.path, include_files, recursive, filter)
                    for key, value in sub_res.items():
                        result[key] = value

                ui_path = str(entry.path)
                ui_path = ui_path.replace(base_path, "")
                ui_path = ui_path.lstrip("/\\")  # Removes leading forward or backward slashes
                result[ui_path] = entry_data_2

        result[".."] = {"path": start_dir.replace(f"{base_path}{os.path.sep}", "")}

        return result


def is_image(path: str, feats=None):
    extensions = Image.registered_extensions()
    supported_extensions = {ex for ex, f in extensions.items() if f in Image.OPEN}
    filename, file_ext = os.path.splitext(path.strip())
    file_ext = file_ext.lower()
    is_img = os.path.isfile(path) and file_ext in supported_extensions
    if not is_img:
        logging.getLogger(__name__).debug(f"File {path}({file_ext}) is not an image: {supported_extensions}")
    return is_img

