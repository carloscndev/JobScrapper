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
        )
