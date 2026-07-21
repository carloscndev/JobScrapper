"""Tests for JOBS-002 identity, merge, versioning and lifecycle behavior."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is not installed")
class JobIdentityTests(unittest.TestCase):
    def test_canonical_url_removes_tracking_fragment_and_default_port(self) -> None:
        from app.jobs import canonicalize_url

        self.assertEqual(
            canonicalize_url(
                "HTTPS://Example.COM:443/jobs//python/?utm_source=news&b=2&a=1#details"
            ),
            "https://example.com/jobs/python?a=1&b=2",
        )

    def test_fingerprint_is_stable_for_case_and_whitespace(self) -> None:
        from app.jobs import fingerprint_job

        first = {"title": " Senior Engineer ", "company": "Acme", "location": "CDMX"}
        second = {"title": "senior   engineer", "company": "ACME", "location": "cdmx"}
        self.assertEqual(fingerprint_job(first), fingerprint_job(second))


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is not installed")
class JobRepositoryTests(unittest.TestCase):
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
        self.source = Source(name=f"source-{id(self)}", kind="feed", base_url="https://jobs.example")
        self.session.add(self.source)
        self.session.flush()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def _job(self, *, description: str = "Build systems", url: str = "https://jobs.example/1", **kwargs):
        from app.models import Job

        return Job(
            source_id=self.source.id,
            title="Backend Engineer",
            company="Acme",
            description=description,
            description_url=url,
            application_url=kwargs.pop("application_url", "https://apply.example/1"),
            canonical_url=kwargs.pop("canonical_url", url),
            fingerprint=kwargs.pop("fingerprint", ""),
            location=kwargs.pop("location", "CDMX"),
            region=kwargs.pop("region", "cdmx"),
            modality=kwargs.pop("modality", "remote"),
            **kwargs,
        )

    def test_upsert_deduplicates_url_and_preserves_useful_existing_values(self) -> None:
        from app.repositories import JobRepository

        repo = JobRepository(self.session)
        original = repo.upsert(self._job(description="Detailed description"))
        duplicate = repo.upsert(
            self._job(
                description="",
                url="https://jobs.example/1?utm_source=mail",
                canonical_url="https://jobs.example/1?utm_source=mail",
                application_url=None,
                modality="unknown",
            )
        )
        self.assertEqual(original.id, duplicate.id)
        self.assertEqual(duplicate.description, "Detailed description")
        self.assertEqual(duplicate.modality, "remote")

    def test_upsert_sets_checked_at_when_incoming_is_none(self) -> None:
        from datetime import datetime, timezone
        from app.repositories import JobRepository

        repo = JobRepository(self.session)
        first = repo.upsert(self._job())
        self.assertIsNotNone(first.checked_at)
        second = repo.upsert(self._job(url="https://jobs.example/2", canonical_url="https://jobs.example/2"))
        self.assertIsNotNone(second.checked_at)

    def test_upsert_respects_explicit_checked_at(self) -> None:
        from datetime import datetime, timezone
        from app.repositories import JobRepository

        explicit = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo = JobRepository(self.session)
        job = repo.upsert(self._job(checked_at=explicit, url="https://jobs.example/3", canonical_url="https://jobs.example/3"))
        self.assertEqual(job.checked_at, explicit)

    def test_content_change_creates_one_previous_snapshot(self) -> None:
        from sqlalchemy import select
        from app.models import JobSnapshot
        from app.repositories import JobRepository

        repo = JobRepository(self.session)
        job = repo.upsert(self._job(description="v1"))
        repo.upsert(self._job(description="v2", canonical_url=job.canonical_url))
        snapshots = self.session.scalars(select(JobSnapshot).where(JobSnapshot.job_id == job.id)).all()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].description, "v1")

    def test_identical_partial_upsert_does_not_create_snapshot(self) -> None:
        """A sparse retry of the same content is not a new historical version."""
        from sqlalchemy import select
        from app.models import JobSnapshot
        from app.repositories import JobRepository

        repo = JobRepository(self.session)
        job = repo.upsert(self._job(description="stable", modality="remote"))
        repo.upsert(
            self._job(
                description="stable",
                canonical_url=job.canonical_url,
                application_url=None,
                modality="unknown",
                region="other",
                location=None,
            )
        )
        snapshots = self.session.scalars(select(JobSnapshot).where(JobSnapshot.job_id == job.id)).all()
        self.assertEqual(snapshots, [])

    def test_mark_missing_deactivates_only_unseen_source_jobs(self) -> None:
        from app.repositories import JobRepository

        repo = JobRepository(self.session)
        seen = repo.upsert(self._job(url="https://jobs.example/seen", fingerprint="seen-fp"))
        missing = repo.upsert(self._job(url="https://jobs.example/missing", fingerprint="miss-fp"))
        changed = repo.mark_missing(self.source.id, {"https://jobs.example/seen?utm_medium=email"})
        self.assertEqual(changed, 1)
        self.session.refresh(seen)
        self.session.refresh(missing)
        self.assertEqual(seen.status, "active")
        self.assertEqual(missing.status, "inactive")


if __name__ == "__main__":
    unittest.main()
