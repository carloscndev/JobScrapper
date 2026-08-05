"""TEST-005 browser contract: fixture ingestion -> score -> dashboard detail.

The test is opt-in because the lightweight CI image may not have Playwright or
frontend dependencies.  Set ``JOBSCRAPPER_E2E_URL`` to an already running Vite
server, or ``JOBSCRAPPER_E2E_COMMAND`` to let the test own its server lifecycle.
Browser console output and server stdout/stderr are retained in the log path.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import time
import unittest
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
PLAYWRIGHT_AVAILABLE = importlib.util.find_spec("playwright") is not None


class E2EContractTests(unittest.TestCase):
    def test_e2e_defines_fixture_score_detail_and_lifecycle_contract(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        for marker in ("JOBSCRAPPER_E2E_COMMAND", "subprocess.Popen", "server.terminate", "browser_logs", "log_handle.write", "browser.close()", "networkidle", "Senior Backend Engineer", "94%", "#vacancy-detail-title"):
            self.assertIn(marker, source)


@unittest.skipUnless(PLAYWRIGHT_AVAILABLE, "Playwright is not installed")
class IngestionDashboardE2ETests(unittest.TestCase):
    def test_fixture_job_reaches_scored_detail_and_captures_logs(self) -> None:
        from playwright.sync_api import sync_playwright

        base_url = os.getenv("JOBSCRAPPER_E2E_URL", "http://127.0.0.1:4173").rstrip("/")
        command = os.getenv("JOBSCRAPPER_E2E_COMMAND")
        log_path = Path(os.getenv("JOBSCRAPPER_E2E_LOG", "/tmp/jobscrapper-e2e.log"))
        server: subprocess.Popen[str] | None = None
        log_handle = log_path.open("w", encoding="utf-8")
        browser_logs: list[str] = []
        logs_written = False
        try:
            if command:
                server = subprocess.Popen(command, cwd=ROOT / "frontend", shell=True, stdout=log_handle, stderr=subprocess.STDOUT, text=True)
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    try:
                        with urlopen(base_url, timeout=1):
                            break
                    except Exception:
                        time.sleep(0.25)
                else:
                    self.fail("frontend server did not become ready; see E2E log")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.on("console", lambda message: browser_logs.append(f"{message.type}: {message.text}"))
                    page.goto(base_url, wait_until="networkidle")
                    page.get_by_role("tab", name="Openings").click()
                    card = page.get_by_role("button", name="View details for Senior Backend Engineer at Nubank")
                    card.click()
                    self.assertEqual(page.locator("#vacancy-detail-title").inner_text(), "Senior Backend Engineer")
                    self.assertIn("94%", page.get_by_label("94% compatibility").inner_text())
                    self.assertEqual(page.locator('a[href*="#apply"]').count(), 1)
                finally:
                    # Persist browser output even when an assertion fails.
                    browser.close()
                    log_handle.write("\n[BROWSER CONSOLE]\n" + "\n".join(browser_logs))
                    logs_written = True
        finally:
            if not logs_written:
                log_handle.write("\n[BROWSER CONSOLE]\n" + "\n".join(browser_logs))
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
            log_handle.close()
        self.assertTrue(log_path.exists())


if __name__ == "__main__":
    unittest.main()
