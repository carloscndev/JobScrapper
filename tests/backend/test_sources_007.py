"""SOURCES-007 regression tests for Greenhouse and Lever JSON feeds."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is required for connector runtime tests")
class Sources007ConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        from app import connectors
        from app.sources import SourceConfig

        self.connectors = connectors
        self.SourceConfig = SourceConfig

    def test_greenhouse_jobs_payload_normalizes_nested_record_and_absolute_url(self) -> None:
        payload = {
            "jobs": [
                {
                    "title": "Platform Engineer",
                    "company_name": "Acme",
                    "content": "<p>Build reliable APIs.</p>",
                    "location": {"name": "Ciudad de México"},
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
                    "first_published": "2026-07-31",
                }
            ]
        }
        config = self.SourceConfig(
            name="greenhouse-acme",
            base_url="https://boards.greenhouse.io/acme",
            terms_accepted=True,
            settings={"payload": json.dumps(payload)},
        )

        result = self.connectors.GreenhouseCareerPageAdapter().fetch(config)

        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.jobs), 1)
        job = result.jobs[0]
        self.assertEqual(job.title, "Platform Engineer")
        self.assertEqual(job.company, "Acme")
        self.assertEqual(job.description, "Build reliable APIs.")
        self.assertEqual(job.location, "Ciudad de México")
        self.assertEqual(job.published_at, date(2026, 7, 31))
        self.assertEqual(job.description_url, "https://boards.greenhouse.io/acme/jobs/101")
        self.assertIsNone(job.application_url)
        self.assertEqual(job.canonical_url, job.description_url)

    def test_lever_list_payload_normalizes_nested_location_date_and_distinct_urls(self) -> None:
        payload = [
            {
                "text": "Data Engineer",
                "descriptionPlain": "<p>Process distributed data.</p>",
                "categories": {"location": "Remote - United States"},
                "hostedUrl": "https://jobs.lever.co/acme/abc123",
                "applyUrl": "https://jobs.lever.co/acme/abc123/apply",
                "workplaceType": "remote",
                "createdAt": 1893499200000,
            }
        ]
        config = self.SourceConfig(
            name="lever-acme",
            base_url="https://jobs.lever.co/acme",
            terms_accepted=True,
            settings={"payload": json.dumps(payload)},
        )

        result = self.connectors.LeverCareerPageAdapter().fetch(config)

        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.jobs), 1)
        job = result.jobs[0]
        self.assertEqual(job.title, "Data Engineer")
        self.assertEqual(job.company, "Lever employer")
        self.assertEqual(job.description, "Process distributed data.")
        self.assertEqual(job.location, "Remote - United States")
        self.assertEqual(job.published_at, date(2030, 1, 1))
        self.assertEqual(job.description_url, "https://jobs.lever.co/acme/abc123")
        self.assertEqual(job.application_url, "https://jobs.lever.co/acme/abc123/apply")
        self.assertNotEqual(job.description_url, job.application_url)

    def test_malformed_ats_links_are_rejected_without_example_com_fallback(self) -> None:
        cases = (
            (
                self.connectors.GreenhouseCareerPageAdapter(),
                self.SourceConfig(
                    name="greenhouse-invalid-link",
                    base_url="https://boards.greenhouse.io/acme",
                    terms_accepted=True,
                    settings={
                        "payload": json.dumps(
                            {
                                "jobs": [
                                    {
                                        "title": "Broken Greenhouse",
                                        "company_name": "Acme",
                                        "content": "No safe details link",
                                        "absolute_url": "javascript:alert(1)",
                                    }
                                ]
                            }
                        )
                    },
                ),
                "invalid description URL",
            ),
            (
                self.connectors.LeverCareerPageAdapter(),
                self.SourceConfig(
                    name="lever-invalid-link",
                    base_url="https://jobs.lever.co/acme",
                    terms_accepted=True,
                    settings={
                        "payload": json.dumps(
                            [
                                {
                                    "text": "Broken Lever",
                                    "descriptionPlain": "No safe apply link",
                                    "hostedUrl": "https://jobs.lever.co/acme/broken",
                                    "applyUrl": "https://?invalid",
                                }
                            ]
                        )
                    },
                ),
                "invalid application URL",
            ),
        )

        for adapter, config, error_marker in cases:
            with self.subTest(source=config.name):
                result = adapter.fetch(config)
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.jobs, ())
                self.assertIn(error_marker, result.error or "")
                self.assertNotIn("example.com", result.error or "")


if __name__ == "__main__":
    unittest.main()
