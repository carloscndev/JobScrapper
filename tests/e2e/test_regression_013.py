"""TEST-013 regression coverage for source ingestion and profile restrictions.

The API checks are deliberately fixture-first and are skipped when the optional
FastAPI/SQLAlchemy stack is not installed.  Frontend assertions are executable
contracts, so CI can still verify the dashboard/detail and profile reload wiring
without requiring a browser runtime.  Set ``JOBSCRAPPER_E2E_URL`` and install
Playwright to opt into the browser flow.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
APP = (ROOT / "frontend/src/App.tsx").read_text(encoding="utf-8")
CLIENT = (ROOT / "frontend/src/api/client.ts").read_text(encoding="utf-8")
PLAYWRIGHT_AVAILABLE = importlib.util.find_spec("playwright") is not None
HTTP_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("fastapi", "sqlalchemy", "httpx", "pydantic")
)


class RegressionContractTests(unittest.TestCase):
    """Keep the three user-visible regression paths wired together."""

    def test_fixture_source_contract_carries_success_and_actionable_failures(self) -> None:
        source_tests = (ROOT / "tests/backend/test_sources_004.py").read_text(encoding="utf-8")
        for marker in (
            '"payload": json.dumps',
            '"/api/v1/operations/refresh"',
            '"source_runs"',
            '"No jobs found"',
            '"status"',
        ):
            self.assertIn(marker, source_tests)

    def test_dashboard_detail_contract_preserves_resolved_and_distinct_links(self) -> None:
        for marker in (
            "description_url",
            "application_url",
            'href={detail.application_url ?? detail.description_url}',
            'href={detail.description_url}',
            'target="_blank"',
            'rel="noopener noreferrer"',
            'id="vacancy-detail-title"',
        ):
            self.assertIn(marker, APP)
        connector_tests = (ROOT / "tests/backend/test_connectors.py").read_text(encoding="utf-8")
        self.assertIn("test_job_resolves_relative_links_with_or_without_trailing_slash", connector_tests)
        self.assertIn("test_job_keeps_supplied_description_application_and_canonical_urls_distinct", connector_tests)

    def test_profile_contract_sends_and_rehydrates_every_restriction(self) -> None:
        for marker in (
            "willing_to_relocate",
            "excluded_constraints",
            "weights",
            "persistedConstraints",
            "CONSTRAINT_NO_SALARY",
            "CONSTRAINT_UNVERIFIED_COMPANY",
            "CONSTRAINT_RELOCATION_REQUIRED",
        ):
            self.assertIn(marker, APP)
        for marker in ("willing_to_relocate", "excluded_constraints", "weights"):
            self.assertIn(marker, CLIENT)
        profile_tests = (ROOT / "tests/backend/test_api_profile.py").read_text(encoding="utf-8")
        self.assertIn("test_preferences_put_then_get_preserves_constraints_relocation_and_weights", profile_tests)


@unittest.skipUnless(HTTP_AVAILABLE, "FastAPI/SQLAlchemy/httpx dependencies are not installed")
class ApiRegressionTests(unittest.TestCase):
    """Exercise source refresh errors and preference PUT -> GET persistence."""

    def setUp(self) -> None:
        import sys

        sys.path.insert(0, str(BACKEND))
        from fastapi.testclient import TestClient
        from app.config import Settings
        from app.factory import create_app
        from app.models import Base, Profile
        from app.database import create_db_engine, create_session_factory

        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "regression.db"
        self.settings = Settings(database_url=f"sqlite:///{self.db_path}", environment="test")
        self.engine = create_db_engine(self.settings)
        Base.metadata.create_all(self.engine)
        with create_session_factory(self.engine)() as db:
            profile = Profile(name="Regression Candidate", skills=["Python"], experience=[], languages=[])
            db.add(profile)
            db.commit()
            self.profile_id = profile.id
        self.client = TestClient(create_app(self.settings))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.engine.dispose()
        self._tmp.cleanup()

    def test_fixture_refresh_persists_valid_job_and_surfaces_invalid_item(self) -> None:
        payload = {
            "jobs": [
                {
                    "title": "Fixture Backend Engineer",
                    "company": "Fixture Co",
                    "description": "Build APIs",
                    "url": "roles/backend",
                    "apply_url": "roles/backend/apply",
                },
                {"title": "Broken fixture", "company": "Fixture Co", "description": "Missing URL"},
            ]
        }
        response = self.client.post(
            "/api/v1/sources",
            json={
                "name": "regression-feed",
                "kind": "api",
                "base_url": "https://jobs.example/careers",
                "terms_accepted": True,
                "config": {"adapter": "json-api-feed", "payload": json.dumps(payload)},
            },
        )
        self.assertEqual(response.status_code, 201)

        refreshed = self.client.post("/api/v1/operations/refresh")
        self.assertEqual(refreshed.status_code, 202)
        report = refreshed.json()
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["metrics"]["jobs_found"], 1)
        source_run = report["source_runs"][0]
        self.assertEqual(source_run["status"], "partial")
        self.assertIn("missing a valid description URL", source_run["error"])

        jobs = self.client.get("/api/v1/jobs").json()["items"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["description_url"], "https://jobs.example/careers/roles/backend")
        self.assertEqual(jobs[0]["application_url"], "https://jobs.example/careers/roles/backend/apply")

    def test_preference_restrictions_survive_api_save_and_reload(self) -> None:
        payload = {
            "target_roles": ["Backend Engineer"],
            "locations": ["CDMX"],
            "modalities": ["remote"],
            "willing_to_relocate": False,
            "excluded_constraints": ["no_salary", "unverified_company", "relocation_required"],
            "weights": {"skills": 2.5, "experience": 1.25, "location": 0.75},
        }
        saved = self.client.put(f"/api/v1/profiles/{self.profile_id}/preferences", json=payload)
        self.assertEqual(saved.status_code, 200)

        reloaded = self.client.get(f"/api/v1/profiles/{self.profile_id}")
        self.assertEqual(reloaded.status_code, 200)
        preferences = reloaded.json()["preferences"]
        self.assertEqual(preferences["excluded_constraints"], payload["excluded_constraints"])
        self.assertFalse(preferences["willing_to_relocate"])
        self.assertEqual(preferences["weights"], payload["weights"])


@unittest.skipUnless(PLAYWRIGHT_AVAILABLE and os.getenv("JOBSCRAPPER_E2E_URL"), "opt-in Playwright browser regression")
class BrowserRegressionContractTests(unittest.TestCase):
    """Optional browser smoke test; normal CI remains dependency-light."""

    def test_dashboard_detail_and_profile_reload_smoke(self) -> None:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(os.environ["JOBSCRAPPER_E2E_URL"].rstrip("/"), wait_until="networkidle")
                page.get_by_role("tab", name="Preferences and weights").click()
                relocation = page.get_by_role("checkbox", name="Show openings that require relocation")
                initial_relocation = relocation.is_checked()
                relocation.click()
                page.get_by_role("button", name="Save changes").click()
                page.get_by_text("Changes saved").wait_for()
                page.reload(wait_until="networkidle")
                page.get_by_role("tab", name="Preferences and weights").click()
                self.assertEqual(page.get_by_role("checkbox", name="Show openings that require relocation").is_checked(), not initial_relocation)
                page.get_by_role("tab", name="Openings").click()
                detail_button = page.get_by_role("button", name="View details for Senior Backend Engineer at Nubank")
                self.assertEqual(detail_button.count(), 1)
                detail_button.click()
                detail_title = page.locator("#vacancy-detail-title")
                self.assertTrue(detail_title.is_visible())
                self.assertEqual(detail_title.inner_text().strip(), "Senior Backend Engineer")
                application_href = page.get_by_role("link", name="Apply").get_attribute("href")
                description_href = page.get_by_role("link", name="View original description").get_attribute("href")
                self.assertTrue(application_href)
                self.assertTrue(description_href)
                self.assertNotEqual(application_href, description_href)
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
