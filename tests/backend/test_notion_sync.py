"""Offline tests for NOTION-002 synchronization and HTTP resilience."""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.notion import NotionConfig  # noqa: E402
from app.notion_sync import NotionHttpClient, NotionRequestError, NotionSyncService, ReconciliationReport, job_properties  # noqa: E402


class QueueTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url, dict(headers), json.loads(body) if body else None))
        response = self.responses.pop(0)
        if callable(response):
            response = response(method, url, headers, body, timeout)
        return response


def config() -> NotionConfig:
    return NotionConfig(token_env="TEST_SYNC_TOKEN", database_id_env="TEST_SYNC_DB", api_version="2025-09-03", timeout_seconds=2)


def job(fingerprint="abc"):
    return SimpleNamespace(
        id=7, fingerprint=fingerprint, title="Backend Engineer", company="Acme", region="cdmx", modality="remote",
        location="CDMX", metadata_json={"requirements": "Python, SQL", "salary_period": "annual", "source": "greenhouse"},
        salary_min=50000, salary_max=70000, salary_currency="MXN", description_url="https://jobs.example/1",
        application_url="https://apply.example/1", canonical_url="https://jobs.example/1", published_at=date(2026, 1, 2),
        detected_at=datetime(2026, 1, 3), checked_at=datetime(2026, 1, 4), status="active",
    )


def evaluation():
    return SimpleNamespace(score=87.5, score_breakdown={"explanation": "Strong skills match"}, matches=["Python"], gaps=["AWS"], recommendations=["Review AWS basics"])


