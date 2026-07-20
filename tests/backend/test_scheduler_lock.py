"""Tests for OPS-003 scheduling and cross-process locking guarantees."""
from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.process_lock import ProcessLock


def _hold_lock(path: str, ready: multiprocessing.Queue, release: multiprocessing.Event) -> None:
    lock = ProcessLock(path)
    ready.put(lock.acquire(blocking=False))
    release.wait(timeout=10)
    lock.release()


class SchedulerLockTests(unittest.TestCase):
    def test_default_lock_is_repository_relative(self) -> None:
        expected = ROOT / "data" / "jobscrapper.pipeline.lock"
        previous = Path.cwd()
        try:
            os.chdir(tempfile.gettempdir())
            self.assertEqual(ProcessLock().path, expected)
        finally:
            os.chdir(previous)

    def test_second_process_cannot_acquire_lock_until_first_releases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "pipeline.lock")
            ready: multiprocessing.Queue = multiprocessing.Queue()
            release = multiprocessing.Event()
            holder = multiprocessing.Process(target=_hold_lock, args=(path, ready, release))
            holder.start()
            self.assertTrue(ready.get(timeout=5))
            contender = ProcessLock(path)
            self.assertFalse(contender.acquire(blocking=False))
            release.set()
            holder.join(timeout=5)
            self.assertEqual(holder.exitcode, 0)
            self.assertTrue(contender.acquire(blocking=False))
            contender.release()

    def test_scheduler_help_and_cron_example_document_daily_run(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "scheduler.py"), "--help"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--profile-id", result.stdout)
        cron = (ROOT / "scripts" / "jobscrapper.cron.example").read_text(encoding="utf-8")
        self.assertIn("scripts/scheduler.py", cron)
        self.assertIn("17 2", cron)

    def test_pipeline_reports_skip_and_exit_75_when_lock_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock_path = str(Path(directory) / "pipeline.lock")
            lock = ProcessLock(lock_path)
            self.assertTrue(lock.acquire(blocking=False))
            try:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "run_pipeline.py"), "--no-ollama", "--no-notion"],
                    cwd=ROOT, env={**os.environ, "JOBSCRAPPER_LOCK_FILE": lock_path},
                    capture_output=True, text=True, check=False,
                )
            finally:
                lock.release()
            self.assertEqual(result.returncode, 75, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "skipped")
            self.assertEqual(payload["reason"], "pipeline_in_progress")


try:
    import fastapi  # noqa: F401
    import sqlalchemy  # noqa: F401
    API_DEPS = True
except ImportError:
    API_DEPS = False


@unittest.skipUnless(API_DEPS, "FastAPI and SQLAlchemy are not installed")
class ApiLockTests(unittest.TestCase):
    def test_manual_refresh_returns_409_while_scheduler_lock_is_held(self) -> None:
        from fastapi.testclient import TestClient
        from app.config import Settings
        from app.factory import create_app

        with tempfile.TemporaryDirectory() as directory:
            lock_path = str(Path(directory) / "pipeline.lock")
            os.environ["JOBSCRAPPER_LOCK_FILE"] = lock_path
            try:
                app = create_app(Settings(database_url=f"sqlite:///{Path(directory) / 'db.sqlite'}"))
                lock = ProcessLock(lock_path)
                self.assertTrue(lock.acquire(blocking=False))
                try:
                    with TestClient(app) as client:
                        response = client.post("/api/v1/refresh")
                    self.assertEqual(response.status_code, 409)
                    self.assertEqual(response.json()["error"]["code"], "refresh_in_progress")
                finally:
                    lock.release()
            finally:
                os.environ.pop("JOBSCRAPPER_LOCK_FILE", None)


if __name__ == "__main__":
    unittest.main()
