import asyncio
import logging
import traceback
from typing import Dict, List

import jwt
from fastapi import WebSocket, HTTPException
from jwt import PyJWTError
from starlette.status import HTTP_403_FORBIDDEN
from starlette.websockets import WebSocketDisconnect

from app.auth_helpers import get_user, TokenData, SECRET_KEY, ALGORITHM
from app.oauth2_password_bearer import OAuth2PasswordBearerCookie
from core.handlers.queues import QueueHandler

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, user_auth=False):
        self.active_connections: List[WebSocket] = []
        self.sessions = {}
        self.user_auth = user_auth

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        logger.debug("Accepted.")
        self.active_connections.append(websocket)

    async def send_personal_message(self, message: Dict):
        websocket = message.pop("socket")
        await websocket.send_json(message)

    async def broadcast(self, message: Dict):
        message_targets = self.active_connections
        if self.user_auth:
            user = message.get("user", None)
            if user is None:
                logger.debug("NO USER")
            else:
                if user in self.sessions:
                    logger.debug(f"Setting socket targets to user: {user}")
                    message_targets = self.sessions[user]

        disconnected = []
        for connection in message_targets:
            try:
                await connection.send_json(message)
            except Exception as e:
                # client is not connected, disconnect them
                logger.warning(f"Error broadcasting message to client {connection}: {e}")
                disconnected.append(connection)

        # disconnect inactive connections
        for connection in disconnected:
            self.disconnect(connection)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for user, sessions in self.sessions.items():
            if websocket in sessions:
                logger.debug(f"Removing user session: {user}")
                sessions.remove(websocket)

    async def register_session(self, websocket: WebSocket, user: str):

        if user not in self.sessions:
            self.sessions[user] = []
        logger.debug(f"Registering new session for user: {user}")
        self.sessions[user].append(websocket)
        logger.debug("Registered.")

    async def unregister_session(self, websocket: WebSocket, user: str):

        if user in self.sessions:
            session_clients = self.sessions[user]
            if websocket in session_clients:
                session_clients.remove(websocket)
            if len(session_clients) == 0:
                del self.sessions[user]


class SocketHandler:
    _instance = None
    manager = None
    queue = None
    _user_auth = False
    queue_handler = None
    oauth2_scheme = OAuth2PasswordBearerCookie(token_url="/token")

    def __new__(cls, app=None, user_auth=False):
        if cls._instance is None and app is not None:
            cls._instance = super(SocketHandler, cls).__new__(cls)
            cls._instance._init(app)
            cls._instance._user_auth = user_auth
            cls._instance.manager = ConnectionManager(user_auth)
            cls._instance.queue = app.message_queue

            @app.on_event("startup")
            async def start_db():
                asyncio.create_task(cls._instance.consume_queue())
        return cls._instance

    def __init__(self, app=None, user_auth=False):
        if self.queue_handler is None:
            self.queue_handler = QueueHandler()

    async def consume_queue(self):
        while True:
            message = await self.queue.get()
            logger.debug("Pull queue...")
            await self.manager.broadcast(message)
            self.queue.task_done()

    async def handle_socket_callback(self, msg):
        await_response = msg["await"]
        websocket = msg["socket"]
        name = msg["name"]
        response = msg
        user = msg.get("user", None)
        try:
            if await_response:
                if user and name in self.socket_callbacks.get(user, {}):
                    logger.debug(f"Awaiting user callback: {user}")
                    data = await self.socket_callbacks[user][name](msg)
                else:
                    logger.debug("Awaiting shared callback")
                    data = await self.socket_callbacks[name](msg)
                response["data"] = data
            else:
                if user and name in self.socket_callbacks.get(user, {}):
                    self.queue_handler.put_job(self.socket_callbacks[user][name](msg), self.callback_response, self, msg)
                else:
                    self.queue_handler.put_job(self.socket_callbacks[name](msg), self.callback_response, self, msg)
                response["data"] = "Message added to queue."
        except Exception as e:
            response["data"] = f"Exception with socket callback: {e}"
            traceback.print_exc()

        # logger.debug(f"Sending response: {response}")
        await self.manager.send_personal_message(response)

    async def callback_response(self, response):
        websocket = response.pop("socket")
        await self.manager.send_personal_message(response)

    def _init(self, app=None):
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            username = None
            if self._user_auth:
                credentials_exception = HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
                )
                try:
                    socket_cookie = websocket.cookies
                    logger.debug(f"Got cookie: {socket_cookie}")
                    csrf_token = socket_cookie.get("Authorization", None)
                    username = None
                    if csrf_token:
                        logger.debug("Got token!")
                        csrf_token = csrf_token.split(" ")[1]
                        payload = jwt.decode(csrf_token, SECRET_KEY, algorithms=[ALGORITHM])
                        logger.debug(f"Decoded payload: {payload}")
                        username: str = payload.get("sub")
                    if username is None:
                        raise credentials_exception
                    token_data = TokenData(username=username)
                except PyJWTError:
                    raise credentials_exception
                user = get_user(username=token_data.username)
                if user is None:
                    raise credentials_exception

                await self.manager.register_session(websocket, username)
                logger.debug("Really registered, connecting")

            await self.manager.connect(websocket)
            logger.debug(f"Socket connected: {username}")
            while True:
                try:
                    data = await websocket.receive_json()
                    response = {"name": "Received"}
                    if "id" in data:
                        response["id"] = data["id"]
                    if data is not None:
                        try:
                            message = data
                            if "name" in message and "data" in message:
                                logger.debug(f"Message is valid: {message}")
                                name = message.pop("name")
                                if name == "logout":
                                    await websocket.send_json(message)
                                    self.manager.disconnect(websocket)
                                    break
                                data = message["data"]
                                await_msg = message.pop("await")
                                message_id = message.pop("id")
                                if name in self.socket_callbacks:
                                    msg = {
                                        "socket": websocket,
                                        "id": message_id,
                                        "data": data,
                                        "await": await_msg,
                                        "name": name
                                    }
                                    if username is not None:
                                        logger.debug(f"Definitely setting username: {username}")
                                        msg["user"] = username

                                    # asyncio.create_task(self.handle_socket_callback(name, msg, websocket))
                                    await self.handle_socket_callback(msg)
                                else:
                                    logger.debug(f"Undefined message: {message}")
                            else:
                                logger.debug(f"Invalid message: {message}")
                        except Exception as e:
                            logger.warning(f"Exception parsing socket message: {e}")
                            traceback.print_exc()
                except WebSocketDisconnect as d:
                    logger.debug("Socket disconnected.")
                    if websocket in self.clients:
                        self.clients.remove(websocket)
                    break
                except Exception as f:
                    logger.warning(f"SOCKET EXCEPTION: {f}")
                    traceback.print_exc()
                    if websocket in self.clients:
                        self.clients.remove(websocket)
                    break
            self.manager.disconnect(websocket)

        self.clients = []
        self.socket_callbacks = {}

    def register(self, name: str, callback, user=None):
        logger.debug(f"Socket callback registered: {name} {user}")
        if user:
            if user not in self.socket_callbacks:
                self.socket_callbacks[user] = {}
            self.socket_callbacks[user][name] = callback
        else:
            self.socket_callbacks[name] = callback

    def deregister(self, name, user=None):
        if user:
            if user in self.socket_callbacks:
                if name in self.socket_callbacks[user]:
                    del self.socket_callbacks[user][name]
                if  not len(self.socket_callbacks[user]):
                    del self.socket_callbacks[user]
        else:
            if name in self.socket_callbacks:
                del self.socket_callbacks[name]
