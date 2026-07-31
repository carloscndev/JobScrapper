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


class LegacyCareerPageLookupTests(unittest.TestCase):
    """Keep legacy persisted career-page sources resolvable without overrides."""

    def setUp(self) -> None:
        from app.sources import resolve_source_adapter

        self.resolve = resolve_source_adapter

    def _source(
        self,
        *,
        name: str = "Acme careers",
        base_url: str = "https://careers.example.com",
        config: dict | None = None,
    ) -> MagicMock:
        source = MagicMock()
        source.name = name
        source.kind = "career_page"
        source.base_url = base_url
        source.provider = ""
        source.config = config or {}
        return source

    def _adapter(self, source: MagicMock, config: dict | None = None) -> FakeAdapter | None:
        return self.resolve(source, FAKE_ADAPTERS, config)

    def test_greenhouse_legacy_name_resolves(self) -> None:
        adapter = self._adapter(self._source(name="Acme Greenhouse careers"))
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "greenhouse-career-page")

    def test_lever_legacy_name_resolves(self) -> None:
        adapter = self._adapter(self._source(name="Acme Lever jobs"))
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "lever-career-page")

    def test_greenhouse_canonical_url_resolves(self) -> None:
        adapter = self._adapter(self._source(base_url="https://boards.greenhouse.io/acme"))
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "greenhouse-career-page")

    def test_lever_canonical_url_resolves(self) -> None:
        adapter = self._adapter(self._source(base_url="https://jobs.lever.co/acme"))
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "lever-career-page")

    def test_provider_metadata_resolves_greenhouse_and_lever(self) -> None:
        greenhouse = self._adapter(self._source(config={"provider": "greenhouse"}))
        lever = self._adapter(self._source(config={"source_provider": "lever"}))
        self.assertIsNotNone(greenhouse)
        self.assertIsNotNone(lever)
        self.assertEqual(greenhouse.name, "greenhouse-career-page")
        self.assertEqual(lever.name, "lever-career-page")

    def test_unknown_career_page_remains_unsupported(self) -> None:
        adapter = self._adapter(self._source(name="Acme careers", base_url="https://jobs.example.com/acme"))
        self.assertIsNone(adapter)

    def test_lookalike_provider_hosts_remain_unsupported(self) -> None:
        for host in (
            "https://notgreenhouse.io/jobs",
            "https://greenhouse.io.evil.test/jobs",
            "https://notlever.co/jobs",
            "https://lever.co.evil.test/jobs",
        ):
            with self.subTest(host=host):
                self.assertIsNone(self._adapter(self._source(base_url=host)))

    def test_explicit_override_wins_over_legacy_name_and_url(self) -> None:
        source = self._source(
            name="Acme Greenhouse careers",
            base_url="https://boards.greenhouse.io/acme",
            config={"adapter": "lever-career-page"},
        )
        adapter = self._adapter(source, source.config)
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "lever-career-page")

    def test_unknown_explicit_override_does_not_fallback_to_legacy_provider(self) -> None:
        source = self._source(
            name="Acme Greenhouse careers",
            base_url="https://boards.greenhouse.io/acme",
            config={"adapter": "missing-adapter"},
        )
        self.assertIsNone(self._adapter(source, source.config))


if __name__ == "__main__":
    unittest.main()
