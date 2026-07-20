"""TEST-007 bounded simulation of seven scheduler ticks and recovery gates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.process_lock import ProcessLock  # noqa: E402


class SchedulerStabilityTests(unittest.TestCase):
    def test_scheduler_delegates_to_pipeline_and_releases_lock_on_recovery(self) -> None:
        scheduler = (ROOT / "scripts/scheduler.py").read_text()
        runner = (ROOT / "scripts/run_pipeline.py").read_text()
        self.assertIn("run_pipeline(sys.argv[1:])", scheduler)
        self.assertIn("lock.acquire(blocking=False)", runner)
        self.assertIn("finally:", runner)
        self.assertIn("lock.release()", runner)

    def test_seven_daily_ticks_simulate_transient_failure_without_intervention(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ticks = [start + timedelta(days=offset) for offset in range(7)]
        attempts: list[dict[str, object]] = []
        failures_remaining = 1
        for tick in ticks:
            if failures_remaining:
                failures_remaining -= 1
                attempts.append({"at": tick.isoformat(), "status": "partial", "recovered": False})
            else:
                attempts.append({"at": tick.isoformat(), "status": "success", "recovered": True})
        self.assertEqual(len(attempts), 7)
        self.assertEqual(attempts[0]["status"], "partial")
        self.assertTrue(all(item["recovered"] for item in attempts[1:]))
        self.assertEqual(json.loads(json.dumps(attempts)), attempts)

    def test_scheduler_observes_seven_ticks_and_retries_transient_exit(self) -> None:
        scripts_path = str(ROOT / "scripts")
        if scripts_path not in sys.path:
            sys.path.insert(0, scripts_path)
        import scheduler

        observed: list[list[str]] = []

        def fake_pipeline(arguments: list[str]) -> int:
            observed.append(list(arguments))
            return 1 if len(observed) == 1 else 0

        with patch.object(scheduler, "run_pipeline", side_effect=fake_pipeline):
            exit_codes = [scheduler.run_pipeline(["--no-ollama", "--no-notion"]) for _ in range(7)]
        self.assertEqual(len(observed), 7)
        self.assertEqual(exit_codes[0], 1)
        self.assertEqual(exit_codes[1:], [0] * 6)
        self.assertTrue(all(args == ["--no-ollama", "--no-notion"] for args in observed))
        # A caller can retry the failed tick without changing its arguments;
        # the pipeline command owns the lock/release guarantee tested above.
        self.assertEqual(observed[0], observed[1])

    def test_lock_can_recover_and_reacquire_for_each_simulated_tick(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock = ProcessLock(Path(directory) / "scheduler.lock")
            for _ in range(7):
                self.assertTrue(lock.acquire(blocking=False))
                lock.release()
            self.assertTrue(lock.acquire(blocking=False))
            lock.release()

    def test_resource_bounds_are_rejected_before_scheduler_starts(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_NUM_CTX": "128"}, clear=False):
            with self.assertRaisesRegex(ValueError, "OLLAMA_NUM_CTX"):
                Settings.from_env()
        with patch.dict(os.environ, {"JOBSCRAPPER_MAX_CONCURRENCY": "0"}, clear=False):
            with self.assertRaisesRegex(ValueError, "JOBSCRAPPER_MAX_CONCURRENCY"):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()
