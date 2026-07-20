"""Contract and HTTP tests for the paginated jobs API (API-002)."""

from __future__ import annotations

import ast
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[2]
BACKEND = ROOT / "backend"
FACTORY = BACKEND / "app" / "factory.py"
SCHEMAS = BACKEND / "app" / "schemas.py"
sys.path.insert(0, str(BACKEND))


class JobsApiSourceContractTests(unittest.TestCase):
    def test_jobs_routes_and_query_contract_are_declared(self) -> None:
        source = FACTORY.read_text(encoding="utf-8")
        tree = ast.parse(source)
        routes = {
            decorator.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr == "get"
            and decorator.args
            and isinstance(decorator.args[0], ast.Constant)
            and isinstance(decorator.args[0].value, str)
        }
        self.assertIn("/api/v1/jobs", routes)
        self.assertIn("/api/v1/jobs/{job_id}", routes)
        for field in ("page", "page_size", "region", "modality", "status_filter", "company", "min_score", "profile_id", "order", "direction"):
            self.assertIn(field, source)

    def test_job_response_schema_contains_links_score_and_history(self) -> None:
        schema_source = SCHEMAS.read_text(encoding="utf-8")
        for field in ("description_url", "application_url", "score_breakdown", "recommendations", "evaluation_history"):
            self.assertIn(field, schema_source)


try:
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.database import create_db_engine, create_session_factory
    from app.factory import create_app
    from app.models import Base, Evaluation, Job, Profile

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


@unittest.skipUnless(HTTP_AVAILABLE, "FastAPI/SQLAlchemy dependencies are not installed")
class JobsApiHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = ROOT / ".tmp-api-jobs-test.db"
        if self.db_path.exists():
            self.db_path.unlink()
        self.settings = Settings(database_url=f"sqlite:///{self.db_path}", environment="test")
        self.engine = create_db_engine(self.settings)
        Base.metadata.create_all(self.engine)
        self.session_factory = create_session_factory(self.engine)
        self._seed()
        self.client = TestClient(create_app(self.settings))

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()

    def _seed(self) -> None:
        with self.session_factory() as db:
            profile = Profile(name="Candidate", skills=["python"])
            other_profile = Profile(name="Other Candidate", skills=["go"])
            db.add_all([profile, other_profile])
            db.flush()
            for index, (title, region, score) in enumerate(
                (("Backend Engineer", "cdmx", 92.0), ("Data Engineer", "guadalajara", 72.0), ("QA Engineer", "usa", 55.0)),
                start=1,
            ):
                job = Job(
                    title=title, company="Acme", description=f"Build {title} systems",
                    description_url=f"https://jobs.example/{index}", application_url=f"https://apply.example/{index}",
                    canonical_url=f"https://jobs.example/{index}", fingerprint=f"fingerprint-{index}",
                    region=region, modality="remote", status="active", published_at=date(2026, 7, index),
                    detected_at=datetime(2026, 7, index, tzinfo=timezone.utc), checked_at=datetime(2026, 7, index, tzinfo=timezone.utc),
                )
                db.add(job)
                db.flush()
                db.add(Evaluation(
                    job_id=job.id, profile_id=profile.id, score=score, ruleset_version="rules-1",
                    model_version="local-1", score_breakdown={"skills": score}, matches=["python"],
                    gaps=[], exclusions=[], recommendations=["Apply"], status="completed",
                ))
            db.commit()

    def test_list_supports_pagination_filter_and_order(self) -> None:
        response = self.client.get("/api/v1/jobs", params={"region": "cdmx", "page": 1, "page_size": 1, "order": "score", "direction": "desc"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["total_pages"], 1)
        self.assertEqual(body["items"][0]["title"], "Backend Engineer")
        self.assertEqual(body["items"][0]["score"], 92.0)

    def test_list_min_score_and_query_filters(self) -> None:
        response = self.client.get("/api/v1/jobs", params={"min_score": 70, "q": "Data"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["title"] for item in response.json()["items"]], ["Data Engineer"])

    def test_profile_filter_keeps_jobs_without_that_profiles_evaluation(self) -> None:
        """A requested profile must not hide jobs evaluated only for another profile."""
        response = self.client.get("/api/v1/jobs", params={"profile_id": 2, "order": "score", "direction": "desc"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual([item["score"] for item in body["items"]], [None, None, None])

    def test_detail_exposes_links_breakdown_recommendations_and_history(self) -> None:
        response = self.client.get("/api/v1/jobs/1", params={"profile_id": 1})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["description_url"], "https://jobs.example/1")
        self.assertEqual(body["application_url"], "https://apply.example/1")
        self.assertEqual(body["score_breakdown"], {"skills": 92.0})
        self.assertEqual(body["recommendations"], ["Apply"])
        self.assertEqual(len(body["evaluation_history"]), 1)
        self.assertEqual(body["evaluation"]["profile_id"], 1)

    def test_detail_not_found_and_invalid_query_use_error_envelope(self) -> None:
        missing = self.client.get("/api/v1/jobs/999")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "job_not_found")
        invalid = self.client.get("/api/v1/jobs", params={"page": 0})
        self.assertEqual(invalid.status_code, 422)
        body = invalid.json()["error"]
        self.assertEqual(body["code"], "validation_error")
        self.assertTrue(body["fields"])


if __name__ == "__main__":
    unittest.main()
