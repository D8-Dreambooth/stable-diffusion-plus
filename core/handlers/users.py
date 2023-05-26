import logging
import os
from datetime import timedelta, datetime
from typing import Optional, List, Dict

import bcrypt
import jwt
from fastapi import Depends, HTTPException, FastAPI
from jwt import PyJWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN

from app.auth.basic_auth import BasicAuth
from app.auth.oauth2_password_bearer import OAuth2PasswordBearerCookie
from core.handlers.config import ConfigHandler
from core.handlers.directories import DirectoryHandler

logger = logging.getLogger(__name__)


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    name: str = ""
    disabled: bool = False
    admin: bool = False
    password: Optional[str] = None


class TokenData(BaseModel):
    name: str = None


def get_user(user: str) -> Optional[Dict]:
    config_handler = ConfigHandler()
    user_dict = config_handler.get_item_protected(user, "users", None)
    if user_dict is None:
        return None
    # Enumerate key/values in user_dict and set attributes of a new User object
    user = User()
    for key, value in user_dict.items():
        try:
            if key == "pass":
                key = "password"
            setattr(user, key, value)
        except:
            logger.error(f"Failed to set attribute: {key}")
    return user.__dict__


oauth2_scheme = OAuth2PasswordBearerCookie(token_url="/token")


async def get_current_socket_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )
    try:
        uh = UserHandler()
        payload = jwt.decode(token, uh.secret, algorithms=[uh.algorithm])
        user: str = payload.get("sub")
        if user is None:
            raise credentials_exception
        token_data = TokenData(name=user)
    except PyJWTError:
        raise credentials_exception
    user = get_user(user=token_data.name)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    config_handler = ConfigHandler()
    uh = UserHandler()
    user_auth = config_handler.get_item_protected("user_auth", "core", False)
    if not user_auth:
        return None
    credentials_exception = HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, uh.secret, algorithms=[uh.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(name=username)
    except PyJWTError:
        raise credentials_exception
    user = get_user(user=token_data.name)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: Dict = Depends(get_current_user)):
    config_handler = ConfigHandler()
    user_auth = config_handler.get_item_protected("user_auth", "core", False)
    if not user_auth:
        return None
    return current_user