class NotionSyncTests(unittest.TestCase):
    def setUp(self):
        self.old = {key: os.environ.get(key) for key in ("TEST_SYNC_TOKEN", "TEST_SYNC_DB")}
        os.environ["TEST_SYNC_TOKEN"] = "secret-token"
        os.environ["TEST_SYNC_DB"] = "database-1"

    def tearDown(self):
        for key, value in self.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_property_mapping_includes_score_explanation_recommendations_links_and_status(self):
        props = job_properties(job(), evaluation())
        self.assertEqual(props["Compatibility score"], {"number": 87.5})
        self.assertIn("Strong skills match", str(props["Score explanation"]))
        self.assertIn("Review AWS basics", str(props["Recommendations"]))
        self.assertEqual(props["Description URL"]["url"], "https://jobs.example/1")
        self.assertEqual(props["Application URL"]["url"], "https://apply.example/1")
        self.assertEqual(props["Status"]["select"]["name"], "active")

    def test_headers_api_version_retry_after_and_rate_limit_are_enforced(self):
        transport = QueueTransport([(429, {"Retry-After": "0"}, b'{"message":"slow down"}'), (200, {}, b'{"ok":true}')])
        client = NotionHttpClient(config(), transport=transport, max_retries=1, backoff_seconds=9, min_interval_seconds=0)
        with patch("app.notion_sync.time.sleep") as sleep:
            self.assertEqual(client.request("GET", "/v1/users/me"), {"ok": True})
        self.assertEqual(len(transport.calls), 2)
        headers = transport.calls[0][2]
        self.assertEqual(headers["Authorization"], "Bearer secret-token")
        self.assertEqual(headers["Notion-Version"], "2025-09-03")
        self.assertIn(0.0, sleep.call_args_list[0].args)

    def test_query_all_follows_cursor(self):
        transport = QueueTransport([
            (200, {}, b'{"results":[{"id":"p1"}],"has_more":true,"next_cursor":"cursor-1"}'),
            (200, {}, b'{"results":[{"id":"p2"}],"has_more":false,"next_cursor":null}'),
        ])
        client = NotionHttpClient(config(), transport=transport, min_interval_seconds=0)
        self.assertEqual([p["id"] for p in client.query_all("database-1")], ["p1", "p2"])
        self.assertEqual(transport.calls[1][3]["start_cursor"], "cursor-1")

    def test_sync_is_idempotent_and_updates_existing_page(self):
        existing = {"id": "page-1", "properties": {"Fingerprint": {"rich_text": [{"plain_text": "abc"}]}}}
        transport = QueueTransport([
            (200, {}, json.dumps({"results": [existing], "has_more": False}).encode()),
            (200, {}, b'{"id":"page-1"}'),
            (200, {}, json.dumps({"results": [existing], "has_more": False}).encode()),
            (200, {}, b'{"id":"page-1"}'),
        ])
        service = NotionSyncService(NotionHttpClient(config(), transport=transport, min_interval_seconds=0))
        first, second = service.sync_job(job(), evaluation()), service.sync_job(job(), evaluation())
        self.assertEqual((first.state, second.state), ("synced", "synced"))
        self.assertEqual([call[0] for call in transport.calls], ["POST", "PATCH", "POST", "PATCH"])
        self.assertEqual(first.reconciliation["action"], "updated")
        self.assertEqual(first.external_id, second.external_id)

    def test_partial_failure_isolated_per_item(self):
        transport = QueueTransport([
            (500, {}, b'{"message":"temporary"}'),
            (200, {}, b'{"results":[],"has_more":false}'),
            (200, {}, b'{"id":"page-ok"}'),
        ])
        service = NotionSyncService(NotionHttpClient(config(), transport=transport, max_retries=0, min_interval_seconds=0))
        results = service.sync_jobs([(job("bad"), None), (job("good"), None)])
        self.assertEqual([result.state for result in results], ["failed", "synced"])
        self.assertEqual(results[1].page_id, "page-ok")
        self.assertEqual(results[0].attempts, 1)

    def test_non_retryable_error_is_reported(self):
        transport = QueueTransport([(400, {}, b'{"message":"invalid payload"}')])
        client = NotionHttpClient(config(), transport=transport, max_retries=2, min_interval_seconds=0)
        with self.assertRaises(NotionRequestError) as context:
            client.request("GET", "/v1/users/me")
        self.assertEqual(context.exception.status, 400)
        self.assertFalse(context.exception.retryable)
        self.assertEqual(len(transport.calls), 1)

    def test_outcome_sink_receives_success_and_failure_outcomes(self):
        sink = []
        transport = QueueTransport([
            (200, {}, b'{"results":[],"has_more":false}'),
            (200, {}, b'{"id":"page-ok"}'),
            (500, {}, b'{"message":"upstream unavailable"}'),
        ])
        client = NotionHttpClient(config(), transport=transport, max_retries=0, min_interval_seconds=0)
        service = NotionSyncService(client, outcome_sink=sink.append)
        success = service.sync_job(job("success"))
        failure = service.sync_job(job("failure"))
        self.assertEqual(success.state, "synced")
        self.assertEqual(failure.state, "failed")
        self.assertEqual([item.state for item in sink], ["synced", "failed"])
        self.assertEqual(sink[0].page_id, "page-ok")
        self.assertEqual(sink[1].external_id, "job:failure")

    def test_sync_outcome_records_actual_attempts_after_retry(self):
        transport = QueueTransport([
            (200, {}, b'{"results":[],"has_more":false}'),
            (429, {"Retry-After": "0"}, b'{"message":"rate limited"}'),
            (200, {}, b'{"id":"page-retried"}'),
        ])
        client = NotionHttpClient(config(), transport=transport, max_retries=1, min_interval_seconds=0)
        service = NotionSyncService(client)
        with patch("app.notion_sync.time.sleep"):
            outcome = service.sync_job(job("retry"))
        self.assertEqual(outcome.state, "synced")
        self.assertEqual(outcome.attempts, 2)
        self.assertEqual(outcome.reconciliation["retry_statuses"], [429])

    def test_failed_outcome_records_all_attempts_after_retry_exhaustion(self):
        transport = QueueTransport([
            (200, {}, b'{"results":[],"has_more":false}'),
            (503, {}, b'{"message":"unavailable"}'),
            (503, {}, b'{"message":"unavailable"}'),
        ])
        client = NotionHttpClient(config(), transport=transport, max_retries=1, min_interval_seconds=0)
        service = NotionSyncService(client)
        with patch("app.notion_sync.time.sleep"):
            outcome = service.sync_job(job("retry-failure"))
        self.assertEqual(outcome.state, "failed")
        self.assertEqual(outcome.attempts, 2)
        self.assertEqual(outcome.reconciliation["retry_statuses"], [503])

    def test_reconcile_reports_missing_stale_and_orphan_without_mutation(self):
        expected = job_properties(job("stale"), evaluation())
        stale_props = dict(expected)
        stale_props["Title"] = {"title": [{"plain_text": "Old title"}]}
        stale_page = {"id": "page-stale", "properties": stale_props}
        orphan_page = {"id": "page-orphan", "properties": {
            "Fingerprint": {"rich_text": [{"plain_text": "orphan-fp"}]},
            "Title": {"title": [{"plain_text": "Legacy listing"}]},
        }}
        untracked_page = {"id": "page-untracked", "properties": {
            "Title": {"title": [{"plain_text": "Untracked listing"}]},
        }}
        transport = QueueTransport([(200, {}, json.dumps({"results": [stale_page, orphan_page, untracked_page], "has_more": False}).encode())])
        service = NotionSyncService(NotionHttpClient(config(), transport=transport, min_interval_seconds=0))
        missing_job = job("missing")
        missing_job.id = 8
        report = service.reconcile([(missing_job, evaluation()), (job("stale"), evaluation())])
        self.assertEqual(report.state, "drift")
        kinds = {item["kind"] for item in report.differences}
        self.assertEqual(kinds, {"missing_in_notion", "stale_in_notion", "orphan_in_notion"})
        self.assertEqual(report.evidence["page_count"], 3)
        self.assertEqual(report.evidence["orphan_count"], 2)
        self.assertEqual([call[0] for call in transport.calls], ["POST"])

    def test_reconciliation_report_serializes_and_preserves_audit_state(self):
        report = ReconciliationReport("r-1", "2026-01-01T00:00:00+00:00", 1,
                                      [{"id": "d-1", "kind": "missing_in_notion", "retryable": True}],
                                      "drift", {"page_count": 0})
        payload = report.as_dict()
        self.assertEqual(payload["reconciliation_id"], "r-1")
        self.assertEqual(json.loads(json.dumps(payload)), payload)
        self.assertNotIn("token", json.dumps(payload).lower())

    def test_repair_retries_retryable_drift_and_skips_orphans(self):
        page = {"id": "page-stale", "properties": {"Fingerprint": {"rich_text": [{"plain_text": "stale"}]}}}
        transport = QueueTransport([
            (200, {}, json.dumps({"results": [page], "has_more": False}).encode()),
            (200, {}, b'{"id":"page-stale"}'),
        ])
        service = NotionSyncService(NotionHttpClient(config(), transport=transport, min_interval_seconds=0))
        report = ReconciliationReport("r-2", "2026-01-01T00:00:00+00:00", 2, [
            {"id": "d-stale", "external_id": "job:stale", "kind": "stale_in_notion", "retryable": True},
            {"id": "d-orphan", "external_id": "job:orphan-fp", "kind": "orphan_in_notion", "retryable": False},
        ], "drift", {"page_count": 2})
        repaired = service.repair(report, [(job("stale"), evaluation())])
        self.assertEqual(repaired.state, "repaired")
        attempts = repaired.evidence["repair_attempts"]
        self.assertEqual([item["state"] for item in attempts], ["repaired", "skipped"])
        self.assertEqual([call[0] for call in transport.calls], ["POST", "PATCH"])
        self.assertFalse(any(call[0] == "DELETE" for call in transport.calls))

    def test_repair_records_failed_retryable_drift_and_missing_local_job(self):
        transport = QueueTransport([
            (200, {}, json.dumps({"results": [], "has_more": False}).encode()),
            (500, {}, b'{"message":"temporary"}'),
        ])
        service = NotionSyncService(NotionHttpClient(config(), transport=transport, max_retries=0, min_interval_seconds=0))
        report = ReconciliationReport("r-3", "2026-01-01T00:00:00+00:00", 2, [
            {"id": "d-fail", "external_id": "job:fail", "kind": "missing_in_notion", "retryable": True},
            {"id": "d-absent", "external_id": "job:absent", "kind": "stale_in_notion", "retryable": True},
        ], "drift", {})
        repaired = service.repair(report, [(job("fail"), None)])
        self.assertEqual(repaired.state, "repair_failed")
        self.assertEqual(repaired.evidence["repair_attempts"][0]["state"], "failed")
        self.assertEqual(repaired.evidence["repair_attempts"][1]["error"], "local_job_not_found")


if __name__ == "__main__":
    unittest.main()
