"""Contract tests for API-003/API-004 operational endpoints.

The repository's lightweight test environment may not have the HTTP stack
installed.  Static contract assertions therefore always run, while FastAPI
tests are explicitly skipped until the optional runtime dependencies exist.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FACTORY = BACKEND / "app" / "factory.py"
REPOSITORIES = BACKEND / "app" / "repositories.py"


def _import_backend(module_name: str):
    backend_text = str(BACKEND)
    if backend_text not in sys.path:
        sys.path.insert(0, backend_text)
    return __import__(module_name, fromlist=["*"])


class OperationsContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = FACTORY.read_text()

    def test_operations_routes_and_tags_are_declared(self) -> None:
        expected = (
            '"/api/v1/sources"', '"/api/v1/sources/{source_id}"',
            '"/api/v1/executions"', '"/api/v1/executions/{run_id}"',
            '"/api/v1/metrics"', '"/api/v1/operations/health"',
            '"/api/v1/health"', '"/api/v1/operations/refresh"',
        )
        for path in expected:
            self.assertIn(path, self.source)
        self.assertGreaterEqual(self.source.count('tags=["operations"]'), 9)

    def test_source_create_and_update_payloads_have_required_fields(self) -> None:
        for field in ('"name"', '"kind"', '"base_url"', '"enabled"'):
            self.assertIn(field, self.source)
        self.assertIn("SourceCreatePayload", self.source)
        self.assertIn("SourceUpdatePayload", self.source)

    def test_source_endpoints_use_source_service_and_repository(self) -> None:
        self.assertIn("SourceService(SourceRepository(db)).configure(config)", self.source)
        self.assertIn("SourceRepository(db).get_by_id(source_id)", self.source)
        self.assertIn("source_not_found", self.source)

    def test_source_repository_has_get_by_id_method(self) -> None:
        source = REPOSITORIES.read_text()
        self.assertIn("def get_by_id(self, source_id: int)", source)
        self.assertIn("return self.session.get(Source, source_id)", source)

    def test_refresh_lock_returns_structured_conflict(self) -> None:
        self.assertIn("refresh_lock.acquire(blocking=False)", self.source)
        self.assertIn("status_code=409", self.source)
        self.assertIn('"code": "refresh_in_progress"', self.source)
        self.assertIn("finally:", self.source)
        self.assertIn("refresh_lock.release()", self.source)

    def test_health_metrics_and_execution_payloads_include_contract_fields(self) -> None:
        for field in ("api", "database", "ollama", "notion", "checked_at"):
            self.assertIn(f'"{field}"', self.source)
        for field in ("jobs", "sources", "executions", "generated_at"):
            self.assertIn(f'"{field}"', self.source)
        for field in ("run_id", "status", "metrics", "source_runs"):
            self.assertIn(f'"{field}"', self.source)

    def test_http_contract_and_openapi_when_dependencies_are_available(self) -> None:
        if importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("sqlalchemy") is None:
            self.skipTest("FastAPI/SQLAlchemy are not installed; static contract checks still run")

        factory = _import_backend("app.factory")
        config = _import_backend("app.config")
        app = factory.create_app(config.Settings(database_url="sqlite:///:memory:", environment="test"))
        paths = {route.path for route in app.routes}
        self.assertIn("/api/v1/operations/refresh", paths)
        self.assertIn("/api/v1/metrics", paths)
        schema = app.openapi()
        self.assertIn("/api/v1/operations/refresh", schema["paths"])
        operation_tags = [
            tag
            for path_item in schema["paths"].values()
            for operation in path_item.values()
            if isinstance(operation, dict)
            for tag in operation.get("tags", [])
        ]
        self.assertIn("operations", schema.get("tags", operation_tags))

        manual = next(route.endpoint for route in app.routes if route.path == "/api/v1/operations/refresh")
        lock = app.state.refresh_lock
        self.assertTrue(lock.acquire(blocking=False))
        try:
            with self.assertRaises(Exception) as raised:
                manual()
            self.assertEqual(getattr(raised.exception, "status_code", None), 409)
        finally:
            lock.release()


try:
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.factory import create_app

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


@unittest.skipUnless(HTTP_AVAILABLE, "FastAPI/SQLAlchemy dependencies are not installed")
class OperationsNotFoundHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = ROOT / ".tmp-api-operations-test.db"
        self.db_path.unlink(missing_ok=True)
        settings = Settings(database_url=f"sqlite:///{self.db_path}", environment="test")
        self.client = TestClient(create_app(settings))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.client.close()
        self.db_path.unlink(missing_ok=True)

    def test_missing_source_returns_source_not_found_on_update(self) -> None:
        response = self.client.patch("/api/v1/sources/999", json={"name": "Updated"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "source_not_found")

    def test_missing_source_returns_source_not_found_on_delete(self) -> None:
        response = self.client.delete("/api/v1/sources/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "source_not_found")

    def test_missing_execution_returns_execution_not_found(self) -> None:
        response = self.client.get("/api/v1/executions/00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "execution_not_found")


@unittest.skipUnless(HTTP_AVAILABLE, "FastAPI/SQLAlchemy dependencies are not installed")
class CorsHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = ROOT / ".tmp-api-cors-test.db"
        self.db_path.unlink(missing_ok=True)
        settings = Settings(database_url=f"sqlite:///{self.db_path}", environment="test")
        self.client = TestClient(create_app(settings))
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.client.close()
        self.db_path.unlink(missing_ok=True)

    def test_cors_headers_on_options_request(self) -> None:
        response = self.client.options("/api/v1/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
        self.assertIn("access-control-allow-origin", response.headers)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")

    def test_cors_headers_on_get_request(self) -> None:
        response = self.client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
        self.assertIn("access-control-allow-origin", response.headers)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")


if __name__ == "__main__":
    unittest.main()
