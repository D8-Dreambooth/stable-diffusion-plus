import logging

from core.dataclasses.status_data import StatusData

logger = logging.getLogger(__name__)


class StatusHandler:
    socket_handler = None
    _instance = None
    _instances = {}
    _do_send = False
    status = StatusData()
    _user_name = None

    def __new__(cls, socket_handler=None, user_name=None):
        if cls._instance is None and socket_handler is not None:
            cls._instance = super(StatusHandler, cls).__new__(cls)
            cls._instance.socket_handler = socket_handler
            cls._instance.socket_handler.register("get_status", cls._instance._get_status)
            cls._instance.socket_handler.register("cancel", cls._instance.cancel)
            cls._instance.status = StatusData()
            cls._instance.queue = socket_handler.queue
            cls._instance._do_send = False
        if user_name is not None:
            userinstance = cls._instances.get(user_name, None)
            if userinstance is None:
                logger.debug(f"Creating new status handler for user: {user_name}")
                userinstance = super(StatusHandler, cls).__new__(cls)
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
            logger.debug(f"Returning existing user-specific instance of status handler: {user_name}")
            return cls._instance

    def send(self):
        message = {"name": "status", "status": self.status.dict(), "user":self._user_name}
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
        logger.debug(f"\nSTEP: {n}")
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
