"""Representative and ambiguous fixtures for normalized job ingestion.

The fixtures are deliberately deterministic and offline.  They exercise the
boundary between source parsing and job identity without making network calls
or depending on a particular provider's live HTML.
"""

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


NORMALIZATION_FIXTURE = {
    "jobs": [
        {
            "title": "Senior Python Engineer",
            "company": "Acme México",
            "description": "Build <strong>APIs</strong> and reliable pipelines.",
            "url": "/jobs/python?utm_source=mail",
            "apply_url": "/apply/python",
            "location": "Ciudad de México",
            "modality": "Remote",
            "salary": "$50,000-$70,000 MXN",
            "requirements": "Python\n• FastAPI; SQL",
            "date_posted": "2026-07-18",
        },
        {
            "title": "Platform Engineer",
            "company": "Acme Guadalajara",
            "description": "Operate cloud infrastructure.",
            "url": "https://jobs.example/platform",
            "application_url": "https://apply.example/platform",
            "location": "Remote - Zapopan, Jalisco",
            "modality": "remote / hybrid",
        },
        {
            "title": "SRE",
            "company": "Acme US",
            "description": "Keep services healthy.",
            "url": "https://jobs.example/sre",
            "location": "Austin, United States",
            "workplace_type": "On-site",
        },
        {
            "title": "Researcher",
            "company": "Acme Europe",
            "description": "Explore new systems.",
            "url": "https://jobs.example/research",
            "location": "Berlin, Germany",
        },
    ]
}


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is required for runtime job fixtures")
class JobNormalizationFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        from app import connectors
        from app.sources import SourceConfig, SourceKind

        self.connectors = connectors
        self.config = SourceConfig(
            name="normalization-fixture",
            kind=SourceKind.FEED,
            base_url="https://jobs.example/",
            terms_accepted=True,
            settings={"payload": json.dumps(NORMALIZATION_FIXTURE)},
        )

    def test_representative_feed_normalizes_urls_salary_requirements_and_dates(self) -> None:
        result = self.connectors.JsonApiFeedAdapter().fetch(self.config)

        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.jobs), 4)
        job = result.jobs[0]
        self.assertEqual(job.description_url, "https://jobs.example/jobs/python?utm_source=mail")
        self.assertEqual(job.application_url, "https://jobs.example/apply/python")
        self.assertEqual((job.salary_min, job.salary_max), (50000.0, 70000.0))
        self.assertEqual(job.salary_currency, "MXN")
        self.assertEqual(job.requirements, ("Python", "FastAPI", "SQL"))
        self.assertNotIn("<strong>", job.description)
        self.assertEqual(job.published_at.isoformat(), "2026-07-18")

    def test_ambiguous_location_and_modality_rules_are_stable(self) -> None:
        result = self.connectors.JsonApiFeedAdapter().fetch(self.config)
        by_title = {job.title: job for job in result.jobs}

        # A remote marker must not erase the more specific Guadalajara region.
        self.assertEqual(by_title["Platform Engineer"].region, "guadalajara")
        self.assertEqual(by_title["Platform Engineer"].modality.value, "remote")
        self.assertEqual(by_title["SRE"].region, "usa")
        self.assertEqual(by_title["SRE"].modality.value, "onsite")
        self.assertEqual(by_title["Researcher"].region, "other")
        self.assertEqual(by_title["Researcher"].modality.value, "unknown")

    def test_explicit_region_wins_only_according_to_documented_precedence(self) -> None:
        # This intentionally ambiguous input is a regression fixture: the
        # classifier is deterministic and checks CDMX before USA.
        from app.connectors import classify_region

        self.assertEqual(classify_region("Remote", explicit="USA").value, "usa")
        self.assertEqual(classify_region("CDMX / United States").value, "cdmx")
        self.assertEqual(classify_region("Monterrey, Nuevo León").value, "mexico")


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is required for identity fixtures")
class JobIdentityFixtureTests(unittest.TestCase):
    def test_tracking_variants_have_one_canonical_identity(self) -> None:
        from app.jobs import canonicalize_url, fingerprint_job

        first = "HTTPS://Jobs.Example:443/jobs//python/?utm_source=mail&b=2#description"
        second = "https://jobs.example/jobs/python?b=2&utm_medium=campaign"
        self.assertEqual(canonicalize_url(first), canonicalize_url(second))
        self.assertEqual(
            fingerprint_job({"title": " Senior Engineer ", "company": "Acme", "location": "CDMX"}),
            fingerprint_job({"title": "senior   engineer", "company": "ACME", "location": "cdmx"}),
        )

    def test_content_hash_is_repeatable_and_changes_only_when_content_changes(self) -> None:
        from app.jobs import content_hash

        kwargs = {
            "description": "Build reliable APIs",
            "description_url": "https://jobs.example/1",
            "application_url": "https://apply.example/1",
        }
        original = content_hash(**kwargs)
        self.assertEqual(original, content_hash(**kwargs))
        self.assertNotEqual(original, content_hash(**{**kwargs, "description": "Build reliable data pipelines"}))
        self.assertNotEqual(original, content_hash(**{**kwargs, "application_url": "https://apply.example/2"}))


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is required for persistence fixtures")
class JobChangeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models import Base

        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.factory = sessionmaker(bind=cls.engine, expire_on_commit=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        from app.models import Source

        self.session = self.factory()
        self.source = Source(name=f"fixture-source-{id(self)}", kind="feed", base_url="https://jobs.example")
        self.session.add(self.source)
        self.session.flush()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def _job(self, description: str, *, url: str = "https://jobs.example/1"):
        from app.models import Job

        return Job(
            source_id=self.source.id,
            title="Backend Engineer",
            company="Acme",
            description=description,
            description_url=url,
            application_url="https://apply.example/1",
            canonical_url=url,
            fingerprint="",
            location="CDMX",
            region="cdmx",
            modality="remote",
        )

    def test_repeated_rediscovery_is_one_job_and_one_snapshot_per_distinct_change(self) -> None:
        from sqlalchemy import select
        from app.models import JobSnapshot
        from app.repositories import JobRepository

        repo = JobRepository(self.session)
        first = repo.upsert(self._job("v1"))
        duplicate = repo.upsert(self._job("v1", url="https://jobs.example/1?utm_source=feed"))
        changed = repo.upsert(self._job("v2"))
        repeated_change = repo.upsert(self._job("v2"))
        snapshots = self.session.scalars(select(JobSnapshot).where(JobSnapshot.job_id == first.id)).all()

        self.assertEqual(first.id, duplicate.id)
        self.assertEqual(changed.id, repeated_change.id)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].description, "v1")


if __name__ == "__main__":
    unittest.main()
