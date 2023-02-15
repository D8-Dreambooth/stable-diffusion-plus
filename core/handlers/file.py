import os
from typing import Dict, List, Tuple, Union

from starlette.websockets import WebSocket

from core.handlers.websockets import SocketHandler


class FileHandler:
    _instance = None
    user_dir = None
    current_dir = None
    socket_handler = None

    def __new__(cls, user_dir=None):
        if cls._instance is None and user_dir is not None:
            cls._instance = super(FileHandler, cls).__new__(cls)
            cls._instance.user_dir = user_dir
            cls._instance.current_dir = user_dir
            socket_handler = SocketHandler()
            socket_handler.register("files", cls._instance.pass_dir_content)

        return cls._instance

    async def pass_dir_content(self, websocket: WebSocket, data):
        print(f"Passed: {data}")
        res = self.get_dir_content(data["start_dir"], data["include_files"], data["recursive"], data["filter"])
        current_path = self.current_dir.replace(self.user_dir, "")
        if current_path == "":
            current_path = os.path.sep
        result = {
            "items": res,
            "current": current_path,
            "separator": os.path.sep
        }
        print(f"No, really, got: {result}")
        return result

    def get_dir_content(self, start_dir: str = None, include_files: bool = False, recursive: bool = False,
                        filter: Union[str, List[str]] = None) -> Dict[str, Tuple[str, int, str, Union[None, Dict]]]:
        if start_dir is not None:
            start_dir = os.path.abspath(os.path.join(self.current_dir, start_dir))
            if not start_dir.startswith(self.user_dir):
                print(f"INVALID PATH SPECIFIED: {start_dir}")
            else:
                self.current_dir = start_dir
            print(f"Current dir: {self.current_dir}")

        if not os.path.isdir(self.current_dir):
            print("Invalid current directory.")
            return {}

        result = {}
        print("Scanning...")
        for entry in os.scandir(self.current_dir):
            if filter is not None:
                if isinstance(filter, str):
                    if not entry.name.endswith(filter):
                        continue
                elif isinstance(filter, list) and len(filter):
                    print("Filter junk?")
                    if not any(entry.name.endswith(ext) for ext in filter):
                        print("Nothing to filter.")
                        continue
            entry_data = (entry.stat().st_mtime, entry.stat().st_size, os.path.splitext(entry.path)[1] if entry.is_file() else "directory",
                          None if not entry.is_dir() else self.get_dir_content(entry.path, include_files, recursive,
                                                                               filter) if recursive else None)
            if include_files or entry.is_dir():
                print(f"Appending: {entry_data}")
                ui_path = str(entry.path)
                ui_path = ui_path.replace(self.current_dir, "")
                ui_path = ui_path.lstrip("/\\")  # Removes leading forward or backward slashes
                result[ui_path] = entry_data
        print(f"Result: {result}")
        return result

    def change_dir(self, path: str, recursive: bool = False, filter: Union[str, List[str]] = None) -> Dict[
        str, Tuple[str, int, str, Union[None, Dict]]]:
        full_path = os.path.abspath(os.path.join(self.current_dir, path))
        if not full_path.startswith(self.user_dir):
            print("Invalid directory. Must be within the user directory.")
            return {}
        if not os.path.isdir(full_path):
            print("Invalid directory.")
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
            print("Invalid directory.")
            return {}
        self.current_dir = path
        return self.get_dir_content(include_files=True, recursive=recursive, filter=filter)

    def reset_dir(self, recursive: bool = False, filter: Union[str, List[str]] = None) -> Dict[
        str, Tuple[str, int, str, Union[None, Dict]]]:
        self.current_dir = self.user_dir
        return self.get_dir_content(include_files=True, recursive=recursive, filter=filter)
