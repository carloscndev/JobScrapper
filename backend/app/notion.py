"""Local-only Notion integration configuration and vacancy schema.

The application keeps SQLite as its source of truth.  This module describes
the shape of the Notion master database and its regional views; network
requests and page upserts belong to the synchronization task.  Credentials
are environment-variable references, never values embedded in configuration
files or logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from .config import Settings


REGIONS = ("cdmx", "guadalajara", "mexico", "usa", "other")
REGIONAL_VIEWS = {
    "CDMX": {"property": "Region", "select": {"equals": "cdmx"}},
    "Guadalajara": {"property": "Region", "select": {"equals": "guadalajara"}},
    "Mexico": {"property": "Region", "select": {"equals": "mexico"}},
    "USA": {"property": "Region", "select": {"equals": "usa"}},
    "Other": {"property": "Region", "select": {"equals": "other"}},
}


# Property types use the Notion data-source schema vocabulary.  Long job
# descriptions remain in SQLite; the Notion page contains links and the
# bounded explanation fields needed for prioritization.
NOTION_JOB_SCHEMA: dict[str, dict[str, Any]] = {
    "Title": {"title": {}},
    "Company": {"rich_text": {}},
    "Region": {"select": {"options": [{"name": item} for item in REGIONS]}},
    "Modality": {"select": {"options": [{"name": item} for item in ("remote", "hybrid", "onsite", "unknown")]}},
    "Location": {"rich_text": {}},
    "Requirements": {"rich_text": {}},
    "Salary min": {"number": {"format": "number"}},
    "Salary max": {"number": {"format": "number"}},
    "Salary currency": {"select": {}},
    "Salary period": {"select": {}},
    "Source": {"rich_text": {}},
    "Description URL": {"url": {}},
    "Application URL": {"url": {}},
    "Canonical URL": {"url": {}},
    "Published": {"date": {}},
    "Detected": {"date": {}},
    "Checked": {"date": {}},
    # Scores are stored as the auditable 0-100 value used by SQLite/UI.
    "Compatibility score": {"number": {"format": "number"}},
    "Score explanation": {"rich_text": {}},
    "Matches": {"rich_text": {}},
    "Gaps": {"rich_text": {}},
    "Recommendations": {"rich_text": {}},
    "Status": {"select": {"options": [{"name": item} for item in ("active", "inactive", "pending")]}},
    "Local job ID": {"rich_text": {}},
    "Fingerprint": {"rich_text": {}},
}


@dataclass(frozen=True, slots=True)
class NotionConfig:
    """Safe references needed by a future Notion client.

    ``token_env`` and ``database_id_env`` are names only.  ``token`` is read
    on demand, so a config object cannot accidentally be serialized with a
    secret.  ``require_credentials`` is called by the sync worker immediately
    before an outbound request.
    """

    token_env: str = "NOTION_API_TOKEN"
    database_id_env: str = "NOTION_DATABASE_ID"
    api_version: str = "2025-09-03"
    timeout_seconds: float = 20.0

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "NotionConfig":
        runtime = settings or Settings.from_env()
        return cls(runtime.notion_api_token_env, runtime.notion_database_id_env, runtime.notion_api_version, runtime.notion_timeout_seconds)

    @property
    def database_id(self) -> str | None:
        return os.getenv(self.database_id_env) or None

    def require_credentials(self) -> tuple[str, str]:
        credential = os.getenv(self.token_env)
        database_id = self.database_id
        if not credential:
            raise RuntimeError(f"Notion token is missing; set {self.token_env} in the local environment")
        if not database_id:
            raise RuntimeError(f"Notion database id is missing; set {self.database_id_env} in the local environment")
        return credential, database_id

    def redacted(self) -> dict[str, Any]:
        """Return log-safe configuration metadata without credential values."""

        return {"token_env": self.token_env, "database_id_env": self.database_id_env, "api_version": self.api_version, "timeout_seconds": self.timeout_seconds, "configured": bool(self.database_id and os.getenv(self.token_env))}


def schema_for_data_source() -> dict[str, Any]:
    """Return a deep-copy-safe Notion schema payload."""

    import copy

    return copy.deepcopy(NOTION_JOB_SCHEMA)


def regional_views() -> Mapping[str, dict[str, Any]]:
    """Return the five supported filtered views for a master database."""

    import copy

    return copy.deepcopy(REGIONAL_VIEWS)
