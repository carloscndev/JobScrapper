"""Fixture-only tests for the initial job-source connectors.

These tests intentionally never contact a real job board.  Network behaviour
is verified with mocks so the suite can run offline and still enforce the
connector safety contract.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _modules():
    from app import connectors
    from app.sources import SourceConfig, SourceKind, WorkModality

    return connectors, SourceConfig, SourceKind, WorkModality


class _Response:
    def __init__(self, body: str) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body.encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


@unittest.skipUnless(_available("sqlalchemy"), "SQLAlchemy is required for connector runtime tests")
class ConnectorFixtureTests(unittest.TestCase):
    def test_job_resolves_relative_links_with_or_without_trailing_slash(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        payload = {
            "jobs": [{
                "title": "Backend Engineer",
                "company": "Acme",
                "description": "Build APIs",
                "url": "roles/backend",
                "apply_url": "roles/backend/apply",
            }]
        }

        for base_url in ("https://jobs.example/careers", "https://jobs.example/careers/"):
            config = SourceConfig(
                name="relative-links",
                base_url=base_url,
                terms_accepted=True,
                settings={"payload": json.dumps(payload)},
            )
            result = connectors.JsonApiFeedAdapter().fetch(config)

            self.assertEqual(result.status, "success")
            self.assertEqual(result.jobs[0].description_url, "https://jobs.example/careers/roles/backend")
            self.assertEqual(result.jobs[0].application_url, "https://jobs.example/careers/roles/backend/apply")

    def test_job_keeps_supplied_description_application_and_canonical_urls_distinct(self) -> None:
        connectors, _SourceConfig, _SourceKind, _WorkModality = _modules()

        job = connectors._job(
            {
                "title": "Platform Engineer",
                "company": "Acme",
                "description": "Operate distributed systems",
                "description_url": "roles/platform",
                "application_url": "https://apply.example/platform",
                "canonical_url": "roles/platform?source=feed",
            },
            "https://jobs.example/careers",
            "fixture",
        )

        self.assertEqual(job.description_url, "https://jobs.example/careers/roles/platform")
        self.assertEqual(job.application_url, "https://apply.example/platform")
        self.assertEqual(job.canonical_url, "https://jobs.example/careers/roles/platform?source=feed")
        self.assertNotEqual(job.description_url, job.application_url)

    def test_json_feed_fixture_normalizes_fields_and_both_urls(self) -> None:
        connectors, SourceConfig, SourceKind, WorkModality = _modules()
        config = SourceConfig(
            name="jobs-json",
            kind=SourceKind.FEED,
            base_url="https://jobs.example/",
            terms_accepted=True,
            settings={
                "payload": '{"jobs": [{"title": "Backend Engineer", "employer": "Acme", '
                '"description": "Build APIs", "url": "/jobs/42", "apply_url": "/apply/42", '
                '"location": "CDMX", "region": "cdmx", "modality": "Hybrid", '
                '"salary_min": 50000, "salary_max": 70000, "currency": "MXN", '
                '"date_posted": "2026-07-18"}]}'
            },
        )

        result = connectors.JsonApiFeedAdapter().fetch(config)

        self.assertIsNone(result.error)
        self.assertEqual(len(result.jobs), 1)
        job = result.jobs[0]
        self.assertEqual(job.title, "Backend Engineer")
        self.assertEqual(job.company, "Acme")
        self.assertEqual(job.description_url, "https://jobs.example/jobs/42")
        self.assertEqual(job.application_url, "https://jobs.example/apply/42")
        self.assertEqual(job.location, "CDMX")
        self.assertEqual(job.region, "cdmx")
        self.assertEqual(job.modality, WorkModality.HYBRID)
        self.assertEqual(job.salary_currency, "MXN")

    def test_greenhouse_fixture_produces_normalized_job(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        html = (
            '<article class="job-card">'
            '<h2 class="title">Platform Engineer</h2>'
            '<p class="description">Own distributed systems.</p>'
            '<span class="location">New York, USA</span>'
            '<a href="/roles/platform">Description</a>'
            '<a class="apply" href="/roles/platform/apply">Apply</a>'
            '</article>'
        )
        config = SourceConfig(name="greenhouse", base_url="https://boards.example", terms_accepted=True, settings={"html": html})

        result = connectors.GreenhouseCareerPageAdapter().fetch(config)

        self.assertIsNone(result.error)
        self.assertEqual(len(result.jobs), 1)
        job = result.jobs[0]
        self.assertEqual(job.company, "Greenhouse employer")
        self.assertEqual(job.title, "Platform Engineer")
        self.assertEqual(job.description_url, "https://boards.example/roles/platform")
        self.assertEqual(job.application_url, "https://boards.example/roles/platform/apply")
        self.assertEqual(job.location, "New York, USA")
        self.assertEqual(job.metadata["source_adapter"], "greenhouse-career-page")

    def test_lever_fixture_classifies_remote_modality_and_links(self) -> None:
        connectors, SourceConfig, _SourceKind, WorkModality = _modules()
        html = (
            '<article data-job="true">'
            '<div data-field="title">Data Engineer</div>'
            '<div data-field="description">Build pipelines.</div>'
            '<div data-field="location">Remote - United States</div>'
            '<a href="https://jobs.example/data">Details</a>'
            '<a data-field="application_url" href="https://apply.example/data">Apply</a>'
            '</article>'
        )
        config = SourceConfig(name="lever", base_url="https://jobs.example", terms_accepted=True, settings={"html": html})

        result = connectors.LeverCareerPageAdapter().fetch(config)

        self.assertIsNone(result.error)
        self.assertEqual(len(result.jobs), 1)
        job = result.jobs[0]
        self.assertEqual(job.company, "Lever employer")
        self.assertEqual(job.modality, WorkModality.REMOTE)
        self.assertEqual(job.description_url, "https://jobs.example/data")
        self.assertEqual(job.application_url, "https://apply.example/data")

    def test_network_is_opt_in_and_does_not_call_urlopen_for_fixture(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        config = SourceConfig(name="offline", base_url="https://jobs.example", terms_accepted=True, settings={})
        with patch.object(connectors.urllib.request, "urlopen") as urlopen:
            result = connectors.JsonApiFeedAdapter().fetch(config)
        self.assertIsNotNone(result.error)
        self.assertIn("requires an inline payload fixture", result.error or "")
        urlopen.assert_not_called()

    def test_network_fetch_checks_robots_and_sends_identifiable_user_agent(self) -> None:
        connectors, SourceConfig, SourceKind, _WorkModality = _modules()
        config = SourceConfig(
            name="network-enabled",
            kind=SourceKind.API,
            base_url="https://jobs.example/feed",
            terms_accepted=True,
            settings={"allow_network": True, "user_agent": "JobScrapperTest/1.0"},
        )
        response = _Response('{"data": [{"title": "SRE", "company": "Acme", "description": "Operate", "url": "/sre"}]}')
        with patch.object(connectors, "_robots_check") as robots_check, patch.object(
            connectors.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            result = connectors.JsonApiFeedAdapter().fetch(config)

        self.assertIsNone(result.error)
        robots_check.assert_called_once_with("https://jobs.example/feed", "JobScrapperTest/1.0")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), "JobScrapperTest/1.0")

    def test_one_malformed_source_returns_error_while_other_source_succeeds(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        bad = SourceConfig(name="bad", terms_accepted=True, settings={"payload": "not-json"})
        good = SourceConfig(
            name="good",
            base_url="https://jobs.example",
            terms_accepted=True,
            settings={"payload": '[{"title": "QA", "company": "Acme", "description": "Test", "url": "/qa"}]'},
        )

        failed = connectors.JsonApiFeedAdapter("bad-adapter").fetch(bad)
        succeeded = connectors.JsonApiFeedAdapter("good-adapter").fetch(good)

        self.assertEqual(failed.status, "failed")
        self.assertTrue(failed.error)
        self.assertEqual(succeeded.status, "success")
        self.assertEqual(succeeded.jobs[0].title, "QA")

    def test_fetch_rejects_source_without_terms_acceptance(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        config = SourceConfig(
            name="unreviewed",
            base_url="https://jobs.example",
            settings={"payload": '[{"title": "QA", "company": "Acme", "description": "Test", "url": "/qa"}]'},
        )

        result = connectors.JsonApiFeedAdapter().fetch(config)

        self.assertEqual(result.status, "failed")
        self.assertIn("terms_accepted=True", result.error or "")

    def test_network_fetch_applies_rate_limit_and_retries_with_backoff(self) -> None:
        connectors, SourceConfig, SourceKind, _WorkModality = _modules()
        config = SourceConfig(
            name="retry-source", kind=SourceKind.API, base_url="https://jobs.example/feed",
            terms_accepted=True, requests_per_minute=12, max_retries=1,
            settings={"allow_network": True},
        )
        response = _Response(json.dumps({"data": [{"title": "SRE", "company": "Acme", "description": "Operate", "url": "/sre"}]}))
        with patch.object(connectors, "_robots_check"), patch.object(connectors._RATE_LIMITER, "wait") as wait, patch.object(
            connectors.urllib.request, "urlopen", side_effect=[URLError("temporary"), response]
        ) as urlopen, patch.object(connectors.time, "sleep") as sleep:
            result = connectors.JsonApiFeedAdapter().fetch(config)

        self.assertEqual(result.status, "success")
        self.assertEqual(urlopen.call_count, 2)
        wait.assert_has_calls([call("retry-source", 12), call("retry-source", 12)])
        sleep.assert_called_once_with(1.0)

    def test_json_description_sanitizes_script_style_and_noscript_content(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        payload = {"jobs": [{
            "title": "Safe", "company": "Acme",
            "description": "Build <script>alert(1)</script><style>.x{}</style><noscript>hidden</noscript> APIs",
            "url": "https://jobs.example/safe",
        }]}
        result = connectors.JsonApiFeedAdapter().fetch(SourceConfig(name="sanitize", terms_accepted=True, settings={"payload": json.dumps(payload)}))
        self.assertEqual(result.status, "success")
        description = result.jobs[0].description
        self.assertEqual(description, "Build APIs")
        for marker in ("script", "alert", "style", "noscript", "hidden"):
            self.assertNotIn(marker, description.lower())

    def test_invalid_item_isolated_while_valid_item_is_retained(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        payload = {"jobs": [
            {"title": "Broken", "company": "Acme", "description": "No valid URL", "url": "javascript:alert(1)"},
            {"title": "Valid", "company": "Acme", "description": "Works", "url": "/valid"},
        ]}
        result = connectors.JsonApiFeedAdapter().fetch(SourceConfig(name="isolated", base_url="https://jobs.example", terms_accepted=True, settings={"payload": json.dumps(payload)}))
        self.assertEqual(result.status, "partial")
        self.assertEqual([job.title for job in result.jobs], ["Valid"])
        self.assertIn("invalid job", result.error or "")

    def test_invalid_description_url_is_rejected(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        payload = {"jobs": [{"title": "Broken", "company": "Acme", "description": "Bad", "url": "javascript:alert(1)"}]}
        result = connectors.JsonApiFeedAdapter().fetch(SourceConfig(name="url-check", terms_accepted=True, settings={"payload": json.dumps(payload)}))
        self.assertEqual(result.status, "failed")
        self.assertIn("invalid job", result.error or "")

    def test_json_fixture_reports_missing_invalid_and_canonical_links_per_item(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        payload = {"jobs": [
            {
                "title": "Missing description",
                "company": "Acme",
                "description": "No details link",
                "application_url": "/apply/missing",
            },
            {
                "title": "Invalid application",
                "company": "Acme",
                "description": "Bad apply link",
                "url": "/roles/invalid-application",
                "application_url": "javascript:alert(1)",
            },
            {
                "title": "Invalid canonical",
                "company": "Acme",
                "description": "Bad canonical link",
                "url": "/roles/invalid-canonical",
                "canonical_url": "mailto:jobs@example.com",
            },
            {
                "title": "Valid",
                "company": "Acme",
                "description": "Works",
                "url": "/roles/valid",
            },
        ]}
        config = SourceConfig(
            name="json-link-errors",
            base_url="https://jobs.example",
            terms_accepted=True,
            settings={"payload": json.dumps(payload)},
        )

        result = connectors.JsonApiFeedAdapter().fetch(config)

        self.assertEqual(result.status, "partial")
        self.assertEqual([job.title for job in result.jobs], ["Valid"])
        self.assertIn("missing a valid description URL", result.error or "")
        self.assertIn("invalid application URL", result.error or "")
        self.assertIn("invalid canonical URL", result.error or "")

    def test_json_fixture_rejects_malformed_raw_http_links_by_field(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        payload = {"jobs": [
            {
                "title": "Malformed description scheme",
                "company": "Acme",
                "description": "Bad description link",
                "url": "https:",
            },
            {
                "title": "Malformed description authority",
                "company": "Acme",
                "description": "Bad description link",
                "url": "https://",
            },
            {
                "title": "Malformed application scheme",
                "company": "Acme",
                "description": "Valid details link",
                "url": "/roles/malformed-application-scheme",
                "application_url": "//",
            },
            {
                "title": "Malformed application query",
                "company": "Acme",
                "description": "Valid details link",
                "url": "/roles/malformed-application-query",
                "application_url": "https://?foo",
            },
            {
                "title": "Malformed canonical authority",
                "company": "Acme",
                "description": "Valid details link",
                "url": "/roles/malformed-canonical",
                "canonical_url": "https://:bad",
            },
            {
                "title": "Valid",
                "company": "Acme",
                "description": "Works",
                "url": "/roles/valid-malformed-neighbors",
            },
        ]}
        config = SourceConfig(
            name="raw-url-errors",
            base_url="https://jobs.example",
            terms_accepted=True,
            settings={"payload": json.dumps(payload)},
        )

        result = connectors.JsonApiFeedAdapter().fetch(config)

        self.assertEqual(result.status, "partial")
        self.assertEqual([job.title for job in result.jobs], ["Valid"])
        self.assertIn("invalid description URL", result.error or "")
        self.assertIn("invalid application URL", result.error or "")
        self.assertIn("invalid canonical URL", result.error or "")

    def test_career_fixture_reports_missing_and_invalid_links_without_dropping_valid_card(self) -> None:
        connectors, SourceConfig, _SourceKind, _WorkModality = _modules()
        html = (
            '<article class="job-card">'
            '<h2 class="title">Missing details</h2>'
            '<p class="description">No posting link.</p>'
            '<a class="apply" href="/apply/missing">Apply</a>'
            '</article>'
            '<article class="job-card">'
            '<h2 class="title">Invalid details</h2>'
            '<p class="description">Unsafe posting link.</p>'
            '<a href="javascript:alert(1)">Details</a>'
            '</article>'
            '<article class="job-card">'
            '<h2 class="title">Invalid application</h2>'
            '<p class="description">Unsafe application link.</p>'
            '<a href="/roles/invalid-application">Details</a>'
            '<a class="apply" href="javascript:alert(1)">Apply</a>'
            '</article>'
            '<article class="job-card">'
            '<h2 class="title">Valid</h2>'
            '<p class="description">Works.</p>'
            '<a href="/roles/valid">Details</a>'
            '</article>'
        )
        config = SourceConfig(
            name="career-link-errors",
            base_url="https://jobs.example/careers/",
            terms_accepted=True,
            settings={"html": html},
        )

        result = connectors.GreenhouseCareerPageAdapter().fetch(config)

        self.assertEqual(result.status, "partial")
        self.assertEqual([job.title for job in result.jobs], ["Valid"])
        self.assertIn("missing a valid description URL", result.error or "")
        self.assertIn("invalid description URL", result.error or "")
        self.assertIn("invalid application URL", result.error or "")


if __name__ == "__main__":
    unittest.main()
