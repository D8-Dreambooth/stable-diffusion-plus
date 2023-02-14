from core.handlers.cache import CacheHandler


class ConfigHandler(CacheHandler):
    def __init__(self, config_dir):
        super().__init__(config_dir)
