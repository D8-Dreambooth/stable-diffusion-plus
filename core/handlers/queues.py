import logging
from typing import Callable, Dict
from queue import Queue
from threading import Thread


logger = logging.getLogger(__name__)


class QueueHandler:
    _instance = None

    def __new__(cls, num_workers: int = 2):
        if cls._instance is None:
            cls._instance = super(QueueHandler, cls).__new__(cls)
            cls._instance.jobs_queue = Queue()
            cls._instance.workers = []
            for i in range(num_workers):
                logger = logging.getLogger(f"{__name__}.worker.{i}")
                t = Thread(target=cls._instance.execute_jobs, args=(logger,))
                cls._instance.workers.append(t)
                t.start()
        return cls._instance

    def put_job(self, first_callable: Callable, second_callable: Callable, message: Dict):
        """Method to put a job in the pub sub queue system"""
        logger.debug(f"Job added: {message}")
        self.jobs_queue.put((first_callable, second_callable, message))

    async def execute_jobs(self, logger):
        """Method executed by each worker thread to execute jobs in the pub sub queue system"""
        while True:
            logger.debug("EXECUTE")
            job = self.jobs_queue.get()
            logger.debug("Got job")
            first_callable = job[0]
            second_callable = job[1]
            message = job[2]
            logger.debug("Awaiting main method")
            message["data"] = await first_callable(**message)  # await the first callable
            logger.debug("Awaiting method callback")
            await second_callable(**message)  # await the second callable
            self.jobs_queue.task_done()
