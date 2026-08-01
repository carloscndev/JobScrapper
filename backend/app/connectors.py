"""Compliant, fixture-friendly connectors for permitted job sources.

Connectors deliberately accept inline fixtures (or a fixture path) so tests and
local development never need to contact a real job board.  Network fetching is
opt-in through ``settings['allow_network']`` and checks robots.txt first.
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunsplit
from urllib.robotparser import RobotFileParser
from typing import Any, Mapping

from .sources import JobRegion, NormalizedJob, SourceAdapter, SourceConfig, SourceFetchResult, WorkModality


class _RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}

    def wait(self, source: str, requests_per_minute: int) -> None:
        interval = 60.0 / requests_per_minute
        with self._lock:
            delay = interval - (time.monotonic() - self._last.get(source, 0.0))
            if delay > 0:
                time.sleep(min(delay, 60.0))
            self._last[source] = time.monotonic()


_RATE_LIMITER = _RateLimiter()


def _date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        # Lever commonly returns Unix timestamps in milliseconds while other
        # feeds use seconds.  Normalize both forms and isolate malformed
        # provider values to the record instead of failing the whole source.
        timestamp = float(value)
        if abs(timestamp) >= 100_000_000_000:
            timestamp /= 1000
        try:
            return date.fromtimestamp(timestamp)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return _date(float(text))
    try:
        return date.fromisoformat(text[:10])
    except (ValueError, TypeError):
        return None


def _number(value: Any) -> float | None:
    """Parse common feed salary values without failing the whole source."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def _currency(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip().upper()
    if "MXN" in text or "MX$" in text:
        return "MXN"
    if "USD" in text or "US$" in text:
        return "USD"
    aliases = {"$": "USD", "US$": "USD", "USD$": "USD", "MX$": "MXN", "M\u00d7N": "MXN"}
    text = aliases.get(text, text)
    return text if re.fullmatch(r"[A-Z]{3}", text) else None


def classify_region(location: Any, explicit: Any = None) -> JobRegion:
    """Map free-form locations to the five supported regional buckets."""
    text = " ".join(str(value or "") for value in (explicit, location)).lower()
    text = re.sub(r"[\u00e1\u00e0\u00e4]", "a", text)
    text = re.sub(r"[\u00e9\u00e8\u00eb]", "e", text)
    text = re.sub(r"[\u00ed\u00ec\u00ef]", "i", text)
    text = re.sub(r"[\u00f3\u00f2\u00f6]", "o", text)
    text = re.sub(r"[\u00fa\u00f9\u00fc]", "u", text)
    if re.search(r"\b(cdmx|ciudad de mexico|mexico city|distrito federal)\b", text):
        return JobRegion.CDMX
    if re.search(r"\b(guadalajara|zapopan|jalisco)\b", text):
        return JobRegion.GUADALAJARA
    if re.search(r"\b(usa|u\.s\.a\.?|united states|estados unidos|\b(us)\b)", text):
        return JobRegion.USA
    if re.search(r"\b(mexico|mexico|mx|monterrey|queretaro|puebla|merida|tijuana)\b", text):
        return JobRegion.MEXICO
    return JobRegion.OTHER


def _requirements(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    values = value if isinstance(value, (list, tuple, set)) else re.split(r"\n|[•;]", str(value))
    return tuple(item for item in (_sanitize_text(str(item)) for item in values) if item)


def _modality(value: Any) -> WorkModality:
    text = str(value or "").lower()
    if "remote" in text:
        return WorkModality.REMOTE
    if "hybrid" in text:
        return WorkModality.HYBRID
    if "onsite" in text or "on-site" in text or "office" in text:
        return WorkModality.ONSITE
    return WorkModality.UNKNOWN


def _sanitize_text(value: str) -> str:
    """Remove markup/control content before storing or model processing."""
    value = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join("".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32).split())


def _normalise_base_url(base_url: str | None) -> str:
    """Return a directory-style HTTP(S) base for consistent relative joins."""
    if not base_url:
        return ""
    parsed = urlparse(str(base_url).strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"source base_url must be an absolute HTTP(S) URL: {base_url!r}")
    path = parsed.path or "/"
    if not path.endswith("/"):
        path += "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", ""))


