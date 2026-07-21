"""Test that source kinds resolve to the correct adapters in pipeline and factory.

API-006: Fix adapter lookup — map source kind to adapter name.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class FakeAdapter:
    def __init__(self, name: str) -> None:
        self.name = name

    def fetch(self, config):
        return None


FAKE_ADAPTERS = (FakeAdapter("json-api-feed"), FakeAdapter("greenhouse-career-page"), FakeAdapter("lever-career-page"))


class PipelineAdapterLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.pipeline import JobPipeline
        session = MagicMock()
        self.pipeline = JobPipeline(session, adapters=FAKE_ADAPTERS)

    def _source(self, kind: str, name: str = "test-source", config: dict | None = None) -> MagicMock:
        source = MagicMock()
        source.kind = kind
        source.name = name
        source.config = config or {}
        source.base_url = "https://example.com"
        source.terms_url = None
        source.timeout_seconds = 20
        source.requests_per_minute = 30
        source.max_retries = 2
        return source

    def test_api_kind_resolves_to_json_api_feed(self) -> None:
        source = self._source("api")
        adapter = self.pipeline._adapter(source, {})
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "json-api-feed")

    def test_feed_kind_resolves_to_json_api_feed(self) -> None:
        source = self._source("feed")
        adapter = self.pipeline._adapter(source, {})
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "json-api-feed")

    def test_career_page_kind_returns_none(self) -> None:
        source = self._source("career_page")
        adapter = self.pipeline._adapter(source, {})
        self.assertIsNone(adapter)

    def test_config_adapter_override_is_respected(self) -> None:
        source = self._source("career_page", config={"adapter": "greenhouse-career-page"})
        adapter = self.pipeline._adapter(source, source.config)
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "greenhouse-career-page")

    def test_source_name_matching_adapter_name(self) -> None:
        source = self._source("api", name="json-api-feed")
        adapter = self.pipeline._adapter(source, {})
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "json-api-feed")

    def test_config_adapter_takes_precedence_over_kind(self) -> None:
        source = self._source("api", config={"adapter": "greenhouse-career-page"})
        adapter = self.pipeline._adapter(source, source.config)
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "greenhouse-career-page")


class FactoryAdapterLookupTests(unittest.TestCase):
    def test_factory_refresh_uses_same_kind_mapping(self) -> None:
        from app.connectors import DEFAULT_ADAPTERS

        def _resolve(kind: str, adapter_override: str | None = None) -> str | None:
            _KIND_MAP = {"api": "json-api-feed", "feed": "json-api-feed"}
            name = adapter_override or "unimportant-name"
            adapter = next((item for item in DEFAULT_ADAPTERS if item.name == name), None)
            if adapter is None:
                mapped = _KIND_MAP.get(kind)
                adapter = next((item for item in DEFAULT_ADAPTERS if item.name == (mapped or kind)), None)
            return adapter.name if adapter else None

        self.assertEqual(_resolve("api"), "json-api-feed")
        self.assertEqual(_resolve("feed"), "json-api-feed")
        self.assertIsNone(_resolve("career_page"))
        self.assertEqual(_resolve("api", "greenhouse-career-page"), "greenhouse-career-page")


if __name__ == "__main__":
    unittest.main()
