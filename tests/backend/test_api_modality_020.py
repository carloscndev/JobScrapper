"""API-020 end-to-end modality persistence and query-filter regressions."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

RUNTIME_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("fastapi", "sqlalchemy", "httpx", "pydantic")
)


@unittest.skipUnless(RUNTIME_AVAILABLE, "FastAPI/SQLAlchemy/httpx dependencies are required")
class ModalityApi020Tests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient
        from app.config import Settings
        from app.database import create_db_engine, create_session_factory
        from app.factory import create_app
        from app.models import Base

        self._tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(
            database_url=f"sqlite:///{Path(self._tmp.name) / 'modality.db'}",
            environment="test",
        )
        self.engine = create_db_engine(self.settings)
        Base.metadata.create_all(self.engine)
        self.session_factory = create_session_factory(self.engine)
        self.client = TestClient(create_app(self.settings))
        self.client.__enter__()

        jobs = [
            {
                "title": f"{modality.title()} Engineer",
                "company": "Modality Co",
                "description": f"A {modality} role",
                "url": f"https://jobs.example/{modality}",
                "modality": modality,
            }
            for modality in ("remote", "hybrid", "onsite")
        ]
        created = self.client.post(
            "/api/v1/sources",
            json={
                "name": "modality-feed",
                "kind": "api",
                "terms_accepted": True,
                "config": {"adapter": "json-api-feed", "payload": json.dumps({"jobs": jobs})},
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        refreshed = self.client.post("/api/v1/operations/refresh")
        self.assertEqual(refreshed.status_code, 202, refreshed.text)
        self.assertEqual(refreshed.json()["metrics"]["jobs_found"], 3)

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.engine.dispose()
        self._tmp.cleanup()

    def test_refresh_persists_canonical_modality_values(self) -> None:
        from sqlalchemy import select
        from app.models import Job

        with self.session_factory() as db:
            persisted = list(db.scalars(select(Job.modality).order_by(Job.modality)).all())
        self.assertEqual(persisted, ["hybrid", "onsite", "remote"])
        self.assertNotIn("WorkModality.REMOTE", persisted)

    def test_each_canonical_modality_filter_returns_only_matching_jobs(self) -> None:
        for modality in ("remote", "hybrid", "onsite"):
            with self.subTest(modality=modality):
                response = self.client.get("/api/v1/jobs", params={"modality": modality})
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["total"], 1)
                self.assertEqual([item["modality"] for item in body["items"]], [modality])
                self.assertEqual(body["items"][0]["title"], f"{modality.title()} Engineer")

    def test_invalid_modality_returns_structured_422(self) -> None:
        response = self.client.get("/api/v1/jobs", params={"modality": "sometimes"})
        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "validation_error")
        self.assertTrue(any(field.get("field") == "query.modality" for field in error["fields"]))


if __name__ == "__main__":
    unittest.main()
