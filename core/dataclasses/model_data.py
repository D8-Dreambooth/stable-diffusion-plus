import hashlib
import os

from core.handlers.cache import CacheHandler


class ModelData:
    name = ""
    path = ""
    hash = ""
    is_url = False
    loader = None

    def __init__(self, model_path, loader=None):
        self.path = model_path
        if not os.path.exists(model_path):
            if "http" not in model_path:
                raise Exception("File does not exist at the specified path")
            else:
                self.is_url = True
        else:
            cache_handler = CacheHandler()
            existing_hash = cache_handler.get("model_hash", model_path)
            if existing_hash:
                self.hash = existing_hash
            else:
                with open(model_path, "rb") as f:
                    # use sha256 hash algorithm to calculate the hash
                    hash_obj = hashlib.sha256()
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        hash_obj.update(chunk)
                    self.hash = hash_obj.hexdigest()

        self.name = os.path.basename(model_path)
        self.loader = loader

    def display_name(self):
        return self.name + " [" + self.hash[:6] + "]"
