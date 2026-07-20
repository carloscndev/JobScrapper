"""Fixture-only tests for the initial job-source connectors.

These tests intentionally never contact a real job board.  Network behaviour
is verified with mocks so the suite can run offline and still enforce the
connector safety contract.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


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


if __name__ == "__main__":
    unittest.main()
