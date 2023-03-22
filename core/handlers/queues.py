import asyncio
import logging
import threading
from queue import Queue

logger = logging.getLogger(__name__)


class QueueHandler:
    _instance = None

    def __new__(cls, num_workers=None):
        if cls._instance is None and num_workers is not None:
            cls._instance = super().__new__(cls)
            cls._instance.num_workers = num_workers
            cls._instance.job_queue = Queue()
            cls._instance.worker_threads = []
            cls._instance.initialize_workers()
            cls._instance.loop = asyncio.get_event_loop()
            cls._instance.loop_thread = threading.Thread(target=cls._instance.run_loop, daemon=True)
            cls._instance.loop_thread.start()
        return cls._instance

    def initialize_workers(self):
        for _ in range(self.num_workers):
            logger.debug(f"Initializing worker: {_}")
            worker = threading.Thread(target=self.worker_function, daemon=True)
            worker.start()
            self.worker_threads.append(worker)

    def put_job(self, method1, method2, cls, message):
        coro = self.coro_wrapper(method1, method2, self, message)
        self.job_queue.put(coro)
        num_jobs = self.job_queue.qsize() - 1  # subtract the current job
        return num_jobs

    async def coro_wrapper(self, method1, method2, cls, message):
        result = await method1(message)
        message["data"] = result
        logger.debug(f"RES1: {message}")
        await method2(cls, message)

    def worker_function(self):
        while True:
            try:
                coro = self.job_queue.get()  # use parentheses to unpack the result
                asyncio.run_coroutine_threadsafe(coro, self.loop)
                self.job_queue.task_done()
            except Exception as e:
                logger.exception("Error in worker function", exc_info=e)
                self.job_queue.task_done()  # make sure to mark the job as done even if an error occurs

    def run_loop(self):
        asyncio.set_event_loop(self.loop)
        if not self.loop.is_running():
            self.loop.run_forever()

    def subscribe_consume(self):

        self.job_queue.join()
        for worker in self.worker_threads:
            worker.join()
