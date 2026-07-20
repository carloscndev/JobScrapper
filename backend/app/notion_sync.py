"""Idempotent, offline-testable synchronization of evaluated jobs to Notion.

The client deliberately has no import-time network side effects.  A transport
can be injected by tests; the default transport uses ``urllib`` and reads the
credential only when a request is made.  The service mirrors one SQLite job to
one Notion page identified by ``job:<fingerprint>`` and records per-item
outcomes so a failed page never aborts the rest of a batch.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol

from .notion import NotionConfig


class NotionTransport(Protocol):
    def __call__(self, method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: float) -> tuple[int, Mapping[str, str], bytes]: ...


def _default_transport(method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: float) -> tuple[int, Mapping[str, str], bytes]:
    request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is configuration, not user input
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


class NotionRequestError(RuntimeError):
    def __init__(self, status: int, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.status, self.retryable = status, retryable


class NotionHttpClient:
    """Small REST client with Retry-After aware exponential backoff."""

    def __init__(self, config: NotionConfig | None = None, *, transport: NotionTransport | None = None, max_retries: int = 3, backoff_seconds: float = 0.5, min_interval_seconds: float = 1 / 3) -> None:
        if max_retries < 0 or backoff_seconds < 0 or min_interval_seconds < 0:
            raise ValueError("retry and rate-limit values must be non-negative")
        self.config = config or NotionConfig()
        self.transport = transport or _default_transport
        self.max_retries, self.backoff_seconds, self.min_interval_seconds = max_retries, backoff_seconds, min_interval_seconds
        self._last_request = 0.0
        # Exposed for durable reconciliation metadata; reset on every request.
        self.last_attempts = 0
        self.last_retry_statuses: list[int] = []

    def request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        token, _ = self.config.require_credentials()
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {token}", "Notion-Version": self.config.api_version, "Content-Type": "application/json"}
        url = "https://api.notion.com" + (path if path.startswith("/") else "/" + path)
        self.last_attempts, self.last_retry_statuses = 0, []
        for attempt in range(self.max_retries + 1):
            wait = self.min_interval_seconds - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            self.last_attempts += 1
            status, response_headers, raw = self.transport(method, url, headers, body, self.config.timeout_seconds)
            try:
                data = json.loads(raw.decode() or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                data = {"message": raw.decode(errors="replace")}
            if 200 <= status < 300:
                return data
            retryable = status == 429 or status in {500, 502, 503, 504}
            if retryable and attempt < self.max_retries:
                self.last_retry_statuses.append(status)
                retry_after = response_headers.get("Retry-After") or response_headers.get("retry-after")
                try:
                    delay = max(0.0, float(retry_after)) if retry_after else self.backoff_seconds * (2 ** attempt)
                except ValueError:
                    delay = self.backoff_seconds * (2 ** attempt)
                time.sleep(delay)
                continue
            message = str(data.get("message") or data.get("code") or f"Notion request failed ({status})")
            raise NotionRequestError(status, message, retryable=retryable)
        raise AssertionError("unreachable")

    def query_all(self, database_id: str) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            result = self.request("POST", f"/v1/data_sources/{database_id}/query", payload)
            pages.extend(result.get("results", []))
            if not result.get("has_more"):
                return pages
            cursor = result.get("next_cursor")
            if not cursor:
                return pages


def _get(obj: object, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, Mapping) else getattr(obj, key, default)


def _rich(value: Any, limit: int = 2000) -> list[dict[str, Any]]:
    text = ", ".join(map(str, value)) if isinstance(value, (list, tuple, set)) else str(value or "")
    return [{"type": "text", "text": {"content": text[:limit]}}] if text else []


def _prop(kind: str, value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {kind: [] if kind in {"title", "rich_text"} else None}
    if kind == "title" or kind == "rich_text":
        return {kind: _rich(value)}
    if kind == "select":
        return {kind: {"name": str(value)}}
    if kind == "url":
        return {kind: str(value)[:2000]}
    if kind == "number":
        return {kind: float(value)}
    if kind == "date":
        return {kind: {"start": value.isoformat() if hasattr(value, "isoformat") else str(value)}}
    return {kind: value}


def job_properties(job: object, evaluation: object | None = None) -> dict[str, Any]:
    """Map normalized job/evaluation fields to the configured Notion schema."""
    get = lambda key, default=None: _get(job, key, default)
    ev = lambda key, default=None: _get(evaluation, key, default)
    breakdown = ev("score_breakdown", {}) or {}
    explanation = breakdown.get("explanation") or ev("explanation", "")
    return {
        "Title": _prop("title", get("title")), "Company": _prop("rich_text", get("company")),
        "Region": _prop("select", get("region", "other")), "Modality": _prop("select", get("modality", "unknown")),
        "Location": _prop("rich_text", get("location")), "Requirements": _prop("rich_text", get("metadata_json", {}).get("requirements", "")),
        "Salary min": _prop("number", get("salary_min")), "Salary max": _prop("number", get("salary_max")),
        "Salary currency": _prop("select", get("salary_currency")), "Salary period": _prop("select", get("metadata_json", {}).get("salary_period")),
        "Source": _prop("rich_text", get("metadata_json", {}).get("source")), "Description URL": _prop("url", get("description_url")),
        "Application URL": _prop("url", get("application_url")), "Canonical URL": _prop("url", get("canonical_url")),
        "Published": _prop("date", get("published_at")), "Detected": _prop("date", get("detected_at")), "Checked": _prop("date", get("checked_at")),
        "Compatibility score": _prop("number", ev("score")), "Score explanation": _prop("rich_text", explanation),
        "Matches": _prop("rich_text", ev("matches", [])), "Gaps": _prop("rich_text", ev("gaps", [])),
        "Recommendations": _prop("rich_text", ev("recommendations", [])), "Status": _prop("select", get("status", "active")),
        "Local job ID": _prop("rich_text", str(get("id")) if get("id") is not None else None), "Fingerprint": _prop("rich_text", get("fingerprint")),
    }


def _page_key(page: Mapping[str, Any], name: str) -> str:
    prop = (page.get("properties") or {}).get(name) or {}
    values = prop.get("rich_text") or prop.get("title") or []
    return "".join(item.get("plain_text") or item.get("text", {}).get("content", "") for item in values)


@dataclass
class SyncOutcome:
    external_id: str
    state: str
    page_id: str | None = None
    error: str | None = None
    attempts: int = 0
    reconciliation: dict[str, Any] = field(default_factory=dict)


class NotionSyncService:
    def __init__(self, client: NotionHttpClient, *, database_id: str | None = None, sync_repository: Any | None = None, outcome_sink: Callable[[SyncOutcome], None] | None = None) -> None:
        self.client, self.database_id = client, database_id
        self.sync_repository, self.outcome_sink = sync_repository, outcome_sink

    def _persist(self, job: object, outcome: SyncOutcome) -> None:
        """Persist a local NotionSync row without making persistence fatal.

        The repository is intentionally duck-typed so the sync worker remains
        usable in offline tests and with a queue-backed persistence adapter.
        """
        if self.outcome_sink is not None:
            self.outcome_sink(outcome)
        if self.sync_repository is None or _get(job, "id") is None:
            return
        try:
            from .models import NotionSync
            now = datetime.now(timezone.utc)
            self.sync_repository.upsert(NotionSync(job_id=int(_get(job, "id")), external_id=outcome.external_id, state=outcome.state, attempts=outcome.attempts, last_error=outcome.error, reconciliation=outcome.reconciliation, synced_at=now if outcome.state == "synced" else None))
        except Exception:
            # A page result remains available to the caller even if the local
            # audit write fails; the next scheduled run can reconcile it.
            return

    def sync_job(self, job: object, evaluation: object | None = None) -> SyncOutcome:
        fingerprint = str(_get(job, "fingerprint") or _get(job, "canonical_url") or _get(job, "id"))
        external_id = f"job:{fingerprint}"
        try:
            database_id = self.database_id or self.client.config.require_credentials()[1]
            pages = self.client.query_all(database_id)
            page = next((item for item in pages if _page_key(item, "Fingerprint") == fingerprint or _page_key(item, "Local job ID") == str(_get(job, "id"))), None)
            properties = job_properties(job, evaluation)
            if page:
                result = self.client.request("PATCH", f"/v1/pages/{page['id']}", {"properties": properties})
                page_id = result.get("id", page["id"])
                action = "updated"
            else:
                result = self.client.request("POST", "/v1/pages", {"parent": {"data_source_id": database_id}, "properties": properties})
                page_id, action = result.get("id"), "created"
            outcome = SyncOutcome(external_id, "synced", page_id, attempts=self.client.last_attempts, reconciliation={"action": action, "fingerprint": fingerprint, "retry_statuses": list(self.client.last_retry_statuses)})
            self._persist(job, outcome)
            return outcome
        except Exception as exc:  # isolate one job from a batch
            outcome = SyncOutcome(external_id, "failed", error=str(exc)[:500], attempts=self.client.last_attempts, reconciliation={"fingerprint": fingerprint, "retry_statuses": list(self.client.last_retry_statuses)})
            self._persist(job, outcome)
            return outcome

    def sync_jobs(self, items: list[tuple[object, object | None]]) -> list[SyncOutcome]:
        return [self.sync_job(job, evaluation) for job, evaluation in items]