def _resolve_job_url(value: Any, base_url: str, field: str, *, required: bool = False) -> str | None:
    """Resolve and validate one source link, preserving actionable field names."""
    if value is None or not str(value).strip():
        if required:
            raise ValueError(f"job is missing a valid {field} URL")
        return None
    raw = str(value).strip()

    # Validate the source value before joining it.  ``urljoin`` treats malformed
    # absolute-looking values such as ``https:`` as relative paths, which could
    # otherwise silently fall back to the configured source base URL.
    try:
        if any(ord(char) < 32 for char in raw):
            raise ValueError
        raw_parsed = urlparse(raw)
        if raw.startswith("//"):
            raise ValueError
        if raw_parsed.scheme:
            if raw_parsed.scheme.lower() not in {"http", "https"}:
                raise ValueError
            if not raw_parsed.netloc or not raw_parsed.hostname:
                raise ValueError
            # Accessing ``port`` validates malformed and out-of-range ports.
            raw_parsed.port
            if any(char.isspace() or ord(char) < 32 for char in raw_parsed.hostname):
                raise ValueError
    except (TypeError, ValueError):
        raise ValueError(f"job has an invalid {field} URL: {value!r}") from None

    resolved = urljoin(base_url, raw)
    try:
        parsed = urlparse(resolved)
        parsed.port
        hostname = parsed.hostname
    except (TypeError, ValueError):
        raise ValueError(f"job has an invalid {field} URL: {value!r}") from None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not hostname:
        raise ValueError(f"job has an invalid {field} URL: {value!r}")
    if any(char.isspace() or ord(char) < 32 for char in hostname):
        raise ValueError(f"job has an invalid {field} URL: {value!r}")
    return resolved


def _job(
    item: Mapping[str, Any],
    base_url: str | None,
    source: str,
    *,
    default_company: str | None = None,
) -> NormalizedJob:
    # A source's base URL is normalized once so ``/jobs`` and ``jobs`` resolve
    # identically whether the configured base ends in a slash or not.
    normalized_base = _normalise_base_url(base_url)
    # Application links must never become a fallback description link: source
    # provenance and the two user-facing actions are distinct fields.
    description_url = _resolve_job_url(
        item.get("description_url") or item.get("url") or item.get("absolute_url") or item.get("hostedUrl"),
        normalized_base,
        "description",
        required=True,
    )
    application_url = _resolve_job_url(
        item.get("application_url") or item.get("apply_url") or item.get("applyUrl"),
        normalized_base,
        "application",
    )
    location_value = (item.get("location") or item.get("locations") or item.get("candidate_required_location")
                      or item.get("jobLocation") or item.get("jobGeo"))
    if isinstance(location_value, Mapping):
        location_value = location_value.get("name") or location_value.get("location")
    categories = item.get("categories")
    if not location_value and isinstance(categories, Mapping):
        location_value = categories.get("location")
    location = str(location_value or "").strip() or None
    salary_min = _number(item.get("salary_min") or item.get("salaryMin"))
    salary_max = _number(item.get("salary_max") or item.get("salaryMax"))
    if salary_min is None and salary_max is None and item.get("salary"):
        amounts = re.findall(r"\d[\d,]*(?:\.\d+)?", str(item["salary"]))
        if amounts:
            salary_min = _number(amounts[0])
            salary_max = _number(amounts[-1])
    requirements = _requirements(item.get("requirements") or item.get("qualifications") or item.get("must_have"))
    metadata = {"source_adapter": source, "requirements": list(requirements)}
    provider_metadata = item.get("metadata")
    if isinstance(provider_metadata, Mapping):
        metadata.update(dict(provider_metadata))
    elif provider_metadata is not None:
        metadata["provider_metadata"] = provider_metadata
    return NormalizedJob(
        title=str(item.get("title") or item.get("name") or item.get("jobTitle") or item.get("text") or "Untitled role").strip(),
        company=str(item.get("company") or item.get("employer") or item.get("company_name")
                    or item.get("companyName") or default_company or "").strip(),
        description=_sanitize_text(str(item.get("description") or item.get("content")
                                       or item.get("descriptionPlain") or item.get("summary")
                                       or item.get("jobDescription") or "No description provided")),
        description_url=description_url,
        application_url=application_url,
        canonical_url=_resolve_job_url(
            item.get("canonical_url") or item.get("absolute_url") or item.get("hostedUrl"),
            normalized_base,
            "canonical",
        ) or description_url,
        location=location,
        region=classify_region(location, item.get("region")).value,
        modality=_modality(item.get("modality") or item.get("workplace_type") or item.get("workplaceType") or item.get("remote")
                           or item.get("jobType") or item.get("location")),
        salary_min=salary_min, salary_max=salary_max,
        salary_currency=_currency(item.get("salary_currency") or item.get("currency")
                                  or item.get("salaryCurrency") or item.get("salary")),
        published_at=_date(item.get("published_at") or item.get("date_posted") or item.get("publication_date")
                           or item.get("created_at") or item.get("first_published") or item.get("createdAt")
                           or item.get("pubDate")),
        requirements=requirements,
        salary_period=str(item.get("salary_period") or item.get("pay_period")
                          or item.get("salaryPeriod") or "").strip().lower() or None,
        source=str(item.get("source") or source),
        metadata=metadata,
    )


