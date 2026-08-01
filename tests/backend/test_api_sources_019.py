"""API-019 regressions for Mexican and Ashby job-board payloads."""

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
class ApiSources019ConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        from app import connectors
        from app.sources import SourceConfig

        self.connectors = connectors
        self.SourceConfig = SourceConfig

    def _fetch(self, payload: object, name: str = "api-019"):
        config = self.SourceConfig(
            name=name,
            base_url="https://jobs.ashbyhq.com/kueski",
            terms_accepted=True,
            settings={"payload": json.dumps(payload)},
        )
        return self.connectors.JsonApiFeedAdapter().fetch(config)

    def test_kueski_payload_normalizes_ashby_fields_urls_html_date_and_mexico_region(self) -> None:
        result = self._fetch(
            {
                "jobs": [
                    {
                        "title": "Backend Engineer",
                        "company": "Kueski",
                        "jobUrl": "https://jobs.ashbyhq.com/kueski/backend-1",
                        "descriptionHtml": "<p>Build APIs.</p><script>discard()</script>",
                        "applyUrl": "https://jobs.ashbyhq.com/kueski/backend-1/apply",
                        "location": "Monterrey, Mexico",
                        "publishedAt": "2026-07-31",
                        "isRemote": True,
                    }
                ]
            },
            "kueski-ashby",
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.jobs), 1)
        job = result.jobs[0]
        self.assertEqual(job.description_url, "https://jobs.ashbyhq.com/kueski/backend-1")
        self.assertEqual(job.application_url, "https://jobs.ashbyhq.com/kueski/backend-1/apply")
        self.assertEqual(job.description, "Build APIs.")
        self.assertEqual(job.published_at, date(2026, 7, 31))
        self.assertEqual(job.region, "mexico")
        self.assertEqual(job.modality.value, "remote")
        self.assertNotIn("example.com", job.description_url)

    def test_guadajalara_alias_classifies_as_guadalajara(self) -> None:
        result = self._fetch(
            {
                "jobs": [
                    {
                        "title": "Product Engineer",
                        "company": "Kueski",
                        "jobUrl": "https://jobs.ashbyhq.com/kueski/product-1",
                        "descriptionHtml": "<p>Build products.</p>",
                        "applyUrl": "https://jobs.ashbyhq.com/kueski/product-1/apply",
                        "location": "Guadajalara, Jalisco",
                    }
                ]
            },
            "kueski-guadajalara",
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.jobs[0].region, "guadalajara")
        self.assertEqual(result.jobs[0].description_url, "https://jobs.ashbyhq.com/kueski/product-1")

    def test_malformed_ashby_job_url_is_rejected_without_fallback(self) -> None:
        result = self._fetch(
            {
                "jobs": [
                    {
                        "title": "Broken Ashby job",
                        "company": "Kueski",
                        "jobUrl": "javascript:alert(1)",
                        "descriptionHtml": "<p>Unsafe link.</p>",
                        "applyUrl": "https://jobs.ashbyhq.com/kueski/broken/apply",
                    }
                ]
            },
            "kueski-invalid-url",
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.jobs, ())
        self.assertIn("invalid description URL", result.error or "")
        self.assertNotIn("example.com", result.error or "")


if __name__ == "__main__":
    unittest.main()
