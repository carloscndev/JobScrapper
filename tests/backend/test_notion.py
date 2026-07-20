"""Offline contract tests for NOTION-001 configuration and schema."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.notion import NOTION_JOB_SCHEMA, NotionConfig, regional_views, schema_for_data_source  # noqa: E402


class NotionContractTests(unittest.TestCase):
    def test_credentials_are_environment_references_and_redacted(self) -> None:
        config = NotionConfig(token_env="TEST_NOTION_TOKEN", database_id_env="TEST_NOTION_DB")
        self.assertNotIn("secret", repr(config).lower())
        self.assertEqual(config.redacted()["token_env"], "TEST_NOTION_TOKEN")
        self.assertEqual(config.redacted()["database_id_env"], "TEST_NOTION_DB")
        self.assertNotIn("tok-value", str(config.redacted()))
        old = {key: os.environ.get(key) for key in ("TEST_NOTION_TOKEN", "TEST_NOTION_DB")}
        try:
            os.environ["TEST_NOTION_TOKEN"] = "tok"
            os.environ["TEST_NOTION_DB"] = "database-id"
            self.assertEqual(config.require_credentials(), ("tok", "database-id"))
            self.assertTrue(config.redacted()["configured"])
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_missing_credentials_fail_before_any_network_client_is_needed(self) -> None:
        config = NotionConfig(token_env="MISSING_NOTION_TOKEN", database_id_env="MISSING_NOTION_DB")
        for key in ("MISSING_NOTION_TOKEN", "MISSING_NOTION_DB"):
            os.environ.pop(key, None)
        with self.assertRaisesRegex(RuntimeError, "MISSING_NOTION_TOKEN"):
            config.require_credentials()
        os.environ["MISSING_NOTION_TOKEN"] = "token"
        try:
            with self.assertRaisesRegex(RuntimeError, "MISSING_NOTION_DB"):
                config.require_credentials()
        finally:
            os.environ.pop("MISSING_NOTION_TOKEN", None)

    def test_schema_maps_normalized_job_fields_and_is_copy_safe(self) -> None:
        schema = schema_for_data_source()
        expected = {
            "Title", "Company", "Region", "Modality", "Location", "Requirements",
            "Salary min", "Salary max", "Salary currency", "Salary period", "Source",
            "Description URL", "Application URL", "Canonical URL", "Published", "Detected",
            "Checked", "Compatibility score", "Score explanation", "Matches", "Gaps",
            "Recommendations", "Status", "Local job ID", "Fingerprint",
        }
        self.assertEqual(set(schema), expected)
        self.assertEqual(set(schema), set(NOTION_JOB_SCHEMA))
        self.assertEqual(schema["Description URL"], {"url": {}})
        self.assertEqual(schema["Application URL"], {"url": {}})
        self.assertEqual(schema["Canonical URL"], {"url": {}})
        self.assertEqual(schema["Compatibility score"], {"number": {"format": "number"}})
        schema["Region"]["select"]["options"].append({"name": "tampered"})
        self.assertNotIn({"name": "tampered"}, schema_for_data_source()["Region"]["select"]["options"])

    def test_regional_views_cover_all_required_buckets(self) -> None:
        views = regional_views()
        self.assertEqual(set(views), {"CDMX", "Guadalajara", "Mexico", "USA", "Other"})
        self.assertEqual({item["select"]["equals"] for item in views.values()}, {"cdmx", "guadalajara", "mexico", "usa", "other"})
        self.assertTrue(all(item["property"] == "Region" for item in views.values()))

    def test_settings_load_notion_environment_configuration_without_secret_values(self) -> None:
        keys = ("NOTION_API_TOKEN_ENV", "NOTION_DATABASE_ID_ENV", "NOTION_API_VERSION", "NOTION_TIMEOUT_SECONDS")
        old = {key: os.environ.get(key) for key in keys}
        try:
            os.environ.update({
                "NOTION_API_TOKEN_ENV": "LOCAL_TOK",
                "NOTION_DATABASE_ID_ENV": "LOCAL_NOTION_DATABASE",
                "NOTION_API_VERSION": "2025-09-03",
                "NOTION_TIMEOUT_SECONDS": "7.5",
            })
            settings = Settings.from_env()
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(settings.notion_api_token_env, "LOCAL_TOK")
        self.assertEqual(settings.notion_database_id_env, "LOCAL_NOTION_DATABASE")
        self.assertEqual(settings.notion_timeout_seconds, 7.5)
        self.assertNotIn("LOCAL_TOK_VALUE", repr(settings))


if __name__ == "__main__":
    unittest.main()
