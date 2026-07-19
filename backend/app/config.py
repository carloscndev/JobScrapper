"""Environment-backed settings for the HTTP service."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings read when the application is created."""

    app_name: str = "JobScrapper API"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///./data/jobscrapper.db"
    database_echo: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables with safe local defaults."""

        defaults = cls()
        raw_port = os.getenv("JOBSCRAPPER_PORT", str(defaults.port))
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ValueError("JOBSCRAPPER_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise ValueError("JOBSCRAPPER_PORT must be between 1 and 65535")
        return cls(
            app_name=os.getenv("JOBSCRAPPER_APP_NAME", defaults.app_name),
            environment=os.getenv("JOBSCRAPPER_ENV", defaults.environment),
            host=os.getenv("JOBSCRAPPER_HOST", defaults.host),
            port=port,
            database_url=os.getenv("DATABASE_URL", defaults.database_url),
            database_echo=_parse_bool(os.getenv("JOBSCRAPPER_DB_ECHO", str(defaults.database_echo))),
        )


def _parse_bool(value: str) -> bool:
    """Parse an explicit boolean environment value."""

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("JOBSCRAPPER_DB_ECHO must be a boolean")
