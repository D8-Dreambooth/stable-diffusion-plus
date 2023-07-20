import json
import logging
import os

from core.handlers.directories import DirectoryHandler


class HistoryHandler:
    _instance = None
    _instances = {}
    user_dir = None

    def __new__(cls, user_name=None):
        from core.handlers.websocket import SocketHandler

        if cls._instance is None:
            dir_handler = DirectoryHandler()
            cls._instance = super(HistoryHandler, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(f"{__name__}-shared")
            user_dir = None
            cls._instance.shared_dir = dir_handler.shared_path
            cls._instance.user_dir = user_dir
            socket_handler = SocketHandler()
            socket_handler.register("get_history", cls._instance.get_history)
            socket_handler.register("delete_history", cls._instance.delete_history)

        if user_name is not None:

            if user_name in cls._instances:
                return cls._instances[user_name]
            else:
                user_instance = super(HistoryHandler, cls).__new__(cls)
                user_instance.logger = logging.getLogger(f"{__name__}-{user_name}")
                dir_handler = DirectoryHandler(user_name=user_name)
                user_dir = dir_handler.get_directory(user_name)[0]
                user_instance.user_dir = user_dir
                socket_handler = SocketHandler()
                socket_handler.register("get_history", user_instance.get_history, user_name)
                socket_handler.register("delete_history", user_instance.delete_history, user_name)
                user_instance.user_name = user_name
                cls._instances[user_name] = user_instance
                return user_instance
        else:
            return cls._instance

    def set_history(self, history: dict, module: str):
        history_dir = os.path.join(self.user_dir, "history")
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
        history_file = os.path.join(history_dir, f"{module}.json")
        history_entries = []
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history_entries = json.load(f)
        history_entries.insert(0, history)
        with open(history_file, "w") as f:
            json.dump(history_entries, f)
        return

    async def get_history(self, data: dict) -> dict:
        index = data.get("index", 0)
        module = data.get("module", "infer")
        history_dir = os.path.join(self.user_dir, "history")
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
        history_file = os.path.join(history_dir, f"{module}.json")
        history_entries = []
        history = {}
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history_entries = json.load(f)
        if index < len(history_entries):
            history = history_entries[index]
        if module == "infer":
            from core.handlers.images import decode_dict
            history = decode_dict(history)
        return {"history": history}

    async def delete_history(self, data: dict) -> None:
        index = data.get("index", 0)
        history_dir = os.path.join(self.user_dir, "history")
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
        history_file = os.path.join(history_dir, "infer.json")
        history_entries = []
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history_entries = json.load(f)
        if index < len(history_entries):
            history_entries.pop(index)
        with open(history_file, "w") as f:
            json.dump(history_entries, f)
