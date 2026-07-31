"""Regression tests for SOURCES-004 source registration and refresh.

These tests exercise the public source/refresh contract as well as the shared
adapter resolver.  They intentionally use inline fixtures so no external job
board or network access is required.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


RUNTIME_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("fastapi", "sqlalchemy", "httpx", "pydantic")
)
SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


@unittest.skipUnless(RUNTIME_AVAILABLE, "FastAPI/SQLAlchemy/httpx dependencies are not installed")
class SourceRegistrationValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        from app.config import Settings
        from app.factory import create_app

        self.tempdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tempdir.name) / "sources.db"
        settings = Settings(database_url=f"sqlite:///{db_path}", environment="test")
        self.client = TestClient(create_app(settings))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    @staticmethod
    def _errors(response) -> list[dict[str, str]]:
        return response.json()["error"]["fields"]

    def test_enabled_source_requires_terms_and_runnable_fetch_configuration(self) -> None:
        response = self.client.post(
            "/api/v1/sources",
            json={"name": "missing-config", "kind": "api", "enabled": True},
        )

        self.assertEqual(response.status_code, 422)
        fields = self._errors(response)
        self.assertEqual(
            {item["field"] for item in fields},
            {"terms_accepted", "config"},
        )

    def test_enabled_source_requires_fixture_or_explicit_network_mode(self) -> None:
        response = self.client.post(
            "/api/v1/sources",
            json={
                "name": "missing-fixture",
                "kind": "api",
                "terms_accepted": True,
                "config": {"adapter": "json-api-feed"},
            },
        )

        self.assertEqual(response.status_code, 422)
        fields = self._errors(response)
        self.assertIn("config", {item["field"] for item in fields})
        self.assertIn("payload", fields[-1]["message"])

    def test_network_mode_requires_base_url(self) -> None:
        response = self.client.post(
            "/api/v1/sources",
            json={
                "name": "missing-network-url",
                "kind": "api",
                "terms_accepted": True,
                "config": {"adapter": "json-api-feed", "allow_network": True},
            },
        )

        self.assertEqual(response.status_code, 422)
        fields = self._errors(response)
        self.assertIn("base_url", {item["field"] for item in fields})

    def test_invalid_source_urls_return_structured_422(self) -> None:
        for field_name in ("base_url", "terms_url"):
            with self.subTest(field_name=field_name):
                response = self.client.post(
                    "/api/v1/sources",
                    json={
                        "name": f"invalid-{field_name}",
                        "kind": "api",
                        field_name: "not-a-url",
                        "enabled": False,
                    },
                )

                self.assertEqual(response.status_code, 422)
                fields = self._errors(response)
                matching = [item for item in fields if item["field"] == field_name]
                self.assertEqual(len(matching), 1)
                self.assertIn("http(s) URL", matching[0]["message"])

    def test_allow_network_must_be_boolean(self) -> None:
        response = self.client.post(
            "/api/v1/sources",
            json={
                "name": "non-boolean-network-mode",
                "kind": "api",
                "terms_accepted": True,
                "config": {"adapter": "json-api-feed", "allow_network": "true"},
            },
        )

        self.assertEqual(response.status_code, 422)
        fields = self._errors(response)
        matching = [item for item in fields if item["field"] == "config.allow_network"]
        self.assertEqual(len(matching), 1)
        self.assertIn("boolean", matching[0]["message"])

    def test_disabled_source_can_be_saved_then_rejects_invalid_enablement(self) -> None:
        response = self.client.post(
            "/api/v1/sources",
            json={"name": "disabled-unconfigured", "kind": "api", "enabled": False},
        )
        self.assertEqual(response.status_code, 201)
        source_id = response.json()["id"]

        response = self.client.patch(f"/api/v1/sources/{source_id}", json={"enabled": True})

        self.assertEqual(response.status_code, 422)
        self.assertIn("terms_accepted", {item["field"] for item in self._errors(response)})


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is not installed")
class SharedAdapterResolverTests(unittest.TestCase):
    def test_resolver_uses_explicit_override_then_name_then_kind(self) -> None:
        from app.sources import resolve_source_adapter

        adapters = (
            SimpleNamespace(name="json-api-feed"),
            SimpleNamespace(name="greenhouse-career-page"),
        )
        source = SimpleNamespace(name="custom-source", kind="api", config={})

        self.assertEqual(resolve_source_adapter(source, adapters).name, "json-api-feed")
        source.config = {"adapter": "greenhouse-career-page"}
        self.assertEqual(resolve_source_adapter(source, adapters).name, "greenhouse-career-page")
        source.config = {"adapter": "does-not-exist"}
        self.assertIsNone(resolve_source_adapter(source, adapters))


@unittest.skipUnless(RUNTIME_AVAILABLE, "FastAPI/SQLAlchemy/httpx dependencies are not installed")
class SourceRefreshRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        from app.config import Settings
        from app.factory import create_app

        self.tempdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tempdir.name) / "refresh.db"
        settings = Settings(database_url=f"sqlite:///{db_path}", environment="test")
        self.client = TestClient(create_app(settings))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_direct_adapter_match_refreshes_without_unbound_mapping_state(self) -> None:
        response = self.client.post(
            "/api/v1/sources",
            json={
                # The adapter name itself exercises the direct-name branch;
                # the old factory implementation then referenced ``mapped``
                # before assignment while trying to log/resolve it.
                "name": "json-api-feed",
                "kind": "api",
                "terms_accepted": True,
                "config": {
                    "adapter": "json-api-feed",
                    "payload": json.dumps(
                        {
                            "jobs": [
                                {
                                    "title": "Backend Engineer",
                                    "company": "Fixture Co",
                                    "description": "Build reliable APIs",
                                    "url": "https://jobs.example/roles/1",
                                }
                            ]
                        }
                    ),
                },
            },
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post("/api/v1/operations/refresh")

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["metrics"]["jobs_found"], 1)
        self.assertEqual(payload["source_runs"][0]["status"], "success")
        self.assertEqual(payload["source_runs"][0]["jobs_found"], 1)
        self.assertIsNone(payload["source_runs"][0]["error"])

    def test_zero_job_fixture_is_failed_with_actionable_source_error(self) -> None:
        response = self.client.post(
            "/api/v1/sources",
            json={
                "name": "empty-feed",
                "kind": "api",
                "terms_accepted": True,
                "config": {
                    "adapter": "json-api-feed",
                    "payload": json.dumps({"jobs": []}),
                },
            },
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post("/api/v1/operations/refresh")

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        source_run = payload["source_runs"][0]
        self.assertEqual(source_run["status"], "failed")
        self.assertEqual(source_run["jobs_found"], 0)
        self.assertIn("No jobs found", source_run["error"])
        self.assertIn("No jobs found", payload["error"])


@unittest.skipUnless(RUNTIME_AVAILABLE, "FastAPI/SQLAlchemy/httpx dependencies are not installed")
class JobPipelineZeroJobsTests(unittest.TestCase):
    def test_empty_fetch_is_failed_in_direct_job_pipeline(self) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.models import Base, Profile, ProfilePreference, Source
        from app.pipeline import JobPipeline
        from app.sources import SourceFetchResult

        class EmptyAdapter:
            name = "empty-feed"

            def fetch(self, _config):
                return SourceFetchResult()

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine, expire_on_commit=False)()
        try:
            profile = Profile(name="Test", skills=["python"], experience=[], languages=[])
            profile.preferences.append(ProfilePreference(target_roles=["backend"], modalities=["remote"]))
            source = Source(
                name="empty-feed",
                kind="api",
                base_url="https://jobs.example",
                config={"adapter": "empty-feed", "terms_accepted": True},
            )
            session.add_all([profile, source])
            session.commit()

            report = JobPipeline(session, adapters=[EmptyAdapter()]).run(profile)

            self.assertEqual(report.status, "failed")
            self.assertEqual(report.jobs_ingested, 0)
            self.assertEqual(report.evaluations_created, 0)
            self.assertEqual(report.source_runs[0]["status"], "failed")
            self.assertEqual(report.source_runs[0]["jobs_found"], 0)
            self.assertIn("No jobs found", report.source_runs[0]["error"])
            self.assertTrue(any(issue.stage == "ingest" for issue in report.issues))
        finally:
            session.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
