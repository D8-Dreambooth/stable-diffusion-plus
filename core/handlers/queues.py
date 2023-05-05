import asyncio
import logging
from queue import Queue
from threading import Thread
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class QueueHandler:
    _instance = None

    def __new__(cls, num_workers: int = 2):
        if cls._instance is None:
            cls._instance = super(QueueHandler, cls).__new__(cls)
            cls._instance.jobs_queue = Queue()
            cls._instance.workers = []

            for i in range(num_workers):
                
                thread_logger = logging.getLogger(f"{__name__}.worker.{i}")
                t = Thread(target=cls._instance.run_coroutine, args=(cls._instance.execute_jobs, thread_logger))
                cls._instance.workers.append(t)
                t.start()

        return cls._instance

    def run_coroutine(self, coro, logger):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro(logger))
        finally:
            loop.close()

    def put_job(self, first_callable: Callable, second_callable: Callable, message: Dict):
        """Method to put a job in the pub sub queue system"""
        self.jobs_queue.put((first_callable, second_callable, message))

    async def execute_jobs(self, logger = None):
        """Method executed by each worker thread to execute jobs in the pub sub queue system"""
        while True:
            job = self.jobs_queue.get()
            first_callable = job[0]
            second_callable = job[1]
            message = job[2]
            if logger:
                logger.debug(f"Executing job {message}")
            message["data"] = await first_callable(message)  # await the first callable
            await second_callable(message)  # await the second callable
            self.jobs_queue.task_done()
