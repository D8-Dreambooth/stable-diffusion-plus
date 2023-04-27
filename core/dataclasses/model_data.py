import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Dict

from core.handlers.cache import CacheHandler
logger = logging.getLogger(__name__)

@dataclass
class ModelData:
    name: str
    path: str
    hash: str
    is_url: bool
    loader: any
    data: Dict
    display_name: ""

    def __init__(self, model_path, name=None, loader=None):
        self.path = model_path
        self.loader = loader
        self.data = {}
        if not os.path.exists(model_path):
            if "http" not in model_path:
                raise Exception("File does not exist at the specified path")
            else:
                self.hash = ""
                self.is_url = True
        else:
            self.is_url = False
            self.get_hash(model_path)
        self.name = name if name else os.path.basename(model_path)
        self.display_name = self.name + " [" + self.hash[:6] + "]" if self.hash else self.name

    def serialize(self):
        return {
            "name": self.name,
            "path": self.path,
            "hash": self.hash,
            "is_url": self.is_url,
            "loader": self.loader,
            "display_name": self.display_name,
            "data": self.data
        }

    def get_hash(self, model_path):
        cache_handler = CacheHandler()
        if os.path.isfile(model_path):
            # If model_path is a file, calculate the hash for the file
            existing_hash = cache_handler.get("model_hash", model_path)
            if existing_hash is not None:
                self.hash = existing_hash
            else:
                with open(model_path, "rb") as f:
                    # use sha256 hash algorithm to calculate the hash
                    hash_obj = hashlib.sha256()
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        hash_obj.update(chunk)
                    self.hash = hash_obj.hexdigest()
                    cache_handler.set("model_hash", model_path, self.hash)
        elif os.path.isdir(model_path):
            # If model_path is a directory, calculate the hash for all files in the directory
            existing_hash = cache_handler.get("directory_hash", model_path)
            if existing_hash is not None:
                self.hash = existing_hash
            else:
                hash_obj = hashlib.sha256()
                for dirpath, dirnames, filenames in os.walk(model_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        with open(filepath, "rb") as f:
                            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                                hash_obj.update(chunk)
                self.hash = hash_obj.hexdigest()
                cache_handler.set("directory_hash", model_path, self.hash)
        else:
            raise ValueError(f"{model_path} is not a valid file or directory.")

    def deserialize(self, data: Dict):
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)