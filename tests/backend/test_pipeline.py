"""Unit coverage for the OPS-002 single-command pipeline.

Database-backed checks skip explicitly when the optional backend dependencies
are not installed in the lightweight harness.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY = True
except ImportError:  # pragma: no cover - exercised in dependency-light CI
    SQLALCHEMY = False


class PipelineCommandTests(unittest.TestCase):
    def test_command_exposes_safe_runtime_flags(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_pipeline.py"), "--help"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0)
        for flag in ("--profile-id", "--no-notion", "--no-ollama", "--max-jobs"):
            self.assertIn(flag, result.stdout)

    @unittest.skipUnless(SQLALCHEMY, "SQLAlchemy is not installed")
    def test_pipeline_orders_stages_and_preserves_partial_success(self) -> None:
        from app.models import Base, Profile, ProfilePreference, Source
        from app.pipeline import JobPipeline
        from app.sources import NormalizedJob, SourceFetchResult, WorkModality
        from app.ollama import LocalAnalysis
        from app.notion_sync import SyncOutcome

        events: list[str] = []

        class Adapter:
            def __init__(self, name: str, fail: bool = False): self.name, self.fail = name, fail
            def fetch(self, config):
                events.append(f"ingest:{self.name}")
                if self.fail:
                    raise RuntimeError("source unavailable")
                return SourceFetchResult(jobs=[NormalizedJob(
                    title="Backend Engineer", company="Acme", description="Python APIs",
                    description_url=f"https://jobs.example/{self.name}",
                    application_url=f"https://apply.example/{self.name}", region="cdmx",
                    modality=WorkModality.REMOTE, metadata={"required_skills": ["python"]},
                )])

        class Analyzer:
            def analyze(self, profile, job):
                events.append("analyze")
                return LocalAnalysis("ok", ["python"], [], [], "local-test")

        class Notion:
            def sync_jobs(self, evaluations):
                events.append("notion")
                return [SyncOutcome("ok", "synced"), SyncOutcome("bad", "failed", error="rate limited")]

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine, expire_on_commit=False)()
        profile = Profile(name="Test", skills=["python"], experience=[], languages=[])
        profile.preferences.append(ProfilePreference(target_roles=["backend"], modalities=["remote"], locations=["cdmx"]))
        good, bad = Source(name="good", kind="feed", base_url="https://good.example", config={}), Source(name="bad", kind="feed", base_url="https://bad.example", config={})
        session.add_all([profile, good, bad]); session.commit()

        report = JobPipeline(
            session, adapters=[Adapter("good"), Adapter("bad", fail=True)], notion=Notion(), analyzer=Analyzer()
        ).run(profile)
        self.assertEqual(report.status, "partial")
        self.assertEqual(report.jobs_ingested, 1)
        self.assertEqual(report.evaluations_created, 1)
        self.assertEqual(report.notion_synced, 1)
        self.assertEqual(report.notion_failed, 1)
        self.assertTrue(any(issue.stage == "ingest" for issue in report.issues))
        self.assertTrue(any(issue.stage == "notion" for issue in report.issues))
        failed_runs = [run for run in report.source_runs if run["source"] == "bad"]
        self.assertEqual(failed_runs[0]["error"], "RuntimeError: source unavailable")
        self.assertLess(events.index("ingest:good"), events.index("analyze"))
        self.assertLess(events.index("analyze"), events.index("notion"))


if __name__ == "__main__":
    unittest.main()
