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


async def get_current_active_user(current_user: User = Depends(get_current_user)):
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

        # Add an endpoint to fastAPI for updating the user data
        @app.post("/users/user")
        async def update_user(user: User, current_user: User = Depends(get_current_user)):
            if current_user.disabled:
                raise HTTPException(status_code=403, detail="Not enough privileges")
            user_data = user.dict()
            existing_users = self.config_handler.get_config_protected("users")
            existing_user = None
            message = ""
            updated_users = []
            for ex_user in existing_users:
                if ex_user["name"] == user_data["name"]:
                    existing_user = ex_user
                    break
                updated_users.append(ex_user)

            if not current_user.admin:
                # Don't allow non-admins to create users
                if not existing_user:
                    raise HTTPException(status_code=403, detail="Not enough privileges")
                # Don't allow non-admins to change the data of other users
                if existing_user["name"] != current_user.name:
                    raise HTTPException(status_code=403, detail="Not enough privileges")
                # Don't allow non-admins to upgrade themselves to admin
                if user.admin:
                    raise HTTPException(status_code=403, detail="Not enough privileges")

            if "password" in user_data:
                password = user_data.pop("password")
                if not password.startswith("$2") and not password.startswith("$3"):
                    # if password is not already hashed, hash it using bcrypt
                    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    user_data["password"] = hashed_password.decode()
                    message = f"User {user_data['name']} created"

            if existing_user:
                for key in existing_user:
                    existing_user[key] = user_data[key]
                user_data = existing_user
                message = f"User {existing_user['name']} updated"

            updated_users.append(user_data)
            self.config_handler.set_item_protected("users", updated_users)
            return JSONResponse(status_code=200, content={"message": message, "user": user_data})

        self.register_users()

    def register_users(self):
        users = self.config_handler.get_config_protected("users")
        from core.handlers.status import StatusHandler
        from core.handlers.file import FileHandler
        from core.handlers.models import ModelHandler
        from core.handlers.images import ImageHandler

        for user in users:
            logger.info(f"Registering handlers for user: {user}")
            DirectoryHandler(user_name=user)
            StatusHandler(user_name=user)
            FileHandler(user_name=user)
            ModelHandler(user_name=user)
            ImageHandler(user_name=user)

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    async def update_password(self, req):
        user = req.get("user", None)
        ch = ConfigHandler()
        user_data = ch.get_item_protected(user, "users", None)
        is_admin = False
        if user:
            if user_data:
                is_admin = user_data.get("admin", False)

            data = req["data"] if "data" in req else {}

            update_user = data.get("user", None)
            password = data.get("password", None)
            if is_admin or update_user == user:
                encrypted_pass = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                user_data["pass"] = encrypted_pass.decode()
                ch.set_item_protected(user, user_data, "users")
                return {"status": "Password updated successfully."}
            return {"status": "Unable to update password."}

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
