from datetime import timedelta, datetime
from typing import Dict, Union

import jwt
from fastapi import Depends, HTTPException
from jwt import PyJWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette.status import HTTP_403_FORBIDDEN

from app.basic_auth import BasicAuth
from app.oauth2_password_bearer import OAuth2PasswordBearerCookie
from core.handlers.config import ConfigHandler

basic_auth = BasicAuth(auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearerCookie(token_url="/token")
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    email: str = None
    full_name: str = None
    disabled: bool = None


class TokenData(BaseModel):
    username: str = None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(username: str) -> Union[Dict, None]:
    config_handler = ConfigHandler()
    return config_handler.get_item_protected(username, "users", None)


def authenticate_user(username: str, password: str):
    user = get_user(username)
    user_hash = user.get("pass", None)
    if not user_hash:
        return False
    if not verify_password(password, user_hash):
        return False
    return True


def create_access_token(*, data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_socket_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except PyJWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    config_handler = ConfigHandler()
    user_auth = config_handler.get_item_protected("user_auth", "core", False)
    if not user_auth:
        return None
    credentials_exception = HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except PyJWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    config_handler = ConfigHandler()
    user_auth = config_handler.get_item_protected("user_auth", "core", False)
    if not user_auth:
        return None
    return current_user


async def get_current_active_socket_user(current_user: User = Depends(get_current_socket_user)):
    return current_user
