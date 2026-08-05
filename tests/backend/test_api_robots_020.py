"""API-020 robots.txt regressions for remote Ashby sources."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


class _Response:
    def __init__(self, body: str) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body.encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is required to import connector runtime")
class RobotsPolicy020Tests(unittest.TestCase):
    def setUp(self) -> None:
        from app import connectors

        self.connectors = connectors
        self.job_url = "https://jobs.ashbyhq.com/kueski/backend-engineer"
        self.user_agent = "JobScrapperTest/2.0"

    def test_allowed_ashby_path_uses_origin_robots_url_and_identifiable_user_agent(self) -> None:
        policy = "User-agent: *\nDisallow: /\nAllow: /kueski/\n"
        with patch.object(self.connectors.urllib.request, "urlopen", return_value=_Response(policy)) as urlopen:
            self.connectors._robots_check(self.job_url, self.user_agent)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://jobs.ashbyhq.com/robots.txt")
        self.assertEqual(request.get_header("User-agent"), self.user_agent)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 10)

    def test_explicit_disallow_remains_fail_closed(self) -> None:
        policy = "User-agent: *\nDisallow: /kueski/\n"
        with patch.object(self.connectors.urllib.request, "urlopen", return_value=_Response(policy)):
            with self.assertRaisesRegex(PermissionError, "robots.txt disallows fetching"):
                self.connectors._robots_check(self.job_url, self.user_agent)

    def test_404_means_no_published_policy_and_allows_fetch(self) -> None:
        missing = HTTPError("https://jobs.ashbyhq.com/robots.txt", 404, "Not Found", {}, None)
        try:
            with patch.object(self.connectors.urllib.request, "urlopen", side_effect=missing):
                self.connectors._robots_check(self.job_url, self.user_agent)
        finally:
            missing.close()

    def test_auth_denials_remain_fail_closed(self) -> None:
        for status in (401, 403):
            denial = HTTPError("https://jobs.ashbyhq.com/robots.txt", status, "Denied", {}, None)
            try:
                with self.subTest(status=status), patch.object(self.connectors.urllib.request, "urlopen", side_effect=denial):
                    with self.assertRaisesRegex(PermissionError, "robots.txt denied access"):
                        self.connectors._robots_check(self.job_url, self.user_agent)
            finally:
                denial.close()

    def test_server_errors_and_network_failures_remain_fail_closed(self) -> None:
        failures = (
            HTTPError("https://jobs.ashbyhq.com/robots.txt", 500, "Server Error", {}, None),
            HTTPError("https://jobs.ashbyhq.com/robots.txt", 503, "Unavailable", {}, None),
            URLError("network unavailable"),
        )
        for failure in failures:
            try:
                with self.subTest(failure=repr(failure)), patch.object(
                    self.connectors.urllib.request, "urlopen", side_effect=failure
                ):
                    with self.assertRaisesRegex(RuntimeError, "could not verify robots.txt"):
                        self.connectors._robots_check(self.job_url, self.user_agent)
            finally:
                close = getattr(failure, "close", None)
                if close is not None:
                    close()


if __name__ == "__main__":
    unittest.main()
