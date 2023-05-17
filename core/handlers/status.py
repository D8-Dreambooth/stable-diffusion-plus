import logging

from core.dataclasses.status_data import StatusData
from dreambooth import shared

logger = logging.getLogger(__name__)


class StatusHandler:
    socket_handler = None
    _instance = None
    _instances = {}
    _target = None
    _do_send = False
    status = StatusData()
    _user_name = None

    def __new__(cls, socket_handler=None, user_name=None, target=None):
        if cls._instance is None and socket_handler is not None:
            cls._instance = super(StatusHandler, cls).__new__(cls)
            cls._instance.socket_handler = socket_handler
            cls._instance.socket_handler.register("get_status", cls._instance._get_status)
            cls._instance.socket_handler.register("cancel", cls._instance.cancel)
            cls._instance.status = StatusData()
            cls._instance.queue = socket_handler.queue
            cls._instance._do_send = False
        if user_name is not None:
            instance_name = user_name if target is None else f"{user_name}_{target}"
            userinstance = cls._instances.get(instance_name, None)
            if userinstance is None:
                userinstance = super(StatusHandler, cls).__new__(cls)
                userinstance._target = target
                userinstance.socket_handler = cls._instance.socket_handler
                userinstance.socket_handler.register("get_status", userinstance._get_status, user_name)
                userinstance.socket_handler.register("cancel", userinstance.cancel, user_name)
                userinstance.status = StatusData()
                userinstance.queue = userinstance.socket_handler.queue
                userinstance._do_send = False
                userinstance._user_name = user_name
                cls._instances[user_name] = userinstance
            return userinstance
        else:
            return cls._instance

    def send(self):
        message = {"name": "status", "status": self.status.dict(), "user": self._user_name}
        if self._target is not None:
            message["target"] = self._target
        self.queue.put_nowait(message)

    async def send_async(self):
        message = {"name": "status", "status": self.status.dict(), "user": self._user_name}
        if self._target is not None:
            message["target"] = self._target
        await self.socket_handler.manager.broadcast(message)

    async def _get_status(self, data):
        status = {"status": self.status.dict()}
        if self._target is not None:
            status["target"] = self._target

    def start(self, total: int = 0, desc: str = ""):
        self.status.start()
        self.status.progress_1_total = total
        self.status.status = desc
        self.send()

    def end(self, desc: str):
        self.status.end(desc)
        self.send()

    def step(self, n: int = 1, secondary_bar: bool = False):
        if secondary_bar:
            self.status.progress_2_current += n
            if self.status.progress_2_current >= self.status.progress_2_total:
                self.status.progress_2_current = self.status.progress_2_total
        else:
            self.status.progress_1_current += n
            if self.status.progress_1_current >= self.status.progress_1_total:
                self.status.progress_1_current = self.status.progress_1_total
        self.send()

    async def cancel(self, data):
        self.end("Canceled")
        self.status.canceled = True
        shared.status.interrupted = True

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
        latents = []
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
        if shared.status.interrupted:
            self.status.canceled = True
        if not self.status.active and not self.status.canceled:
            self.status.active = True
        if send:
            self.send()
