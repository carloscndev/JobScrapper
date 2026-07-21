"""Contract tests for the v1 profile HTTP API.

The repository's lightweight test environment does not necessarily install the
optional FastAPI/SQLAlchemy stack.  Structural tests still run in that case;
HTTP tests are explicitly skipped and report the missing dependency.
"""

from __future__ import annotations

import ast
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
BACKEND = ROOT / "backend"
FACTORY = BACKEND / "app" / "factory.py"
SCHEMAS = BACKEND / "app" / "schemas.py"
sys.path.insert(0, str(BACKEND))


class ApiSourceContractTests(unittest.TestCase):
    """Verify the route and schema contract without importing dependencies."""

    def test_profile_routes_and_openapi_configuration_are_declared(self) -> None:
        source = FACTORY.read_text(encoding="utf-8")
        tree = ast.parse(source)
        routes = {
            decorator.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr in {"get", "post", "put", "patch"}
            and decorator.args
            and isinstance(decorator.args[0], ast.Constant)
            and isinstance(decorator.args[0].value, str)
        }
        self.assertTrue({
            "/api/v1/profiles/upload",
            "/api/v1/profiles/{profile_id}",
            "/api/v1/profiles/{profile_id}/preferences",
        } <= routes)
        self.assertIn('openapi_url="/api/v1/openapi.json"', source)
        self.assertIn('docs_url="/api/v1/docs"', source)

    def test_error_envelope_and_payload_fields_are_present(self) -> None:
        source = FACTORY.read_text(encoding="utf-8")
        self.assertIn('"validation_error"', source)
        self.assertIn('"profile_not_found"', source)
        self.assertIn('"cv_validation_error"', source)
        schema_source = SCHEMAS.read_text(encoding="utf-8")
        for field in ("target_roles", "locations", "modalities", "salary_min", "willing_to_relocate"):
            self.assertIn(field, schema_source)

    def test_profile_patch_contract_marks_profile_for_reevaluation(self) -> None:
        """Structured profile edits must invalidate prior matching results."""
        source = (BACKEND / "app" / "services.py").read_text(encoding="utf-8")
        update_start = source.index("def update_profile")
        update_end = source.index("def update_preferences", update_start)
        update_source = source[update_start:update_end]
        self.assertIn("reevaluation_required", update_source)
        self.assertIn("reevaluation_metadata", update_source)


try:  # Keep collection usable when optional backend dependencies are absent.
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.factory import create_app

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


@unittest.skipUnless(HTTP_AVAILABLE, "FastAPI/SQLAlchemy dependencies are not installed")
class ProfileApiHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = ROOT / ".tmp-api-profile-test.db"
        if self.db_path.exists():
            self.db_path.unlink()
        settings = Settings(database_url=f"sqlite:///{self.db_path}", environment="test")
        self.client = TestClient(create_app(settings))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.client.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def test_openapi_and_docs_are_published(self) -> None:
        spec = self.client.get("/api/v1/openapi.json")
        self.assertEqual(spec.status_code, 200)
        self.assertIn("/api/v1/profiles/upload", spec.json()["paths"])
        self.assertEqual(self.client.get("/api/v1/docs").status_code, 200)

    def test_missing_profile_uses_stable_not_found_envelope(self) -> None:
        response = self.client.get("/api/v1/profiles/999")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "profile_not_found")
        self.assertIsInstance(body["fields"], list)

    def test_update_missing_profile_uses_same_not_found_envelope(self) -> None:
        response = self.client.patch("/api/v1/profiles/999", json={"name": "Updated"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "profile_not_found")

    def test_invalid_upload_uses_cv_validation_envelope(self) -> None:
        response = self.client.post(
            "/api/v1/profiles/upload",
            files={"file": ("resume.txt", b"not a supported cv", "text/plain")},
        )
        self.assertEqual(response.status_code, 422)
        body = response.json()["error"]
        self.assertEqual(body["code"], "cv_validation_error")
        self.assertEqual(body["fields"][0]["field"], "file")

    def test_upload_returns_422_when_parser_unavailable(self) -> None:
        from unittest.mock import patch
        from app.cv_profile import CVParserUnavailable

        with patch("app.factory.ProfileService.ingest_cv", side_effect=CVParserUnavailable("no parser")):
            response = self.client.post(
                "/api/v1/profiles/upload",
                files={"file": ("resume.pdf", b"%PDF-1.4 junk", "application/pdf")},
            )
        self.assertEqual(response.status_code, 422)
        body = response.json()["error"]
        self.assertEqual(body["code"], "cv_validation_error")

    def test_upload_rejects_oversized_file(self) -> None:
        large = b"%PDF-1.7\n" + b"x" * (10 * 1024 * 1024 + 1)
        response = self.client.post(
            "/api/v1/profiles/upload",
            files={"file": ("resume.pdf", large, "application/pdf")},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "cv_validation_error")

    def test_invalid_preference_payload_uses_validation_envelope(self) -> None:
        response = self.client.put(
            "/api/v1/profiles/999/preferences",
            json={"salary_min": -1},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_error")


if __name__ == "__main__":
    unittest.main()
