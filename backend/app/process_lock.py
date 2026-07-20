"""Cross-process lock used by manual and scheduled pipeline runs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO

import fcntl

DEFAULT_LOCK_FILE = "data/jobscrapper.pipeline.lock"


class ProcessLock:
    """Non-blocking advisory lock backed by ``flock``."""

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        configured = Path(path or os.getenv("JOBSCRAPPER_LOCK_FILE", DEFAULT_LOCK_FILE))
        # Resolve the default relative to the repository, not the caller's
        # working directory (uvicorn and cron commonly start from different
        # directories). Explicit absolute paths remain untouched.
        self.path = configured if configured.is_absolute() else Path(__file__).resolve().parents[2] / configured
        self._handle: IO[str] | None = None

    def acquire(self, blocking: bool = True) -> bool:
        if self._handle is not None:
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        try:
            fcntl.flock(handle.fileno(), flags)
        except BlockingIOError:
            handle.close()
            return False
        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is None:
            return
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        self._handle = None
