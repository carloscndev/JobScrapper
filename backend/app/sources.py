"""Contracts and domain services for compliant job sources.

This module intentionally has no FastAPI or HTTP-client dependency.  Concrete
adapters (implemented in later tasks) can be plugged into the pipeline through
``SourceAdapter`` while the rest of the application deals only with
``NormalizedJob`` values.  Source configuration is represented by
``SourceConfig`` and can be persisted using :class:`SourceService`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from .constants import KIND_MAP
from .models import Source

if TYPE_CHECKING:
    from .repositories import SourceRepository


class SourceKind(StrEnum):
    """Supported source categories; adapters may add metadata in ``config``."""

    API = "api"
    FEED = "feed"
    CAREER_PAGE = "career_page"


class WorkModality(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class JobRegion(StrEnum):
    """Stable geographic buckets used by the dashboard and regional views."""

    CDMX = "cdmx"
    GUADALAJARA = "guadalajara"
    MEXICO = "mexico"
    USA = "usa"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Runtime configuration supplied to an adapter.

    ``settings`` may contain non-secret adapter options.  Credentials must be
    references to environment/configuration keys, never raw tokens or cookies.
    """

    name: str
    kind: SourceKind = SourceKind.CAREER_PAGE
    base_url: str | None = None
    terms_url: str | None = None
    # Explicit operator acknowledgement is required before an adapter may
    # fetch a source.  ``settings['terms_accepted']`` is accepted as a config
    # file equivalent for backwards-compatible deserialization.
    terms_accepted: bool = False
    enabled: bool = True
    timeout_seconds: float = 20.0
    requests_per_minute: int = 30
    max_retries: int = 2
    settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("source name cannot be empty")
        for field_name in ("base_url", "terms_url"):
            value = getattr(self, field_name)
            if value is not None and urlparse(value).scheme not in {"http", "https"}:
                raise ValueError(f"{field_name} must be an http(s) URL")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be greater than zero")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")

    def validate_terms_acceptance(self) -> None:
        if not (self.terms_accepted or self.settings.get("terms_accepted") is True):
            raise ValueError(
                "terms_accepted=True is required after reviewing the source terms of use"
            )


@dataclass(frozen=True, slots=True)
class NormalizedJob:
    """Source-independent representation of a discovered job posting."""

    title: str
    company: str
    description: str
    description_url: str
    application_url: str | None = None
    canonical_url: str | None = None
    location: str | None = None
    region: str = "other"
    modality: WorkModality = WorkModality.UNKNOWN
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    published_at: date | None = None
    requirements: tuple[str, ...] = field(default_factory=tuple)
    salary_period: str | None = None
    source: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("description_url", "application_url", "canonical_url"):
            value = getattr(self, field_name)
            if value is not None and urlparse(value).scheme not in {"http", "https"}:
                raise ValueError(f"{field_name} must be an http(s) URL")
        if not self.title.strip() or not self.company.strip() or not self.description.strip():
            raise ValueError("title, company, and description are required")
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("salary_min cannot exceed salary_max")
        if self.salary_currency is not None and len(self.salary_currency) != 3:
            raise ValueError("salary_currency must be an ISO 4217 code")

    @property
    def effective_canonical_url(self) -> str:
        """Return the stable URL used by persistence/deduplication."""

        return self.canonical_url or self.description_url


@dataclass(frozen=True, slots=True)
class SourceFetchResult:
    """Outcome of one adapter fetch, including partial source failures."""

    jobs: Sequence[NormalizedJob] = field(default_factory=tuple)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: Sequence[str] = field(default_factory=tuple)
    error: str | None = None

    @property
    def status(self) -> str:
        if self.error and self.jobs:
            return "partial"
        if self.error:
            return "failed"
        return "success"


class SourceAdapter(ABC):
    """Adapter contract implemented by each permitted job source."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable source name matching ``SourceConfig.name``."""

    @abstractmethod
    def fetch(self, config: SourceConfig) -> SourceFetchResult:
        """Fetch and normalize jobs, honoring timeout and rate-limit settings."""


def resolve_source_adapter(
    source: Source,
    adapters: Sequence[SourceAdapter],
    config: Mapping[str, Any] | None = None,
) -> SourceAdapter | None:
    """Resolve one adapter using the same precedence for every ingestion path.

    An explicitly configured adapter is authoritative: an unknown override is
    an error at the call site rather than silently falling back to a kind
    mapping.  Without an override, a source name is checked first, followed by
    the canonical kind mapping and the raw kind value.
    """

    values = config if config is not None else (source.config or {})
    lookup = {str(adapter.name): adapter for adapter in adapters}
    override = values.get("adapter")
    if override is not None:
        return lookup.get(str(override))
    candidates = (source.name, KIND_MAP.get(source.kind), source.kind)
    for candidate in candidates:
        if candidate is not None and str(candidate) in lookup:
            return lookup[str(candidate)]
    return None


class SourceService:
    """Application-independent source configuration operations."""

    def __init__(self, sources: SourceRepository) -> None:
        self.sources = sources

    def list_enabled(self) -> Sequence[Source]:
        return self.sources.enabled()

    def configure(self, config: SourceConfig) -> Source:
        source = self.sources.get_or_create(
            config.name,
            kind=config.kind.value,
            base_url=config.base_url,
            terms_url=config.terms_url,
            enabled=config.enabled,
            config={
                **dict(config.settings),
                "timeout_seconds": config.timeout_seconds,
                "requests_per_minute": config.requests_per_minute,
                "max_retries": config.max_retries,
                "terms_accepted": config.terms_accepted or config.settings.get("terms_accepted", False),
            },
        )
        source.kind = config.kind.value
        source.base_url = config.base_url
        source.terms_url = config.terms_url
        source.enabled = config.enabled
        source.config = {
            **dict(config.settings),
            "timeout_seconds": config.timeout_seconds,
            "requests_per_minute": config.requests_per_minute,
            "max_retries": config.max_retries,
            "terms_accepted": config.terms_accepted or config.settings.get("terms_accepted", False),
        }
        self.sources.session.flush()
        return source

    def set_enabled(self, name: str, enabled: bool) -> Source:
        source = self.sources.get(name)
        if source is None:
            raise ValueError(f"source {name!r} does not exist")
        source.enabled = enabled
        self.sources.session.flush()
        return source
