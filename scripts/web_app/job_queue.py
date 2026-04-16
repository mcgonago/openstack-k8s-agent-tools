import threading
from concurrent.futures import ThreadPoolExecutor


class JobQueue:
    def __init__(self, max_workers=3):
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs = {}
        self._lock = threading.Lock()

    def submit(self, exec_id, fn, *args, **kwargs):
        future = self._pool.submit(fn, *args, **kwargs)
        with self._lock:
            self._jobs[exec_id] = future
        return future

    def get_status(self, exec_id):
        with self._lock:
            future = self._jobs.get(exec_id)
        if future is None:
            return 'unknown'
        if future.cancelled():
            return 'cancelled'
        if future.running():
            return 'running'
        if future.done():
            exc = future.exception()
            return 'failed' if exc else 'completed'
        return 'queued'

    def cancel(self, exec_id):
        with self._lock:
            future = self._jobs.get(exec_id)
        if future and not future.done():
            return future.cancel()
        return False

    def get_active_count(self):
        with self._lock:
            return sum(1 for f in self._jobs.values() if f.running())

    def get_total_count(self):
        with self._lock:
            return len(self._jobs)


queue = JobQueue(max_workers=3)
