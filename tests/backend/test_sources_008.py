import json
import unittest

from backend.app.connectors import JsonApiFeedAdapter
from backend.app.sources import SourceConfig, SourceKind


class Sources008NormalizationTests(unittest.TestCase):
    def config(self, payload, **settings):
        return SourceConfig(
            name="Greenhouse GitLab API",
            kind=SourceKind.API,
            base_url="https://boards-api.greenhouse.io/v1/boards/gitlab/jobs",
            terms_accepted=True,
            settings={"payload": json.dumps(payload), "terms_accepted": True, **settings},
        )

    def test_greenhouse_metadata_array_is_preserved_without_failing_feed(self):
        result = JsonApiFeedAdapter().fetch(self.config({"jobs": [{
            "title": "Engineer",
            "company_name": "GitLab",
            "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/1",
            "content": "Build software",
            "metadata": [{"name": "Department", "value": "Engineering"}],
        }]}))
        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0].metadata["provider_metadata"][0]["name"], "Department")

    def test_configured_company_is_used_when_feed_omits_company(self):
        result = JsonApiFeedAdapter().fetch(self.config({"jobs": [{
            "title": "Backend Engineer",
            "absolute_url": "https://jobs.lever.co/acme/1",
            "descriptionPlain": "Build APIs",
        }]}, company="Acme"))
        self.assertEqual(result.status, "success")
        self.assertEqual(result.jobs[0].company, "Acme")

    def test_missing_company_without_explicit_fallback_is_rejected(self):
        result = JsonApiFeedAdapter().fetch(self.config({"jobs": [{
            "title": "Unlabeled",
            "absolute_url": "https://job-boards.greenhouse.io/unknown/jobs/1",
            "description": "No company supplied",
        }]}))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.jobs, ())
        self.assertIn("company", result.error or "")


if __name__ == "__main__":
    unittest.main()
