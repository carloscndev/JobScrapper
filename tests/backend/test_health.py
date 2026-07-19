"""Stdlib tests for the BACKEND-001 FastAPI bootstrap.

Backend dependencies are intentionally not required by the harness Python
environment. Configuration and metadata checks always run; the HTTP route
check uses ``skipTest`` with an explicit reason when FastAPI is unavailable.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tomllib
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def _import_backend(module_name: str):
    """Import a backend package module from its source directory."""

    backend_text = str(BACKEND)
    if backend_text not in sys.path:
        sys.path.insert(0, backend_text)
    return __import__(module_name, fromlist=["*"])


def _load_config_without_package_import():
    """Load settings directly so tests do not require FastAPI."""

    path = BACKEND / "app" / "config.py"
    spec = importlib.util.spec_from_file_location("jobscrapper_test_config", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load backend settings module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BackendBootstrapTests(unittest.TestCase):
    def test_settings_module_is_loadable_without_optional_http_dependencies(self) -> None:
        config = _load_config_without_package_import()
        with mock.patch.dict(os.environ, {}, clear=False):
            for key in ("JOBSCRAPPER_PORT", "JOBSCRAPPER_APP_NAME", "JOBSCRAPPER_ENV", "JOBSCRAPPER_HOST"):
                os.environ.pop(key, None)
            settings = config.Settings.from_env()

        self.assertEqual(settings.app_name, "JobScrapper API")
        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 8000)

    def test_settings_overrides_and_rejects_invalid_ports(self) -> None:
        config = _load_config_without_package_import()
        with mock.patch.dict(
            os.environ,
            {
                "JOBSCRAPPER_PORT": "9001",
                "JOBSCRAPPER_APP_NAME": "Test API",
                "JOBSCRAPPER_ENV": "test",
                "JOBSCRAPPER_HOST": "0.0.0.0",
            },
            clear=False,
        ):
            settings = config.Settings.from_env()
            self.assertEqual((settings.app_name, settings.environment, settings.host, settings.port), ("Test API", "test", "0.0.0.0", 9001))

            os.environ["JOBSCRAPPER_PORT"] = "not-a-port"
            with self.assertRaisesRegex(ValueError, "must be an integer"):
                config.Settings.from_env()

            os.environ["JOBSCRAPPER_PORT"] = "70000"
            with self.assertRaisesRegex(ValueError, "between 1 and 65535"):
                config.Settings.from_env()

    def test_pyproject_declares_fastapi_service_metadata(self) -> None:
        metadata = tomllib.loads((BACKEND / "pyproject.toml").read_text())
        project = metadata["project"]

        self.assertEqual(project["name"], "jobscrapper-api")
        self.assertEqual(project["version"], "0.1.0")
        self.assertTrue(any(dependency.startswith("fastapi") for dependency in project["dependencies"]))

    def test_backend_readme_documents_health_endpoint(self) -> None:
        readme = (BACKEND / "README.md").read_text()

        self.assertIn("http://127.0.0.1:8000/health", readme)
        self.assertIn("JOBSCRAPPER_PORT", readme)

    def test_health_route_returns_liveness_payload(self) -> None:
        """Exercise /health only when FastAPI is installed."""

        if importlib.util.find_spec("fastapi") is None:
            self.skipTest("FastAPI is not installed; static backend checks still run")

        factory = _import_backend("app.factory")
        config = _import_backend("app.config")
        app = factory.create_app(config.Settings(app_name="Test API", environment="test"))
        health_route = next(route for route in app.routes if getattr(route, "path", None) == "/health")

        self.assertEqual(
            health_route.endpoint(),
            {"status": "ok", "service": "Test API", "environment": "test"},
        )


if __name__ == "__main__":
    unittest.main()
