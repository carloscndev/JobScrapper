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
from hashlib import sha256
from uuid import uuid4
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
            result = self.request("POST", f"/v1/databases/{database_id}/query", payload)
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


@dataclass
class ReconciliationReport:
    """A deterministic, serializable audit of SQLite versus Notion.

    The report intentionally contains values for changed properties only and
    never credentials.  It can therefore be persisted in ``NotionSync`` and
    replayed by a repair worker without requiring the original query result.
    """

    reconciliation_id: str
    generated_at: str
    checked: int
    differences: list[dict[str, Any]] = field(default_factory=list)
    state: str = "clean"
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "reconciliation_id": self.reconciliation_id,
            "generated_at": self.generated_at,
            "checked": self.checked,
            "differences": self.differences,
            "state": self.state,
            "evidence": self.evidence,
        }


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
                result = self.client.request("POST", "/v1/pages", {"parent": {"database_id": database_id}, "properties": properties})
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

    @staticmethod
    def _property_value(prop: Mapping[str, Any] | None) -> Any:
        """Extract a comparable scalar from a Notion property payload."""
        if not isinstance(prop, Mapping):
            return None
        kind = next((item for item in ("title", "rich_text", "select", "url", "number", "date") if item in prop), None)
        value = prop.get(kind) if kind else None
        if kind in {"title", "rich_text"}:
            return "".join(item.get("plain_text") or item.get("text", {}).get("content", "") for item in (value or []) if isinstance(item, Mapping))
        if kind == "select":
            return value.get("name") if isinstance(value, Mapping) else None
        if kind == "date":
            return value.get("start") if isinstance(value, Mapping) else None
        return value

    @classmethod
    def _comparable_properties(cls, properties: Mapping[str, Any]) -> dict[str, Any]:
        return {name: cls._property_value(prop) for name, prop in properties.items()}

    @staticmethod
    def _expected_properties(job: object, evaluation: object | None) -> dict[str, Any]:
        values = job_properties(job, evaluation)
        return {name: NotionSyncService._property_value(prop) for name, prop in values.items()}

    def reconcile(self, items: list[tuple[object, object | None]]) -> ReconciliationReport:
        """Compare local jobs with one Notion query, without mutating Notion.

        Missing/stale local pages are retryable by :meth:`repair`; pages that
        have no local fingerprint are reported as auditable orphans and are
        never deleted automatically.
        """
        database_id = self.database_id or self.client.config.require_credentials()[1]
        pages = self.client.query_all(database_id)
        by_key: dict[str, Mapping[str, Any]] = {}
        for page in pages:
            if not isinstance(page, Mapping):
                continue
            props = page.get("properties") or {}
            fingerprint = _page_key(page, "Fingerprint")
            local_id = _page_key(page, "Local job ID")
            if fingerprint:
                by_key[f"fingerprint:{fingerprint}"] = page
            if local_id:
                by_key[f"id:{local_id}"] = page

        report = ReconciliationReport(str(uuid4()), datetime.now(timezone.utc).isoformat(), len(items))
        matched_page_ids: set[str] = set()
        for job, evaluation in items:
            fingerprint = str(_get(job, "fingerprint") or _get(job, "canonical_url") or _get(job, "id"))
            local_id = str(_get(job, "id")) if _get(job, "id") is not None else ""
            page = by_key.get(f"fingerprint:{fingerprint}") or (by_key.get(f"id:{local_id}") if local_id else None)
            external_id = f"job:{fingerprint}"
            if page is None:
                report.differences.append({"id": sha256(f"missing:{external_id}".encode()).hexdigest()[:16], "external_id": external_id, "kind": "missing_in_notion", "retryable": True, "fields": list(self._expected_properties(job, evaluation)), "expected": self._expected_properties(job, evaluation), "actual": None})
                continue
            matched_page_ids.add(str(page.get("id")))
            expected = self._expected_properties(job, evaluation)
            actual = self._comparable_properties(page.get("properties") or {})
            fields = [name for name, value in expected.items() if value != actual.get(name)]
            if fields:
                report.differences.append({"id": sha256(f"stale:{external_id}".encode()).hexdigest()[:16], "external_id": external_id, "kind": "stale_in_notion", "retryable": True, "fields": fields, "expected": {name: expected[name] for name in fields}, "actual": {name: actual.get(name) for name in fields}})

        local_external_ids = {f"job:{str(_get(job, 'fingerprint') or _get(job, 'canonical_url') or _get(job, 'id'))}" for job, _ in items}
        for page in pages:
            fingerprint = _page_key(page, "Fingerprint")
            page_id = str(page.get("id") or "")
            if fingerprint and (f"job:{fingerprint}" in local_external_ids or page_id in matched_page_ids):
                continue
            # A page without the stable property is still auditable.  It is
            # deliberately non-retryable: repairing it would require guessing
            # its local owner, while deleting/archiving it would be destructive.
            identity = page_id or sha256(json.dumps(page, sort_keys=True, default=str).encode()).hexdigest()[:16]
            external_id = f"page:{identity}"
            report.differences.append({"id": sha256(f"orphan:{external_id}".encode()).hexdigest()[:16], "external_id": external_id, "kind": "orphan_in_notion", "retryable": False, "fields": [], "expected": None, "actual": self._comparable_properties(page.get("properties") or {})})
        report.state = "drift" if report.differences else "clean"
        report.evidence = {"page_count": len(pages), "retryable_count": sum(1 for diff in report.differences if diff["retryable"]), "orphan_count": sum(1 for diff in report.differences if diff["kind"] == "orphan_in_notion")}
        return report

    # Explicit plural aliases keep the worker API parallel with ``sync_jobs``
    # and make the operation discoverable to scheduled pipeline callers.
    def reconcile_jobs(self, items: list[tuple[object, object | None]]) -> ReconciliationReport:
        return self.reconcile(items)

    def repair(self, report: ReconciliationReport | Mapping[str, Any], items: list[tuple[object, object | None]]) -> ReconciliationReport:
        """Retry repairable drift and append per-item evidence to the report."""
        data = report.as_dict() if isinstance(report, ReconciliationReport) else dict(report)
        by_external = {f"job:{str(_get(job, 'fingerprint') or _get(job, 'canonical_url') or _get(job, 'id'))}": (job, evaluation) for job, evaluation in items}
        attempts: list[dict[str, Any]] = []
        for difference in data.get("differences", []):
            if not difference.get("retryable"):
                attempts.append({"difference_id": difference.get("id"), "state": "skipped", "reason": "not_retryable"})
                continue
            item = by_external.get(difference.get("external_id"))
            if item is None:
                attempts.append({"difference_id": difference.get("id"), "state": "failed", "error": "local_job_not_found", "retryable": False})
                continue
            outcome = self.sync_job(*item)
            attempts.append({"difference_id": difference.get("id"), "state": "repaired" if outcome.state == "synced" else "failed", "retryable": outcome.state != "synced", "external_id": outcome.external_id, "page_id": outcome.page_id, "attempts": outcome.attempts, "error": outcome.error})
        data["evidence"] = {**(data.get("evidence") or {}), "repair_attempts": attempts}
        data["state"] = "repaired" if attempts and all(item["state"] in {"repaired", "skipped"} for item in attempts) else ("repair_failed" if attempts else data.get("state", "clean"))
        return ReconciliationReport(data.get("reconciliation_id", str(uuid4())), data.get("generated_at", datetime.now(timezone.utc).isoformat()), int(data.get("checked", 0)), list(data.get("differences", [])), data["state"], data["evidence"])

    def repair_jobs(self, report: ReconciliationReport | Mapping[str, Any], items: list[tuple[object, object | None]]) -> ReconciliationReport:
        return self.repair(report, items)
