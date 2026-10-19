"""Thread pool and asynchronous job management for long-running operations."""

from typing import Any, Callable, Dict, Optional
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from offline_toolbox.core.models import JobDescriptor, JobStatus


class WorkerSignals(QObject):
    progress = Signal(str, float, str)  # job_id, progress (0.0 to 1.0), status_message
    finished = Signal(str, object)      # job_id, result
    error = Signal(str, str)            # job_id, error_message
    cancelled = Signal(str)             # job_id


class TaskWorker(QRunnable):
    """Executes long-running operations in Qt background threads without freezing UI."""

    def __init__(
        self,
        job_id: str,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__()
        self.job_id = job_id
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def report_progress(self, progress: float, message: str = "") -> None:
        if not self._is_cancelled:
            self.signals.progress.emit(self.job_id, progress, message)

    def run(self) -> None:
        if self._is_cancelled:
            self.signals.cancelled.emit(self.job_id)
            return

        try:
            # Inject cancel checker and progress reporter if function accepts them
            kwargs = dict(self.kwargs)
            result = self.fn(*self.args, **kwargs)

            if self._is_cancelled:
                self.signals.cancelled.emit(self.job_id)
            else:
                self.signals.finished.emit(self.job_id, result)
        except Exception as e:
            self.signals.error.emit(self.job_id, str(e))


class JobManager:
    """Manages active and queued background jobs across the application."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._thread_pool = QThreadPool.globalInstance()
            cls._instance._active_workers: Dict[str, TaskWorker] = {}
        return cls._instance

    def submit_job(
        self,
        job_id: str,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> TaskWorker:
        worker = TaskWorker(job_id, fn, *args, **kwargs)
        self._active_workers[job_id] = worker
        self._thread_pool.start(worker)
        return worker

    def cancel_job(self, job_id: str) -> None:
        worker = self._active_workers.get(job_id)
        if worker:
            worker.cancel()
