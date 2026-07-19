"""Uvicorn entrypoint for ``python -m app``."""

import uvicorn

from .config import Settings


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run("app:create_app", host=settings.host, port=settings.port, factory=True)


if __name__ == "__main__":
    main()
