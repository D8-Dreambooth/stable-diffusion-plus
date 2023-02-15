import hashlib
import os
from dataclasses import dataclass

from core.handlers.cache import CacheHandler


@dataclass
class ModelData:
    name: str
    path: str
    hash: str
    is_url: bool
    loader: any

    def __init__(self, model_path, loader=None):
        self.path = model_path
        self.loader = loader
        if not os.path.exists(model_path):
            if "http" not in model_path:
                raise Exception("File does not exist at the specified path")
            else:
                self.is_url = True
        else:
            self.is_url = False
            cache_handler = CacheHandler()
            existing_hash = cache_handler.get("model_hash", model_path)
            if existing_hash:
                self.hash = existing_hash
            else:
                print(f"Calculating hash for {model_path}")
                with open(model_path, "rb") as f:
                    # use sha256 hash algorithm to calculate the hash
                    hash_obj = hashlib.sha256()
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        hash_obj.update(chunk)
                    self.hash = hash_obj.hexdigest()
                    cache_handler.set("model_hash", model_path, self.hash)

        self.name = os.path.basename(model_path)

    def display_name(self):
        return self.name + " [" + self.hash[:6] + "]"

    def serialize(self):
        return {
            "name": self.name,
            "path": self.path,
            "hash": self.hash,
            "is_url": self.is_url,
            "loader": self.loader,
            "display_name": self.display_name()
        }