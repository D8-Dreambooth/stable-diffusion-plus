import asyncio
import json
import logging
import traceback
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: Dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # client is not connected, disconnect them
                print(f"Error broadcasting message to client {connection}: {e}")
                disconnected.append(connection)

        # disconnect inactive connections
        for connection in disconnected:
            self.disconnect(connection)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"Disconnected client {websocket}")
        else:
            print(f"Client {websocket} was already disconnected")


class SocketHandler:
    _instance = None
    manager = None

    def __new__(cls, app=None):
        if cls._instance is None and app is not None:
            cls._instance = super(SocketHandler, cls).__new__(cls)
            cls._instance._init(app)
            cls._instance.manager = ConnectionManager()
        return cls._instance

    async def handle_socket_callback(self, name, msg, websocket):
        try:
            response = await self.socket_callbacks[name](msg)
        except Exception as e:
            response = {"data": f"Exception with socket callback: {e}"}
            traceback.print_exc()
        response["id"] = msg["id"]
        response["name"] = name
        logger.debug(f"Sending response: {response}")
        await self.manager.send_personal_message(response, websocket)

    def _init(self, app=None):
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.manager.connect(websocket)
            logger.debug(f"Socket added: {websocket}")
            while True:
                try:
                    data = await websocket.receive_json()
                    response = {"name": "Received"}
                    if "id" in data:
                        response["id"] = data["id"]
                    if data is not None:
                        try:
                            logger.debug(f"Raw message: {data}")
                            message = data
                            if "name" in message and "data" in message:
                                logger.debug(f"Message is valid: {message}")
                                name = message["name"]
                                data = message["data"]
                                message_id = message["id"]
                                await_response = message["await"]
                                if not await_response:
                                    await self.manager.send_personal_message(response, websocket)
                                if name in self.socket_callbacks:
                                    msg = {
                                        "socket": websocket,
                                        "id": message_id,
                                        "data": data
                                    }
                                    asyncio.create_task(self.handle_socket_callback(name, msg, websocket))
                                else:
                                    logger.debug(f"Undefined message: {message}")
                            else:
                                logger.debug(f"Invalid message: {message}")
                        except Exception as e:
                            logger.debug(f"Exception parsing socket message: {e}")
                            traceback.print_exc()
                    else:
                        logger.debug("NO DATA!")
                except WebSocketDisconnect as d:
                    logger.debug("Socket disconnected.")
                    if websocket in self.clients:
                        self.clients.remove(websocket)
                    break
                except Exception as f:
                    logger.debug(f"SOCKET EXCEPTION: {f}")
                    traceback.print_exc()
                    if websocket in self.clients:
                        self.clients.remove(websocket)
                    break
            self.manager.disconnect(websocket)
        self.clients = []
        self.socket_callbacks = {}

    async def broadcast_async(self, message: Dict):
        logger.debug("Broadcasting...")
        await self.manager.broadcast(message)
        logger.debug("Broadcasted, for real...")

    def broadcast(self, message: Dict):
        logger.debug("Broadcast fired")
        loop = asyncio.get_event_loop()
        logger.debug("Got loop")
        if loop.is_running():
            logger.debug("Loop running, creating task")
            asyncio.ensure_future(self.manager.broadcast(message))
            # asyncio.create_task(self.manager.broadcast(message))
            logger.debug("Task created")
        else:
            logger.debug("Creating loop?")
            loop.run_until_complete(self.broadcast_async(message))
            logger.debug("Loop created")

    def register(self, name: str, callback):
        logger.debug(f"Socket callback registered: {name}")
        self.socket_callbacks[name] = callback

    def deregister(self, name):
        if name in self.socket_callbacks:
            del self.socket_callbacks[name]

