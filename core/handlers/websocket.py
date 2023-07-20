import asyncio
import logging
import traceback
from typing import Dict, List

import jwt
from fastapi import WebSocket, HTTPException
from jwt import PyJWTError
from starlette.status import HTTP_403_FORBIDDEN
from starlette.websockets import WebSocketDisconnect

from app.auth.oauth2_password_bearer import OAuth2PasswordBearerCookie
from core.handlers.queues import QueueHandler
from core.handlers.users import UserHandler, TokenData, get_user

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, user_auth=False):
        self.active_connections: List[WebSocket] = []
        self.sessions = {}
        self.user_auth = user_auth

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def send_personal_message(self, message: Dict):
        try:
            websocket = message.pop("socket")
            # Make sure the websocket isn't closed already
            await websocket.send_json(message)
        except:
            logger.debug(f"Error sending personal message: {traceback.format_exc()}")
            pass

    async def broadcast(self, message: Dict):
        message["broadcast"] = True
        message_targets = self.active_connections
        if self.user_auth:
            user = message.get("user", None)
            if user:
                if user in self.sessions:
                    message_targets = self.sessions[user]
            else:
                logger.debug("Message has no user: " + str(message))
                return

        disconnected = []
        if "reload" in message["name"]:
            logger.debug(f"Broadcasting: {message}")
        for connection in message_targets:
            try:
                await asyncio.wait_for(connection.send_json(message), timeout=0.01)  # timeout of 10 milliseconds
            except asyncio.TimeoutError:
                logger.warning(f"Timeout error when sending message to client {connection}")
                disconnected.append(connection)
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
                sessions.remove(websocket)

    async def register_session(self, websocket: WebSocket, user: str):

        if user not in self.sessions:
            self.sessions[user] = []
        self.sessions[user].append(websocket)

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
    user_handler = None
    queue_handler = None
    oauth2_scheme = OAuth2PasswordBearerCookie(token_url="/token")

    def __new__(cls, app=None, user_handler: UserHandler = None):
        if cls._instance is None and app is not None:
            cls._instance = super(SocketHandler, cls).__new__(cls)
            cls._instance._init(app)
            cls._instance.user_handler = user_handler
            cls._instance._user_auth = user_handler.user_auth
            cls._instance.manager = ConnectionManager(user_handler.user_auth)
            cls._instance.queue = app.message_queue

            @app.on_event("startup")
            async def start_db():
                asyncio.create_task(cls._instance.consume_queue())
        return cls._instance

    def __init__(self, app=None, user_handler: UserHandler = None):
        if self.queue_handler is None:
            self.queue_handler = QueueHandler()

    async def consume_queue(self):
        while True:
            message = await self.queue.get()
            await self.manager.broadcast(message)
            self.queue.task_done()

    async def handle_socket_callback(self, msg):
        await_response = msg["await"]
        name = msg["name"]
        response = msg.copy()
        user = msg.get("user", None)
        if name == "ping":
            response["data"] = {"message": "pong"}
            await self.manager.send_personal_message(response)
            return
        try:
            if await_response:
                if user and name in self.socket_callbacks.get(user, {}):
                    data = await self.socket_callbacks[user][name](msg)
                else:
                    data = await self.socket_callbacks[name](msg)
                response["data"] = data
            else:
                if user and name in self.socket_callbacks.get(user, {}):
                    self.queue_handler.put_job(self.socket_callbacks[user][name], self.callback_response, msg)
                else:
                    if name in self.socket_callbacks:
                        self.queue_handler.put_job(self.socket_callbacks[name], self.callback_response, msg)
                    else:
                        logger.warning(f"No registered job for callback: {name}")
                response["data"] = {"message": "Message added to queue."}
        except Exception as e:
            response["data"] = {"message": f"Exception with socket callback: {e}"}
            logger.warning(f"Exception with socket callback ({user})({name}): {e}")
            traceback.print_exc()

        await self.manager.send_personal_message(response)

    async def callback_response(self, response):
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
                    csrf_token = socket_cookie.get("Authorization", None)
                    username = None
                    if csrf_token:
                        csrf_token = csrf_token.split(" ")[1]
                        payload = jwt.decode(csrf_token, self.user_handler.secret,
                                             algorithms=[self.user_handler.algorithm])
                        username: str = payload.get("sub")
                    if username is None:
                        raise credentials_exception
                    token_data = TokenData(name=username)
                except PyJWTError:
                    await websocket.close(code=1000, reason="Could not validate credentials")
                    return
                user = get_user(user=token_data.name)
                if user is None:
                    await websocket.close(code=1000, reason="Could not validate credentials")
                    return

                await self.manager.register_session(websocket, username)

            await self.manager.connect(websocket)
            while True:
                await asyncio.sleep(0)
                try:
                    message = await websocket.receive_json()
                    if message is None:
                        continue
                    if "name" not in message or "data" not in message:
                        logger.warning(f"Invalid message: {message}")
                        continue
                    try:
                        name = message.pop("name")
                        if name == "logout":
                            await websocket.send_json(message)
                            self.manager.disconnect(websocket)
                            break
                        if name == "ping":
                            message["name"] = name
                            await websocket.send_json(message)
                            continue
                        if name not in self.socket_callbacks:
                            logger.warning(f"Undefined message: {message}")
                            continue
                        data = message.pop("data")
                        await_msg = message.pop("await")
                        message_id = message.pop("id")
                        target = None

                        if "target" in message:
                            target = message.pop("target")

                        msg = {
                            "socket": websocket,
                            "id": message_id,
                            "data": data,
                            "await": await_msg,
                            "name": name,
                            "target": target
                        }
                        if username is not None:
                            msg["user"] = username
                        asyncio.create_task(self.handle_socket_callback(msg))
                    except Exception as e:
                        logger.warning(f"Exception parsing socket message: {e}")
                        traceback.print_exc()
                except WebSocketDisconnect as d:
                    logger.debug(f"SOCKET DISCONNECT: {d}")
                    self.manager.disconnect(websocket)
                    break
                except Exception as f:
                    logger.warning(f"SOCKET EXCEPTION: {f}")
                    traceback.print_exc()
                    self.manager.disconnect(websocket)
                    break
            logger.debug(f"SOCKET DISCONNECT: {websocket}")
            self.manager.disconnect(websocket)

        self.clients = []
        self.socket_callbacks = {}

    def register(self, name: str, callback, user=None):
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
                if not len(self.socket_callbacks[user]):
                    del self.socket_callbacks[user]
        else:
            if name in self.socket_callbacks:
                del self.socket_callbacks[name]
