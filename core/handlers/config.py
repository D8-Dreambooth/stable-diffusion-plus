import inspect
import json
import logging
import os
import re
import shutil
from typing import Dict, Tuple

from core.handlers.directories import DirectoryHandler

logger = logging.getLogger(__name__)


class ConfigHandler:
    _instance = None
    _shared_dir = None
    _protected_dir = None
    _user_dir = None
    _base_defaults = None
    _user_defaults = None
    config_shared = {}
    config_protected = {}
    config_user = None
    user_instances = {}

    def __new__(cls, user_name=None):
        if cls._instance is None:
            cls._instance = super(ConfigHandler, cls).__new__(cls)
            dir_handler = DirectoryHandler()
            cls._instance._shared_dir = os.path.join(dir_handler.shared_path, "config")
            cls._instance._protected_dir = os.path.join(dir_handler.protected_path, "config")
            cls._instance._base_defaults = os.path.join(dir_handler.protected_path, "defaults")
            cls._instance._create_directories()
            cls._instance._check_defaults(dir_handler.app_path)
            cls._instance._enumerate_configs()

        if user_name is not None:
            if user_name not in cls.user_instances:
                valid_user = None
                user_data = cls._instance.get_config_protected("users")
                if user_name in user_data:
                    valid_user = user_data[user_name]
                if valid_user is None:
                    logger.error(f"User {user_name} not found")
                    return None
                disabled = False if "disabled" not in valid_user else valid_user["disabled"]
                if disabled:
                    logger.error(f"User {user_name} is disabled")
                    return None
                user_instance = super(ConfigHandler, cls).__new__(cls)
                dir_handler = DirectoryHandler()
                user_instance._shared_dir = os.path.join(dir_handler.shared_path, "config")
                if valid_user["admin"]:
                    user_instance._protected_dir = os.path.join(dir_handler.protected_path, "config")
                else:
                    user_instance._protected_dir = None
                user_instance._user_dir = os.path.join(dir_handler.protected_path, "users", user_name, "config")
                user_instance.config_user = {}
                user_instance._base_defaults = os.path.join(dir_handler.protected_path, "users", user_name, "defaults")
                # Enumerate all files in cls._base_defaults and copy to user defaults if not already present
                user_instance._create_directories()

                for file in os.listdir(cls._instance._base_defaults):
                    target = os.path.join(user_instance._base_defaults, file)
                    if not os.path.isfile(target):
                        shutil.copy(os.path.join(cls._instance._base_defaults, file), target)
                user_instance._check_defaults(dir_handler.app_path)
                user_instance._enumerate_configs()
                cls.user_instances[user_name] = user_instance
            return cls.user_instances[user_name]

        return cls._instance

    async def socket_set_config(self, data):
        logger.debug(f"Set socket config: {data}")

    async def socket_get_all(self, req):
        user = req.get("user", None)
        from core.handlers.modules import ModuleHandler
        ch = ConfigHandler()
        module_data = await ModuleHandler().get_module_data()
        locales = self.get_locales()
        shared_config, protected_config, user_config = ch.get_all_protected()
        user_lang = self.get_item_protected("language", "core", "en")
        locale = locales.get(user_lang) if user_lang in locales else locales["en"]
        user_data = ch.get_item_protected(user, "users", None)
        users = protected_config.pop("users", {})
        ui_users = []
        if user_data:
            is_admin = user_data.get("admin", False)
            if is_admin:
                sorted_users = sorted(users.values(), key=lambda u: u.get("name") != user_data.get("name"))
                ui_users = sorted_users
            else:
                ui_data = user_data.copy()
                del ui_data["admin"]
                del ui_data["disabled"]
                del ui_data["pass"]
                ui_users = [ui_data]

        protected_config["users"] = []
        for user in ui_users:
            if "pass" in user:
                del user["pass"]
            protected_config["users"].append(user)
        del user_data["pass"]
        response = {
            "status": "ACK ACK",
            "shared": shared_config,
            "protected": protected_config,
            "user": user_data,
            "locales": locale,
            "modules": module_data
        }

        return response

    async def socket_get_config(self, data):
        self._enumerate_configs()
        key = data["data"]["section_key"] if "section_key" in data["data"] else None
        data = self.get_config_protected(key)
        from core.handlers.modules import ModuleHandler
        module_data = ModuleHandler().get_modules()
        return {"modules": module_data, "config": data}

    async def socket_set_config_item(self, data):
        self._enumerate_configs()
        section_key = data["section_key"] if "section_key" in data else None
        key = data["key"] if "key" in data else None
        value = data["value"] if "value" in data else None
        if key and value:
            self.set_item(key, value, section_key)
        value = self.get_item(key, section_key)
        return {"name": "set_config_item", key: value}

    async def socket_get_config_item(self, data):
        self._enumerate_configs()
        section_key = data["section_key"] if "section_key" in data else None
        key = data["key"] if "key" in data else None
        if section_key == "core":
            return self.get_item_protected(key, section_key)
        else:
            return self.get_item(key, section_key)

    def _check_defaults(self, script_path):
        if not any(frame.filename == __file__ for frame in inspect.getouterframes(inspect.currentframe(), 2)):
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')
        source_dir = os.path.join(script_path, "templates")
        sources = ["config", "defaults", "locales"]
        dir_handler = DirectoryHandler()
        protected_dir = dir_handler.protected_path
        for source in sources:
            s_dir = os.path.join(source_dir, source)
            if not os.path.exists(s_dir):
                os.makedirs(s_dir)
            dest_dir = os.path.join(protected_dir, source)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            for file in [f for f in os.listdir(s_dir) if os.path.splitext(f)[1] == ".json"]:
                src_path = os.path.join(s_dir, file)
                if self._protected_dir:
                    dst_path = os.path.join(dest_dir, file)
                    if not os.path.exists(dst_path):
                        shutil.copy(src_path, dst_path)
                    else:
                        if "users" not in file:
                            self.update_keys(src_path, dst_path)

    def set_module_default(self, file, module_name):
        # Strip any characters from module_name that are not valid in a path
        module_name = re.sub(r'[^a-zA-Z0-9_]', '', module_name)
        default_file = os.path.join(self._base_defaults, f"{module_name}.json")
        # Copy file to default_file if it doesn't exist
        if not os.path.exists(default_file):
            shutil.copy(file, default_file)
        else:
            self.update_keys(file, default_file)

    def get_module_defaults(self, module_name):
        module_name = re.sub(r'[^a-zA-Z0-9]', '', module_name)
        default_file = os.path.join(self._base_defaults, f"{module_name}.json")
        if os.path.exists(default_file):
            with open(default_file, "r") as file:
                return json.load(file)
        return {}

    def update_keys(self, template_path, live_path):
        try:
            # Load the template and live JSON data from files
            with open(template_path, "r") as template_file:
                template = json.load(template_file)
            with open(live_path, "r") as live_file:
                live = json.load(live_file)

            # Create sets of keys for the template and live JSON objects
            template_keys = set(template.keys())
            live_keys = set(live.keys())

            # Remove extra keys in the live JSON object that are not in the template
            for key in live_keys - template_keys:
                del live[key]

            # Add missing keys to the live JSON object from the template
            for key in template_keys - live_keys:
                live[key] = template[key]

            # Save the updated live JSON data to file
            with open(live_path, "w") as live_file:
                json.dump(live, live_file, indent=4)
        except Exception as e:
            pass

    def _create_directories(self):
        if not any(frame.filename == __file__ for frame in inspect.getouterframes(inspect.currentframe(), 2)):
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')
        if self._shared_dir:
            if not os.path.exists(self._shared_dir):
                logger.debug(f"Creating shared directory: {self._shared_dir}")
                os.makedirs(self._shared_dir)
        if self._protected_dir:
            if not os.path.exists(self._protected_dir):
                logger.debug(f"Creating protected directory: {self._protected_dir}")
                os.makedirs(self._protected_dir)
        if self._user_dir:
            if self._user_dir and not os.path.exists(self._user_dir):
                logger.debug(f"Creating user directory: {self._user_dir}")
                os.makedirs(self._user_dir)
        if self._base_defaults:
            if not os.path.exists(self._base_defaults):
                logger.debug(f"Creating base defaults directory: {self._base_defaults}")
                os.makedirs(self._base_defaults)
        if self._shared_dir and self._protected_dir:
            if os.path.samefile(self._shared_dir, self._protected_dir):
                raise ValueError("The shared and protected directories cannot be the same.")

    def _enumerate_configs(self):
        if not any(frame.filename == __file__ for frame in inspect.getouterframes(inspect.currentframe(), 2)):
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')

        self._enumerate_directory(self._shared_dir, self.config_shared)
        if self._protected_dir:
            self._enumerate_directory(self._protected_dir, self.config_protected)
        if self._user_dir and self.config_user:
            self._enumerate_directory(self._user_dir, self.config_user)

    def _enumerate_directory(self, directory, config_dict):
        if not any(frame.filename == __file__ for frame in inspect.getouterframes(inspect.currentframe(), 2)):
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')

        for file_name in os.listdir(directory):
            if file_name.endswith(".json"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, "r") as f:
                    try:
                        config = json.load(f)
                        file_key = os.path.splitext(file_name)[0]
                        config_dict[file_key] = config
                    except json.JSONDecodeError:
                        pass

    def get_config(self, section_key=None):
        self._enumerate_configs()
        data = self._get_config_dict(section_key, self.config_shared)
        return data

    def get_config_user(self, section_key=None):
        self._enumerate_configs()
        return self._get_config_dict(section_key, self.config_user)

    def set_config(self, config, section_key=None):
        """
        Set the configuration for a section. If the section does not exist, it will be created.
        :param config:
        :param section_key:
        """
        self._set_config_dict(config, section_key, self.config_shared)

    def get_item(self, key, section_key=None, default=None):
        self._enumerate_configs()
        if not section_key or section_key == "core":
            section_key = "core"
            return self._get_item_from_dict(key, section_key, default, self.config_protected)
        else:
            return self._get_item_from_dict(key, section_key, default, self.config_shared)

    def get_item_user(self, key, section_key=None, default=None):
        self._enumerate_configs()
        return self._get_item_from_dict(key, section_key, default, self.config_user)

    @staticmethod
    def get_locales(name=None, language=None):
        if name is None:
            name = "locales"
        dh = DirectoryHandler()
        protected_dir = dh.protected_path
        locales_file = os.path.join(protected_dir, "locales", f"{name}.json")
        locales = {}
        if os.path.exists(locales_file):
            with open(locales_file, "r") as f:
                locales = json.load(f)
        if language:
            if language in locales:
                return locales[language]
            elif "en" in locales:
                return locales["en"]
            return []
        return locales

    def get_item_protected(self, key, section_key=None, default=None):
        if "extensions" in locals():
            raise ValueError("Protected configuration accessed from unauthorized method.")
        return self._get_item_from_dict(key, section_key, default, self.config_protected)

    def set_item(self, key, value, section_key=None):
        return self._set_item_in_dict(key, value, section_key, False)

    def set_item_protected(self, key, value, section_key=None):
        if "extensions" in locals():
            raise ValueError("Protected configuration accessed from unauthorized method.")
        return self._set_item_in_dict(key, value, section_key, True)

    def set_item_user(self, key, value, section_key=None):
        return self._set_item_in_dict(key, value, section_key, is_user=True)

    def set_default_config(self, config, section_key=None, protected=False):
        if section_key and section_key not in self.config_shared.keys():
            self._set_config_dict(config, section_key, protected)

    def get_all_protected(self) -> Tuple[Dict, Dict, Dict]:
        if "extensions" in locals():
            raise ValueError("Protected configuration accessed from unauthorized method.")
        shared = self.config_shared.copy()
        protected = self.config_protected.copy()

        user = {}
        if self._user_dir:
            user = self.config_user.copy()

        return shared, protected, user

    def get_config_protected(self, section_key=None):
        if "extensions" in locals():
            raise ValueError("Protected configuration accessed from unauthorized method.")
        return self._get_config_dict(section_key, self.config_protected)

    def set_config_protected(self, config, section_key=None):
        if "extensions" in locals():
            raise ValueError("Protected configuration accessed from unauthorized method.")
        self._set_config_dict(config, section_key, True)

    def set_config_user(self, config, section_key=None):
        """
                Set the configuration for a section. If the section does not exist, it will be created.
                :param config:
                :param section_key:
                """
        self._set_config_dict(config, section_key, is_user=True)

    def _get_config_dict(self, section_key, config_dict):
        if not any(frame.filename == __file__ for frame in inspect.getouterframes(inspect.currentframe(), 2)):
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')
        if section_key is None:
            return config_dict.get("core")

        else:
            section_config = config_dict.get(section_key)
            if section_config is not None:
                return section_config
        return None

    def _get_item_from_dict(self, key, section_key, default, config_dict):
        if not any(frame.filename == __file__ for frame in inspect.getouterframes(inspect.currentframe(), 2)):
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')

        self._enumerate_configs()
        config = self._get_config_dict(section_key, config_dict)
        if config is not None and key in config:
            return config[key]
        else:
            return default

    def _set_item_in_dict(self, key, value, section_key=None, is_protected=False, is_user=False):
        self._enumerate_configs()
        if not any(frame.filename == __file__ for frame in inspect.getouterframes(inspect.currentframe(), 2)):
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')

        if is_user:
            if self._user_dir is not None:
                target_dict = self.config_user
            else:
                raise ValueError(
                    "User directory not set, be sure to instantiate this class with a user_name parameter.")
        elif is_protected:
            target_dict = self.config_protected
        else:
            target_dict = self.config_shared

        if section_key is None:
            section_key = "core"
        if section_key not in target_dict:
            target_dict[section_key] = {}
        target_dict[section_key][key] = value
        self._save_config_file(section_key, target_dict[section_key], is_protected, is_user)
        return True

    def _set_config_dict(self, config, section_key, is_protected=False, is_user=False):
        self._enumerate_configs()
        if not any(frame.filename == __file__ for frame in inspect.getouterframes(inspect.currentframe(), 2)):
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')
        if is_user:
            if self._user_dir is not None:
                target_dict = self.config_user
            else:
                raise ValueError(
                    "User directory not set, be sure to instantiate this class with a user_name parameter.")
        elif is_protected:
            target_dict = self.config_protected
        else:
            target_dict = self.config_shared
        if section_key is None:
            section_key = "core"
        target_dict["core"] = config
        self._save_config_file(section_key, config, is_protected, is_user)

    def _save_config_file(self, section_key, data, is_protected=False, is_user=False):
        caller_file = inspect.getouterframes(inspect.currentframe())[1].filename
        if caller_file != __file__:
            raise NotImplementedError('This method can only be called by the ConfigHandler instance.')
        if is_user:
            if self._user_dir is not None:
                target_dir = self._user_dir
            else:
                raise ValueError(
                    "User directory not set, be sure to instantiate this class with a user_name parameter.")
        elif is_protected:
            target_dir = self._protected_dir
        else:
            target_dir = self._shared_dir
        target_file = os.path.join(target_dir, f"{section_key}.json")
        with open(target_file, "w") as cfg_out:
            json.dump(data, cfg_out, indent=4)
