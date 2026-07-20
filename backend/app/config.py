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
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: float = 30.0
    ollama_num_ctx: int = 2048
    ollama_num_thread: int = 2
    # Notion credentials are always resolved from environment variables.  The
    # token itself is intentionally not stored in Settings or persisted.
    notion_api_token_env: str = "NOTION_API_TOKEN"
    notion_database_id_env: str = "NOTION_DATABASE_ID"
    notion_api_version: str = "2025-09-03"
    notion_timeout_seconds: float = 20.0
    log_level: str = "INFO"
    log_file: str = "data/jobscrapper.log"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    max_concurrency: int = 1
    cpu_limit: str = "1.0"
    memory_limit: str = "512M"

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
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", defaults.ollama_base_url),
            ollama_model=os.getenv("OLLAMA_MODEL", defaults.ollama_model),
            ollama_timeout_seconds=_parse_float("OLLAMA_TIMEOUT_SECONDS", defaults.ollama_timeout_seconds),
            ollama_num_ctx=_parse_int("OLLAMA_NUM_CTX", defaults.ollama_num_ctx, minimum=256),
            ollama_num_thread=_parse_int("OLLAMA_NUM_THREAD", defaults.ollama_num_thread, minimum=1),
            notion_api_token_env=os.getenv("NOTION_API_TOKEN_ENV", defaults.notion_api_token_env),
            notion_database_id_env=os.getenv("NOTION_DATABASE_ID_ENV", defaults.notion_database_id_env),
            notion_api_version=os.getenv("NOTION_API_VERSION", defaults.notion_api_version),
            notion_timeout_seconds=_parse_float("NOTION_TIMEOUT_SECONDS", defaults.notion_timeout_seconds),
            log_level=os.getenv("JOBSCRAPPER_LOG_LEVEL", defaults.log_level).upper(),
            log_file=os.getenv("JOBSCRAPPER_LOG_FILE", defaults.log_file),
            log_max_bytes=_parse_int("JOBSCRAPPER_LOG_MAX_BYTES", defaults.log_max_bytes, minimum=1024),
            log_backup_count=_parse_int("JOBSCRAPPER_LOG_BACKUP_COUNT", defaults.log_backup_count, minimum=1),
            max_concurrency=_parse_int("JOBSCRAPPER_MAX_CONCURRENCY", defaults.max_concurrency, minimum=1),
            cpu_limit=os.getenv("JOBSCRAPPER_CPU_LIMIT", defaults.cpu_limit),
            memory_limit=os.getenv("JOBSCRAPPER_MEMORY_LIMIT", defaults.memory_limit),
        )


def _parse_bool(value: str) -> bool:
    """Parse an explicit boolean environment value."""

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("JOBSCRAPPER_DB_ECHO must be a boolean")


def _parse_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _parse_int(name: str, default: int, *, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value
