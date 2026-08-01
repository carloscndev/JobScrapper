import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
RUNTIME_AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ("fastapi", "sqlalchemy", "httpx", "pydantic"))


@unittest.skipUnless(RUNTIME_AVAILABLE, "FastAPI/SQLAlchemy/httpx dependencies are not installed")
class ManualRefreshScoringTests(unittest.TestCase):
    def setUp(self):
        import sys
        sys.path.insert(0, str(BACKEND)) if str(BACKEND) not in sys.path else None
        from fastapi.testclient import TestClient
        from app.config import Settings
        from app.factory import create_app
        from app.models import Base, Profile, ProfilePreference
        from app.database import create_db_engine, create_session_factory

        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "scoring.db"
        self.settings = Settings(database_url=f"sqlite:///{self.db_path}", environment="test")
        engine = create_db_engine(self.settings)
        Base.metadata.create_all(engine)
        session = create_session_factory(engine)()
        session.add(Profile(name="Scoring profile", skills=["python", "fastapi"], experience=["5 years"], languages=["English"]))
        session.flush()
        profile = session.query(Profile).first()
        profile.preferences.append(ProfilePreference(modalities=["remote"], weights={"skills": 40, "experience": 30, "modality": 30}))
        session.commit()
        session.close()
        self.client = TestClient(create_app(self.settings))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def add_fixture_source(self, jobs=None):
        jobs = jobs or [{
            "title": "Python API Engineer", "company": "Fixture Co", "description": "Build FastAPI services",
            "url": "https://jobs.example/score/1", "modality": "remote",
        }]
        response = self.client.post("/api/v1/sources", json={
            "name": "fixture-score-feed", "kind": "api", "terms_accepted": True,
            "config": {"adapter": "json-api-feed", "terms_accepted": True, "payload": json.dumps({"jobs": jobs})},
        })
        self.assertEqual(response.status_code, 201)

    def test_refresh_persists_score_and_exposes_it_in_jobs(self):
        self.add_fixture_source()
        refresh = self.client.post("/api/v1/operations/refresh")
        self.assertEqual(refresh.status_code, 202)
        payload = refresh.json()
        self.assertEqual(payload["metrics"]["evaluations_created"], 1)
        self.assertEqual(payload["metrics"]["evaluation_errors"], 0)
        jobs = self.client.get("/api/v1/jobs?page=1&page_size=1").json()
        self.assertIsNotNone(jobs["items"][0]["score"])
        self.assertGreaterEqual(jobs["items"][0]["score"], 0)
        detail = self.client.get(f"/api/v1/jobs/{jobs['items'][0]['id']}").json()
        self.assertIsNotNone(detail["score"])
        self.assertIsNotNone(detail["evaluation"])

    def test_refresh_evaluates_fixture_with_more_than_100_jobs(self):
        jobs = [
            {
                "title": f"Python API Engineer {index}",
                "company": "Fixture Co",
                "description": "Build FastAPI services",
                "url": f"https://jobs.example/score/{index}",
                "modality": "remote",
            }
            for index in range(101)
        ]
        self.add_fixture_source(jobs)

        refresh = self.client.post("/api/v1/operations/refresh")

        self.assertEqual(refresh.status_code, 202)
        metrics = refresh.json()["metrics"]
        self.assertEqual(metrics["jobs_found"], 101)
        self.assertEqual(metrics["evaluations_created"], 101)
        self.assertEqual(metrics["evaluation_errors"], 0)
        self.assertEqual(self.client.get("/api/v1/jobs?page=1&page_size=1").json()["total"], 101)


if __name__ == "__main__":
    unittest.main()
