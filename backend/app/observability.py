"""Structured, redacted application logging with bounded file rotation."""

from __future__ import annotations

import json
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_SECRET_KEY = re.compile(r"(token|secret|password|passwd|api[-_]?key|authorization|cookie|credential)", re.I)
_SECRET_VALUE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")


def redact(value: Any) -> Any:
    """Return a recursively redacted copy suitable for logs and JSON output."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if _SECRET_KEY.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub(r"\1[REDACTED]", value)
    return value


class JsonFormatter(logging.Formatter):
    """Emit one compact JSON object per line with a stable event shape."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        for key in ("run_id", "execution_id", "event", "source"):
            if hasattr(record, key):
                payload[key] = redact(getattr(record, key))
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(*, level: str = "INFO", path: str = "data/jobscrapper.log",
                      max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5) -> logging.Logger:
    """Configure process logging once; subsequent calls replace no handlers."""
    logger = logging.getLogger("jobscrapper")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    if logger.handlers:
        return logger
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(target, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    # Keep stderr useful in containers while the rotating file remains bounded.
    stream = logging.StreamHandler()
    stream.setFormatter(JsonFormatter())
    logger.addHandler(stream)
    return logger


def configure_from_env() -> logging.Logger:
    """Configure logging from environment without importing application settings."""
    return configure_logging(
        level=os.getenv("JOBSCRAPPER_LOG_LEVEL", "INFO"),
        path=os.getenv("JOBSCRAPPER_LOG_FILE", "data/jobscrapper.log"),
        max_bytes=int(os.getenv("JOBSCRAPPER_LOG_MAX_BYTES", str(10 * 1024 * 1024))),
        backup_count=int(os.getenv("JOBSCRAPPER_LOG_BACKUP_COUNT", "5")),
    )
