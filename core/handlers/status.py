import logging

from core.dataclasses.status_data import StatusData
from core.handlers.websocket import SocketHandler

logger = logging.getLogger(__name__)


class StatusHandler:
    socket_handler = None
    _instance = None
    status = StatusData()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StatusHandler, cls).__new__(cls)
            cls.socket_handler = SocketHandler()
            cls.socket_handler.register("get_status", cls._instance._get_status)
            cls.socket_handler.register("cancel", cls._instance.cancel)
            cls.status = StatusData()
        return cls._instance

    async def _get_status(self, data):
        return {"status": self.status.dict()}

    def start(self, total: int, desc: str):
        self.status.start()
        self.status.progress_1_total = total
        self.status.status = desc
        self.send({"name": "status", "status": self.status.dict()})

    async def step(self, n: int = 1, secondary_bar: bool = False):
        logger.debug("\nSTEP")
        if secondary_bar:
            self.status.progress_2_current += n
            if self.status.progress_2_current >= self.status.progress_2_total:
                self.status.progress_2_current = self.status.progress_2_total
        else:
            self.status.progress_1_current += n
            if self.status.progress_1_current >= self.status.progress_1_total:
                self.status.progress_1_current = self.status.progress_1_total
        await self.send({"name": "status", "status": self.status.dict()})
        logger.debug("SENT")

    async def cancel(self, data):
        self.status.canceled = True
        await self.send({"name": "status", "status": self.status.dict()})
        return {"status": self.status.dict()}

    async def update(self, key=None, value=None, items=None, send=True):
        if key is not None and value is not None:
            setattr(self.status, key, value)
            if send:
                await self.send({"name": "status", "status": self.status.dict()})
        if items:
            for k, v in items.items():
                setattr(self.status, k, v)
            if send:
                await self.send({"name": "status", "status": self.status.dict()})
                
    async def send(self, message):
        logger.debug("Really sending")
        socket_handler = SocketHandler()
        logger.debug("Broadcasting")
        # logger.debug(f"Sending message: {message}")
        await socket_handler.manager.broadcast(message)
        logger.debug("Broadcasted...")
