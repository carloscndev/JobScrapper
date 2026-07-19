"""Contract and runtime tests for SOURCES-001 source ingestion primitives."""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SOURCES = BACKEND / "app" / "sources.py"


def _available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _source_module():
    backend_path = str(BACKEND)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    return __import__("app.sources", fromlist=["*"])


class SourceContractTests(unittest.TestCase):
    def test_source_module_declares_required_contracts(self) -> None:
        tree = ast.parse(SOURCES.read_text(), filename=str(SOURCES))
        classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        self.assertTrue(
            {"SourceConfig", "NormalizedJob", "SourceFetchResult", "SourceAdapter", "SourceService"}.issubset(classes)
        )
        source = SOURCES.read_text()
        for name in ("timeout_seconds", "requests_per_minute", "max_retries", "description_url", "application_url", "canonical_url"):
            self.assertIn(name, source)
        self.assertNotIn("fastapi", source)

    @unittest.skipUnless(_available("sqlalchemy"), "SQLAlchemy is required for runtime source tests")
    def test_source_config_validates_urls_and_limits(self) -> None:
        module = _source_module()
        config = module.SourceConfig(
            name="Example", base_url="https://jobs.example", terms_url="http://example/terms",
            timeout_seconds=5, requests_per_minute=10, max_retries=1,
            settings={"token_ref": "JOBS_TOKEN"},
        )
        self.assertEqual(config.settings["token_ref"], "JOBS_TOKEN")
        for kwargs in ({"base_url": "ftp://jobs.example"}, {"timeout_seconds": 0}, {"requests_per_minute": 0}, {"max_retries": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                module.SourceConfig(name="x", **kwargs)

    @unittest.skipUnless(_available("sqlalchemy"), "SQLAlchemy is required for runtime source tests")
    def test_normalized_job_requires_safe_urls_and_exposes_canonical(self) -> None:
        module = _source_module()
        job = module.NormalizedJob(
            title="Backend Engineer", company="Acme", description="Build APIs",
            description_url="https://example/jobs/1", application_url="https://apply.example/1",
            canonical_url="https://example/jobs/1?ref=source", published_at=date(2026, 7, 18),
        )
        self.assertEqual(job.effective_canonical_url, "https://example/jobs/1?ref=source")
        fallback = module.NormalizedJob(title="x", company="y", description="z", description_url="https://x")
        self.assertEqual(fallback.effective_canonical_url, "https://x")
        with self.assertRaises(ValueError):
            module.NormalizedJob(title="x", company="y", description="z", description_url="javascript:alert(1)")
        with self.assertRaises(ValueError):
            module.NormalizedJob(title="x", company="y", description="z", description_url="https://x", salary_min=2, salary_max=1)

    @unittest.skipUnless(_available("sqlalchemy"), "SQLAlchemy is required for runtime source tests")
    def test_fetch_result_statuses_cover_success_partial_and_failure(self) -> None:
        module = _source_module()
        job = module.NormalizedJob(title="x", company="y", description="z", description_url="https://x")
        now = datetime.now(timezone.utc)
        self.assertEqual(module.SourceFetchResult(fetched_at=now).status, "success")
        self.assertEqual(module.SourceFetchResult(jobs=[job], error="one failed").status, "partial")
        self.assertEqual(module.SourceFetchResult(error="unavailable").status, "failed")
        self.assertEqual(module.SourceFetchResult(fetched_at=now).fetched_at, now)

    @unittest.skipUnless(_available("sqlalchemy"), "SQLAlchemy is required for runtime source tests")
    def test_adapter_is_abstract_and_requires_name_and_fetch(self) -> None:
        module = _source_module()
        with self.assertRaises(TypeError):
            module.SourceAdapter()  # type: ignore[abstract]

        class Adapter(module.SourceAdapter):
            @property
            def name(self):
                return "example"

            def fetch(self, config):
                return module.SourceFetchResult()

        self.assertEqual(Adapter().name, "example")

    @unittest.skipUnless(_available("sqlalchemy"), "SQLAlchemy is required for runtime source tests")
    def test_source_service_configures_and_filters_enabled_sources(self) -> None:
        module = _source_module()
        session = Mock()
        records = {}

        class Repository:
            def get(self, name):
                return records.get(name)

            def get_or_create(self, name, **values):
                source = records.get(name)
                if source is None:
                    source = Mock(name=name, **values)
                    records[name] = source
                return source

            def enabled(self):
                return [source for source in records.values() if source.enabled]

            session = session

        service = module.SourceService(Repository())
        service.configure(module.SourceConfig(name="enabled", base_url="https://enabled"))
        service.configure(module.SourceConfig(name="disabled", base_url="https://disabled", enabled=False))
        self.assertEqual([item.name for item in service.list_enabled()], ["enabled"])
        service.set_enabled("enabled", False)
        self.assertEqual(service.list_enabled(), [])
        with self.assertRaises(ValueError):
            service.set_enabled("missing", True)


if __name__ == "__main__":
    unittest.main()
