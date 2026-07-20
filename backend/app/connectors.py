"""Compliant, fixture-friendly connectors for permitted job sources.

Connectors deliberately accept inline fixtures (or a fixture path) so tests and
local development never need to contact a real job board.  Network fetching is
opt-in through ``settings['allow_network']`` and checks robots.txt first.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from typing import Any, Mapping

from .sources import NormalizedJob, SourceAdapter, SourceConfig, SourceFetchResult, WorkModality


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _modality(value: Any) -> WorkModality:
    text = str(value or "").lower()
    if "remote" in text:
        return WorkModality.REMOTE
    if "hybrid" in text:
        return WorkModality.HYBRID
    if "onsite" in text or "on-site" in text or "office" in text:
        return WorkModality.ONSITE
    return WorkModality.UNKNOWN


def _job(item: Mapping[str, Any], base_url: str | None, source: str) -> NormalizedJob:
    description_url = str(item.get("description_url") or item.get("url") or item.get("apply_url") or "")
    application_url = item.get("application_url") or item.get("apply_url")
    description_url = urljoin(base_url or "", description_url)
    application_url = urljoin(base_url or "", str(application_url)) if application_url else None
    if not description_url or urlparse(description_url).scheme not in {"http", "https"}:
        raise ValueError("job is missing a valid description URL")
    return NormalizedJob(
        title=str(item.get("title") or item.get("name") or "Untitled role").strip(),
        company=str(item.get("company") or item.get("employer") or source).strip(),
        description=str(item.get("description") or item.get("summary") or "No description provided").strip(),
        description_url=description_url,
        application_url=application_url,
        canonical_url=urljoin(base_url or "", str(item["canonical_url"])) if item.get("canonical_url") else description_url,
        location=item.get("location"),
        region=str(item.get("region") or "other"),
        modality=_modality(item.get("modality") or item.get("workplace_type")),
        salary_min=item.get("salary_min"), salary_max=item.get("salary_max"),
        salary_currency=item.get("salary_currency") or item.get("currency"),
        published_at=_date(item.get("published_at") or item.get("date_posted")),
        metadata={"source_adapter": source, **dict(item.get("metadata") or {})},
    )


def _content(config: SourceConfig, key: str) -> str:
    config.validate_terms_acceptance()
    settings = dict(config.settings)
    if key in settings:
        return str(settings[key])
    path = settings.get(f"{key}_path")
    if path:
        return Path(str(path)).read_text(encoding="utf-8")
    if not settings.get("allow_network", False):
        raise RuntimeError(f"{config.name} requires an inline {key} fixture or allow_network=true")
    if not config.base_url:
        raise ValueError("base_url is required for network fetching")
    _robots_check(config.base_url, str(settings.get("user_agent", "JobScrapper/0.1")))
    request = urllib.request.Request(config.base_url, headers={"User-Agent": str(settings.get("user_agent", "JobScrapper/0.1"))})
    with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:  # noqa: S310 - explicit opt-in
        return response.read().decode("utf-8", errors="replace")


def _robots_check(url: str, user_agent: str) -> None:
    parsed = urlparse(url)
    robots = RobotFileParser(urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt"))
    robots.read()
    if not robots.can_fetch(user_agent, url):
        raise PermissionError(f"robots.txt disallows fetching {url}")


class JsonApiFeedAdapter(SourceAdapter):
    """Adapter for a JSON API or feed returning a list under ``jobs``/``data``."""

    def __init__(self, adapter_name: str = "json-api-feed") -> None:
        self._name = adapter_name

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, config: SourceConfig) -> SourceFetchResult:
        try:
            config.validate_terms_acceptance()
            payload = json.loads(_content(config, "payload"))
            items = payload if isinstance(payload, list) else payload.get("jobs", payload.get("data", []))
            jobs = tuple(_job(item, config.base_url, self.name) for item in items if isinstance(item, Mapping))
            return SourceFetchResult(jobs=jobs)
        except Exception as exc:  # source isolation is handled by the pipeline
            return SourceFetchResult(error=f"{type(exc).__name__}: {exc}")


class _CardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.cards: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._field: str | None = None
        self._anchor: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: v or "" for k, v in attrs}
        if values.get("data-job") == "true" or "job-card" in values.get("class", "") or tag == "article":
            self._current = {}
        if self._current is not None:
            self._field = values.get("data-field")
            classes = values.get("class", "").lower()
            for marker, field in (("title", "title"), ("position", "title"), ("description", "description"), ("location", "location")):
                if marker in classes:
                    self._field = field
            if tag == "a" and values.get("href"):
                # Keep the first ordinary link as the posting/description URL;
                # Apply/Postular links are recorded separately by href below.
                self._anchor = {"href": values["href"], "class": classes, "field": self._field or values.get("data-field", "")}
                # Anchor labels are metadata used for classification only.  Do
                # not let their visible text populate (or overwrite) a job
                # field, especially ``application_url``.
                self._field = None

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._field:
            self._current[self._field] = (self._current.get(self._field, "") + " " + data).strip()
        if self._anchor is not None:
            self._anchor["text"] = (self._anchor.get("text", "") + " " + data).strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current is not None and self._anchor is not None:
            anchor = self._anchor
            label = f"{anchor.get('class', '')} {anchor.get('field', '')} {anchor.get('text', '')}".lower()
            is_apply = any(marker in label for marker in ("apply", "postular", "application"))
            if is_apply:
                # href is authoritative; anchor text is never a URL.
                self._current["application_url"] = anchor["href"]
            else:
                self._current.setdefault("url", anchor["href"])
            self._anchor = None
        if self._current is not None and tag in {"article", "li"}:
            self.cards.append(self._current)
            self._current = None
            self._field = None


class _CareerPageAdapter(SourceAdapter):
    def __init__(self, adapter_name: str, company: str) -> None:
        self._name, self.company = adapter_name, company

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, config: SourceConfig) -> SourceFetchResult:
        try:
            config.validate_terms_acceptance()
            parser = _CardParser()
            parser.feed(_content(config, "html"))
            jobs = tuple(_job({**card, "company": self.company, "description_url": card.get("url")}, config.base_url, self.name) for card in parser.cards if card.get("url"))
            return SourceFetchResult(jobs=jobs)
        except Exception as exc:
            return SourceFetchResult(error=f"{type(exc).__name__}: {exc}")


class GreenhouseCareerPageAdapter(_CareerPageAdapter):
    def __init__(self) -> None:
        super().__init__("greenhouse-career-page", "Greenhouse employer")


class LeverCareerPageAdapter(_CareerPageAdapter):
    def __init__(self) -> None:
        super().__init__("lever-career-page", "Lever employer")


DEFAULT_ADAPTERS = (JsonApiFeedAdapter(), GreenhouseCareerPageAdapter(), LeverCareerPageAdapter())
