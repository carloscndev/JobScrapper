"""Uvicorn entrypoint for ``python -m app``."""

import uvicorn

from .config import Settings
from .observability import configure_logging


def main() -> None:
    settings = Settings.from_env()
    configure_logging(level=settings.log_level, path=settings.log_file,
                      max_bytes=settings.log_max_bytes, backup_count=settings.log_backup_count)
    uvicorn.run("app:create_app", host=settings.host, port=settings.port, factory=True)


if __name__ == "__main__":
    main()