def _content(config: SourceConfig, key: str) -> str:
    config.validate_terms_acceptance()
    settings = dict(config.settings)
    allow_network = settings.get("allow_network", False)
    if type(allow_network) is not bool:
        raise ValueError("allow_network must be a boolean")
    if key in settings:
        return str(settings[key])
    path = settings.get(f"{key}_path")
    if path:
        return Path(str(path)).read_text(encoding="utf-8")
    if not allow_network:
        raise RuntimeError(f"{config.name} requires an inline {key} fixture or allow_network=true")
    if not config.base_url:
        raise ValueError("base_url is required for network fetching")
    _robots_check(config.base_url, str(settings.get("user_agent", "JobScrapper/0.1")))
    user_agent = str(settings.get("user_agent", "JobScrapper/0.1"))
    last_error: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            _RATE_LIMITER.wait(config.name, config.requests_per_minute)
            request = urllib.request.Request(config.base_url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:  # noqa: S310 - explicit opt-in
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_error = exc
            if attempt < config.max_retries:
                time.sleep(min(2**attempt, 10.0))
    raise RuntimeError(f"source fetch failed after retries: {last_error}") from last_error


def _robots_check(url: str, user_agent: str) -> None:
    parsed = urlparse(url)
    robots = RobotFileParser(urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt"))
    robots.read()
    if not robots.can_fetch(user_agent, url):
        raise PermissionError(f"robots.txt disallows fetching {url}")


def _json_items(payload: Any) -> Any:
    """Extract the supported collection shapes used by JSON ATS feeds."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        return payload.get("jobs", payload.get("data", []))
    return []


def _is_legal_metadata(item: Mapping[str, Any]) -> bool:
    """Recognize a provider legal envelope without hiding malformed jobs."""
    if "legal" not in item:
        return False
    job_markers = {
        "title", "name", "text", "description", "content", "descriptionPlain",
        "url", "absolute_url", "hostedUrl", "applyUrl", "company", "company_name",
        "companyName", "location", "categories",
    }
    return not any(marker in item for marker in job_markers)


def _fetch_json_feed(config: SourceConfig, adapter_name: str, default_company: str | None = None) -> SourceFetchResult:
    """Decode and normalize JSON records while isolating malformed items."""
    try:
        config.validate_terms_acceptance()
        payload = json.loads(_content(config, "payload"))
        items = _json_items(payload)
        configured_company = config.settings.get("company")
        configured_company = str(configured_company).strip() if configured_company else None
        company_fallback = configured_company or default_company
        jobs: list[NormalizedJob] = []
        errors: list[str] = []
        for item in items:
            if not isinstance(item, Mapping):
                errors.append("invalid job: item must be an object with a description URL")
                continue
            if _is_legal_metadata(item):
                continue
            try:
                record = dict(item)
                jobs.append(_job(record, config.base_url, adapter_name, default_company=company_fallback))
            except Exception as exc:
                errors.append(f"invalid job: {exc}")
        return SourceFetchResult(jobs=tuple(jobs), error="; ".join(errors) if errors else None)
    except Exception as exc:  # source isolation is handled by the pipeline
        return SourceFetchResult(error=f"{type(exc).__name__}: {exc}")


class JsonApiFeedAdapter(SourceAdapter):
    """Adapter for a JSON API or feed returning a list under ``jobs``/``data``."""

    def __init__(self, adapter_name: str = "json-api-feed") -> None:
        self._name = adapter_name

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, config: SourceConfig) -> SourceFetchResult:
        return _fetch_json_feed(config, self.name)


class _CardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.cards: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._field: str | None = None
        self._anchor: dict[str, str] | None = None
        self._blocked = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: v or "" for k, v in attrs}
        if tag in {"script", "style", "noscript"}:
            self._blocked += 1
            return
        if self._blocked:
            return
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
        if self._blocked:
            return
        if self._current is not None and self._field:
            self._current[self._field] = (self._current.get(self._field, "") + " " + data).strip()
        if self._anchor is not None:
            self._anchor["text"] = (self._anchor.get("text", "") + " " + data).strip()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._blocked = max(0, self._blocked - 1)
            return
        if self._blocked:
            return
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
            settings = dict(config.settings)
            if "payload" in settings or settings.get("payload_path"):
                return _fetch_json_feed(config, self.name, self.company)
            parser = _CardParser()
            parser.feed(_content(config, "html"))
            jobs: list[NormalizedJob] = []
            errors: list[str] = []
            for card in parser.cards:
                if not card.get("url"):
                    errors.append("invalid job: job is missing a valid description URL")
                    continue
                try:
                    jobs.append(_job(
                        {**card, "description_url": card.get("url")},
                        config.base_url,
                        self.name,
                        default_company=self.company,
                    ))
                except Exception as exc:
                    errors.append(f"invalid job: {exc}")
            return SourceFetchResult(jobs=tuple(jobs), error="; ".join(errors) if errors else None)
        except Exception as exc:
            return SourceFetchResult(error=f"{type(exc).__name__}: {exc}")


class GreenhouseCareerPageAdapter(_CareerPageAdapter):
    def __init__(self) -> None:
        super().__init__("greenhouse-career-page", "Greenhouse employer")


class LeverCareerPageAdapter(_CareerPageAdapter):
    def __init__(self) -> None:
        super().__init__("lever-career-page", "Lever employer")


DEFAULT_ADAPTERS = (JsonApiFeedAdapter(), GreenhouseCareerPageAdapter(), LeverCareerPageAdapter())
