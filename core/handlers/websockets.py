import json
import traceback

from starlette.websockets import WebSocket


class SocketHandler:
    _instance = None

    def __new__(cls, app=None):
        if cls._instance is None and app is not None:
            cls._instance = super(SocketHandler, cls).__new__(cls)
            cls._instance._init(app)
        return cls._instance

    def _init(self, app=None):
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            self.clients.append(websocket)
            print(f"Socket added: {websocket}")
            await websocket.accept()
            while True:
                try:
                    data = await websocket.receive_text()
                    if data is not None:
                        try:
                            print(f"Raw message: {data}")
                            message = json.loads(data, object_hook=dict)
                            if "name" in message and "data" in message:
                                print(f"Message is valid: {message}")
                                name = message["name"]
                                data = message["data"]
                                if name in self.socket_callbacks:
                                    await self.socket_callbacks[name](websocket, data)
                                else:
                                    print(f"Undefined message: {message}")
                            else:
                                print(f"Invalid message: {message}")
                        except Exception as e:
                            print(f"Exception parsing socket message: {e}")
                            traceback.print_exc()
                    else:
                        print("NO DATA!")
                except Exception as f:
                    print(f"SOCKET EXCEPTION: {f}")
                    traceback.print_exc()
                    if websocket in self.clients:
                        self.clients.remove(websocket)
                    break

        self.clients = []
        self.socket_callbacks = {}

    async def broadcast(self, message: str):
        for client in self.clients:
            await client.send_text(message)

    def register(self, name: str, callback):
        print(f"Socket callback registered: {name}")
        self.socket_callbacks[name] = callback

    def deregister(self, name):
        if name in self.socket_callbacks:
            del self.socket_callbacks[name]