class UserHandler:
    _instance = None
    user_dir = ""
    user = {}
    basic_auth = BasicAuth(auto_error=False)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearerCookie(token_url="/token")
    secret = None
    algorithm = "HS256"
    access_token_life = 30
    config_handler = None
    user_auth = False
    users: List[User] = []

    def __new__(cls, config_handler: ConfigHandler = None):
        if cls._instance is None and config_handler is not None:
            cls._instance = super(UserHandler, cls).__new__(cls)
            cls._instance.config_handler = config_handler
            dir_handler = DirectoryHandler()
            secret_file = os.path.join(dir_handler.protected_path, "secret.txt")
            # If no secret file exists, generate one
            if not os.path.exists(secret_file):
                with open(secret_file, "w") as f:
                    logger.info("Generating secret file")
                    f.write(os.urandom(32).hex())

            with open(secret_file, "r") as f:
                cls._instance.secret = f.read()

            cls._instance.user_auth = config_handler.get_item("user_auth", "core", False)

        return cls._instance

    def initialize(self, app: FastAPI, handler):
        handler.register("change_password", self.update_password)
        handler.register("update_user", self._socket_update_user)

        # Add an endpoint to fastAPI for updating the user data
        @app.post("/users/user")
        async def update_user(user: User, current_user: Dict = Depends(get_current_user)):
            if current_user["disabled"]:
                raise HTTPException(status_code=403, detail="Not enough privileges")
            user_data = user.dict()
            response = self.update_user_config(user_data, current_user)
            if response["error"]:
                raise HTTPException(status_code=403, detail=response["error"])
            return JSONResponse(status_code=200, content={"message": response["message"], "user": response["user"]})

        self.register_users()

    async def _socket_update_user(self, request):
        user = request["data"]
        current_user = request["user"]
        current_user = get_user(current_user)
        response = self.update_user_config(user, current_user)
        if response["error"]:
            return {"message": response["error"]}
        return {"message": response["message"], "user": response["user"]}

    def update_user_config(self, new_user_data: Dict, request_user: Dict):
        if "name" not in new_user_data:
            return {"message": "Unable to update user", "error": "No user name specified", "user": new_user_data}
        user_name = new_user_data["name"]
        current_user_data = self.config_handler.get_item_protected(user_name, "users", None)
        error = None
        if not request_user["admin"]:
            if "admin" in new_user_data:
                del new_user_data["admin"]
            if "disabled" in new_user_data:
                del new_user_data["disabled"]
            # Don't allow non-admins to create users
            if not current_user_data or current_user_data["name"] != request_user["name"] or request_user["admin"]:
                error = "Not enough privileges"
            if error:
                return {"message": "Unable to update user", "error": error, "user": new_user_data}

        if "pass" in new_user_data or "password" in new_user_data:
            password = new_user_data.pop("pass") if "pass" in new_user_data else new_user_data.pop("password")
            logger.debug(f"Popped pass: {password}")

            if not password.startswith("$2") and not password.startswith("$3"):
                # if password is not already hashed, hash it using bcrypt
                hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                new_user_data["pass"] = hashed_password.decode()
                logger.debug(f"Hashed pass: {new_user_data['pass']}")
                message = f"User {new_user_data['name']} created"
        logger.debug(f"Updating user: {current_user_data}")
        if current_user_data:
            for key in current_user_data:
                if key == "password":
                    key = "pass"
                if key in new_user_data:
                    current_user_data[key] = new_user_data[key]
            new_user_data = current_user_data
            message = f"User {current_user_data['name']} updated"
        else:
            self.register_user(new_user_data)
        self.config_handler.set_item_protected(user_name, new_user_data, "users")

        if "pass" in new_user_data:
            del new_user_data["pass"]
        return {"message": "User updated successfully", "error": None, "user": new_user_data}

    def register_users(self):
        users = self.config_handler.get_config_protected("users")
        from core.handlers.status import StatusHandler
        from core.handlers.file import FileHandler
        from core.handlers.models import ModelHandler
        from core.handlers.images import ImageHandler
        self.users = []
        for user_name, user in users.items():
            if not user["disabled"]:
                logger.info(f"Registering handlers for user_name: {user_name}")
                DirectoryHandler(user_name=user_name)
                StatusHandler(user_name=user_name)
                FileHandler(user_name=user_name)
                ModelHandler(user_name=user_name)
                ImageHandler(user_name=user_name)
                self.users.append(User(**user))

    def register_user(self, user):
        # If the user value is a dict
        if isinstance(user, dict):
            user = User(**user)
        if not user.disabled:
            self.users.append(user)
            from core.handlers.status import StatusHandler
            from core.handlers.file import FileHandler
            from core.handlers.models import ModelHandler
            from core.handlers.images import ImageHandler
            logger.info(f"Registering handlers for user.name: {user.name}")
            DirectoryHandler(user_name=user.name)
            StatusHandler(user_name=user.name)
            FileHandler(user_name=user.name)
            ModelHandler(user_name=user.name)
            ImageHandler(user_name=user.name)

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    async def update_password(self, req):
        request_user = req.get("user", None)
        # Find user data in self.users
        request_user_data = None
        update_user_data = None
        data = req["data"] if "data" in req else {}
        update_user = data.get("user", None)
        new_password = data.get("password", None)

        for user in self.users:
            if user.name == request_user:
                request_user_data = user
            if user.name == update_user:
                update_user_data = user

        is_admin = False if not request_user_data else request_user_data.admin
        if not is_admin or request_user != update_user:
            return {"status": "Unable to update password."}

        encrypted_pass = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        update_user_data.password = encrypted_pass.decode()

        self.users = []
        for u in self.users:
            if u.name == update_user_data.name:
                u = update_user_data
            self.users.append(u)

        return {"status": "Password updated successfully."}

    def authenticate_user(self, user: str, password: str):
        user = get_user(user)
        if user is None:
            return False
        if password is None:
            return False
        user_hash = user["password"]
        if not user_hash:
            return False
        if not self.verify_password(password, user_hash):
            return False
        return True

    def create_access_token(self, *, data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=36)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret, algorithm=self.algorithm)
        return encoded_jwt

    async def get_current_active_user(self, user) -> Optional[Dict]:
        config_handler = ConfigHandler()
        user_auth = config_handler.get_item_protected("user_auth", "core", False)
        if not user_auth:
            return None
        active_user = await get_current_user(user)
        return active_user
