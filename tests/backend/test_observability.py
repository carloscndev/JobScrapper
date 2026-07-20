"""Offline tests for OPS-004 logging and bounded runtime settings."""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.observability import JsonFormatter, configure_logging, redact


class ObservabilityTests(unittest.TestCase):
    def test_redact_hides_secret_keys_and_bearer_values(self) -> None:
        value = {"token": "do-not-log", "headers": {"authorization": "Bearer abc123"}}
        self.assertEqual(redact(value), {"token": "[REDACTED]", "headers": {"authorization": "[REDACTED]"}})
        self.assertIn("Bearer [REDACTED]", redact("Authorization: Bearer abc123"))

    def test_formatter_is_json_and_redacts_structured_fields(self) -> None:
        record = logging.LogRecord("jobscrapper", logging.INFO, "", 1, "pipeline", (), None)
        record.event = "pipeline_finished"
        record.run_id = "run-1"
        record.credential = "do-not-log"
        payload = json.loads(JsonFormatter().format(record))
        self.assertEqual(payload["event"], "pipeline_finished")
        self.assertEqual(payload["run_id"], "run-1")
        self.assertNotIn("do-not-log", json.dumps(payload))

    def test_rotating_file_handler_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobscrapper.log"
            logger = configure_logging(path=str(path), max_bytes=1024, backup_count=1)
            logger.info("probe", extra={"event": "test"})
            for index in range(30):
                logger.info("rotation-%s", index, extra={"event": "test"})
            for handler in logger.handlers:
                handler.flush()
            payload = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(payload["event"], "test")
            self.assertTrue(Path(f"{path}.1").exists())

    def test_concurrency_and_log_bounds_are_validated(self) -> None:
        for name in ("JOBSCRAPPER_MAX_CONCURRENCY", "JOBSCRAPPER_LOG_MAX_BYTES", "JOBSCRAPPER_LOG_BACKUP_COUNT"):
            old = os.environ.get(name)
            os.environ[name] = "0"
            try:
                with self.assertRaises(ValueError):
                    Settings.from_env()
            finally:
                if old is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = old


if __name__ == "__main__":
    unittest.main()
