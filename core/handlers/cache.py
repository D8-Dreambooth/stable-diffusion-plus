import json
import os


class CacheHandler:
    _instance = None
    cache_dir = ""
    cache = {}

    def __new__(cls, cache_dir=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.cache_dir = cache_dir
            if cache_dir:
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir)
        return cls._instance

    def get(self, cache_name, key=None, default=None):
        if cache_name in self.cache:
            if key is None:
                return self.cache[cache_name]
            else:
                return self.cache[cache_name].get(key, default)
        else:
            cache_file = os.path.join(self.cache_dir, cache_name + ".json")
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    try:
                        self.cache[cache_name] = json.load(f)
                        if key is None:
                            return self.cache[cache_name]
                        else:
                            return self.cache[cache_name].get(key, default)
                    except json.JSONDecodeError as e:
                        print(f"Error reading cache file: {e}")
                        self.cache[cache_name] = {}
            else:
                self.cache[cache_name] = {}
        return default

    def set(self, cache_name, key=None, value=None, cache_data=None):
        cache_file = os.path.join(self.cache_dir, cache_name + ".json")
        print(f"Cache file: {cache_file}")
        if cache_data:
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)
        elif key and value:
            if cache_name in self.cache:
                self.cache[cache_name][key] = value
            else:
                if os.path.exists(cache_file):
                    with open(cache_file, "r") as f:
                        try:
                            self.cache[cache_name] = json.load(f)
                        except json.JSONDecodeError as e:
                            print(f"Error reading cache file: {e}")
                            self.cache[cache_name] = {}
                else:
                    self.cache[cache_name] = {}
                self.cache[cache_name][key] = value
            with open(cache_file, "w") as f:
                json.dump(self.cache[cache_name], f)
