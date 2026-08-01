"""API-018 connector regressions for Remote OK legal metadata records."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is required for connector runtime tests")
class ApiSources018ConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        from app import connectors
        from app.sources import SourceConfig

        self.connectors = connectors
        self.SourceConfig = SourceConfig

    def _config(self, payload: object, name: str) -> object:
        return self.SourceConfig(
            name=name,
            base_url="https://remoteok.com",
            terms_accepted=True,
            settings={"payload": json.dumps(payload)},
        )

    def test_legal_envelope_is_ignored_before_valid_remote_ok_job(self) -> None:
        payload = {
            "jobs": [
                {"legal": {"terms": "Remote OK terms", "privacy": "Remote OK privacy"}},
                {
                    "title": "Python API Engineer",
                    "company": "Remote Co",
                    "description": "Build APIs.",
                    "url": "https://remoteok.com/remote-jobs/1",
                    "apply_url": "https://remoteok.com/remote-jobs/1/apply",
                },
            ]
        }

        result = self.connectors.JsonApiFeedAdapter().fetch(self._config(payload, "remote-ok"))

        self.assertEqual(result.status, "success")
        self.assertIsNone(result.error)
        self.assertEqual([job.title for job in result.jobs], ["Python API Engineer"])
        self.assertEqual(result.jobs[0].application_url, "https://remoteok.com/remote-jobs/1/apply")

    def test_legal_record_with_job_field_missing_url_remains_partial(self) -> None:
        payload = {
            "jobs": [
                {"legal": "terms", "title": "Malformed Remote OK job", "company": "Remote Co", "description": "No URL."},
                {
                    "title": "Valid Remote OK job",
                    "company": "Remote Co",
                    "description": "Has a URL.",
                    "url": "/remote-jobs/2",
                },
            ]
        }

        result = self.connectors.JsonApiFeedAdapter().fetch(self._config(payload, "remote-ok-marked"))

        self.assertEqual(result.status, "partial")
        self.assertEqual([job.title for job in result.jobs], ["Valid Remote OK job"])
        self.assertIn("missing a valid description URL", result.error or "")


if __name__ == "__main__":
    unittest.main()
