import logging
import os


class DirectoryHandler:
    _instance = None
    _instances = {}
    _user_name = None
    app_path = None
    _launch_settings = {}
    shared_path = None
    protected_path = None
    protected_dirs = ["cache", "config", "users"]
    shared_dirs = ["models", "extensions", "outputs", "input", "css"]
    combine_dirs = ["models", "extensions", "input"]
    logger = None

    def __new__(cls, app_path=None, launch_settings=None, user_name=None):
        if not cls._instance and launch_settings and app_path:
            cls._instance = super(DirectoryHandler, cls).__new__(cls)
            cls._instance.logger = logging.getLogger(f"{__name__}-shared")
            cls._instance._launch_settings = launch_settings
            cls._instance._user_name = user_name
            cls._instance.app_path = app_path
            cls._instance.initialize_directories()

        if cls._instance and user_name:
            if user_name in cls._instances:
                return cls._instances[user_name]
            else:
                user_instance = super(DirectoryHandler, cls).__new__(cls)
                user_instance.logger = logging.getLogger(f"{__name__}-{user_name}")
                user_instance._user_name = user_name
                user_instance._launch_settings = cls._instance._launch_settings
                user_instance.app_path = cls._instance.app_path
                user_instance.initialize_directories()
                cls._instances[user_name] = user_instance
                return user_instance
        else:
            return cls._instance
        
    def initialize_directories(self):
        # Check/set shared directories based on launch settings
        self.shared_path = self._launch_settings.get("shared_dir", "")
        if self.shared_path == "":
            self.shared_path = os.path.join(self.app_path, "data_shared")
        if not os.path.exists(self.shared_path):
            os.mkdir(self.shared_path)

        self.protected_path = self._launch_settings.get("protected_dir", "")
        if self.protected_path == "":
            self.protected_path = os.path.join(self.app_path, "data_protected")
        if not os.path.exists(self.protected_path):
            os.mkdir(self.protected_path)

        for sub in self.protected_dirs:
            os.makedirs(os.path.join(self.protected_path, sub), exist_ok=True)

        for sub in self.shared_dirs:
            os.makedirs(os.path.join(self.shared_path, sub), exist_ok=True)

        if self._user_name:
            user_dir = os.path.join(self.protected_path, "users", self._user_name)
            os.makedirs(user_dir, exist_ok=True)
            for sub in self.shared_dirs:
                os.makedirs(os.path.join(user_dir, sub), exist_ok=True)

    def get_directory(self, directory: str):
        output = []
        if self._user_name:
            user_dir = os.path.join(self.protected_path, "users", self._user_name)
            if directory == self._user_name:
                return [user_dir]
            if directory in self.combine_dirs:
                output = [os.path.join(user_dir, directory), os.path.join(self.shared_path, directory)]
            elif directory in self.shared_dirs:
                output = [os.path.join(user_dir, directory)]
        else:
            if directory in self.shared_dirs:
                output = [os.path.join(self.shared_path, directory)]
            elif directory in self.protected_dirs:
                output = [os.path.join(self.protected_path, directory)]

        return output

    def get_user_directory(self, directory: str):
        output = None
        if self._user_name:
            user_dir = os.path.join(self.protected_path, "users", self._user_name)
            if directory == self._user_name:
                return user_dir
            full_dir = os.path.abspath(os.path.join(user_dir, directory))
            if user_dir in full_dir:
                output = os.path.join(user_dir, directory)
        else:
            self.logger.warning("No user name set, cannot get user directory.")
        return output

    def get_shared_directory(self, directory: str):
        output = None
        full_path = os.path.join(self.shared_path, directory)
        if self.shared_path in os.path.abspath(full_path):
            output = full_path
        else:
            self.logger.warning(f"Directory '{directory}' not found in shared dir: {self.shared_path}")
        return output

    def get_protected_directory(self, directory: str):
        output = None
        if directory in self.protected_dirs:
            output = os.path.join(self.protected_path, directory)
        else:
            self.logger.warning(f"Directory '{directory}' not found in protected dir: {self.protected_path}")
        return output



