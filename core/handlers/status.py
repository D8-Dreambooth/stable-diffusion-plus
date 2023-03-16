import asyncio
from concurrent import futures
import logging

from core.dataclasses.status_data import StatusData

logger = logging.getLogger(__name__)


class StatusHandler:
    socket_handler = None
    _instance = None
    _do_send = False
    status = StatusData()

    def __new__(cls, socket_handler=None):
        if cls._instance is None:
            cls._instance = super(StatusHandler, cls).__new__(cls)
            cls._instance.socket_handler = socket_handler
            cls._instance.socket_handler.register("get_status", cls._instance._get_status)
            cls._instance.socket_handler.register("cancel", cls._instance.cancel)
            cls._instance.status = StatusData()
            cls._instance.queue = socket_handler.queue
            cls._instance._do_send = False
        return cls._instance

    def send(self):
        message = {"name": "status", "status": self.status.dict()}
        self.queue.put_nowait(message)
        logger.debug("Really sent")

    async def _get_status(self, data):
        return {"status": self.status.dict()}

    def start(self, total: int, desc: str):
        self.status.start()
        self.status.progress_1_total = total
        self.status.status = desc
        self.send()

    def end(self, desc: str):
        self.status.end()
        self.status.status = desc
        self.send()

    def step(self, n: int = 1, secondary_bar: bool = False):
        logger.debug("\nSTEP")
        if secondary_bar:
            self.status.progress_2_current += n
            if self.status.progress_2_current >= self.status.progress_2_total:
                self.status.progress_2_current = self.status.progress_2_total
        else:
            self.status.progress_1_current += n
            if self.status.progress_1_current >= self.status.progress_1_total:
                self.status.progress_1_current = self.status.progress_1_total
        self.send()

    def cancel(self, data):
        self.status.canceled = True
        message = {"name": "status", "status": self.status.dict()}
        self.send()

    def update(self, key=None, value=None, items=None, send=True):
        """

        :param key: 
        One of the following:
        status = ""
        status_2 = ""
        progress_1_total = 0
        progress_1_current = 0
        progress_2_total = 0
        progress_2_current = 0
        active = False
        canceled = False
        images = []
        prompts = []
        descriptions = []
        :param value: 
        :param items: 
        :param send: 
        """
        if key is not None and value is not None:
            setattr(self.status, key, value)
        if items:
            for k, v in items.items():
                setattr(self.status, k, v)
        if send:
            logger.debug("SENDD")
            self.send()
