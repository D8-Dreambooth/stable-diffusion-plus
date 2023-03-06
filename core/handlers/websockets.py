import asyncio
import json
import logging
import traceback
from typing import Dict

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class SocketHandler:
    _instance = None

    def __new__(cls, app=None):
        if cls._instance is None and app is not None:
            cls._instance = super(SocketHandler, cls).__new__(cls)
            cls._instance._init(app)
        return cls._instance

    async def handle_socket_callback(self, name, msg, websocket):
        response = await self.socket_callbacks[name](msg)
        response["id"] = msg["id"]
        response["name"] = name
        logger.debug(f"Sending response: {response}")
        await websocket.send_json(response)

    def _init(self, app=None):

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            self.clients.append(websocket)
            logger.debug(f"Socket added: {websocket}")
            await websocket.accept()
            while True:
                try:
                    data = await websocket.receive_text()
                    if data is not None:
                        try:
                            logger.debug(f"Raw message: {data}")
                            message = json.loads(data, object_hook=dict)
                            if "name" in message and "data" in message:
                                logger.debug(f"Message is valid: {message}")
                                name = message["name"]
                                data = message["data"]
                                message_id = message["id"]
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
                except Exception as f:
                    logger.debug(f"SOCKET EXCEPTION: {f}")
                    traceback.print_exc()
                    if websocket in self.clients:
                        self.clients.remove(websocket)
                    break

        self.clients = []
        self.socket_callbacks = {}

    def broadcast(self, message: Dict):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.broadcast_async(message))
        else:
            loop.run_until_complete(self.broadcast_async(message))

    async def broadcast_async(self, message: Dict):
        logger.debug("Broadcasting...")
        tasks = [client.send_text(json.dumps(message)) for client in self.clients]
        await asyncio.gather(*tasks)

    def register(self, name: str, callback):
        logger.debug(f"Socket callback registered: {name}")
        self.socket_callbacks[name] = callback

    def deregister(self, name):
        if name in self.socket_callbacks:
            del self.socket_callbacks[name]
