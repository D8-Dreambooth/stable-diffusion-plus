import json
import traceback

from starlette.websockets import WebSocket, WebSocketDisconnect


class SocketHandler:
    _instance = None

    def __new__(cls, app):
        if cls._instance is None:
            cls._instance = super(SocketHandler, cls).__new__(cls)
            cls._instance.clients = []
            cls._instance.socket_callbacks = {}

            @app.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket):
                cls._instance.clients.append(websocket)
                print(f"Socket added: {websocket}")
                await websocket.accept()
                while True:
                    try:
                        data = await websocket.receive_text()
                        if data is not None:
                            try:
                                print(f"Raw message: {data}")
                                message = json.loads(data)
                                print(f"Socket message: {message}")
                                if "type" in message and message["type"] in cls._instance.socket_callbacks:
                                    await cls._instance.socket_callbacks[message["type"]](websocket, message)
                                else:
                                    print(f"Undefined message: {message}")
                            except Exception as e:
                                print(f"Exception parsing socket message: {e}")
                                traceback.print_exc()
                    except WebSocketDisconnect:
                        print("Client disconnected.")
                        cls._instance.clients.remove(websocket)
                        pass

        return cls._instance

    async def broadcast(self, message: str):
        for client in self.clients:
            await client.send_text(message)

    def register(self, name: str, callback):
        self.socket_callbacks[name] = callback

    def deregister(self, name):
        if name in self.socket_callbacks:
            del self.socket_callbacks[name]
