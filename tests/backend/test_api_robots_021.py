"""API-021 Ashby API-host robots fallback regressions."""

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


def _http_error(url: str, status: int) -> HTTPError:
    return HTTPError(url, status, "robots error", {}, None)


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is required to import connector runtime")
class AshbyRobotsFallback021Tests(unittest.TestCase):
    def setUp(self) -> None:
        from app import connectors

        self.connectors = connectors
        self.user_agent = "JobScrapperTest/2.1"
        self.public_policy = "User-agent: *\nDisallow: /api\nDisallow: /meeting\nAllow: /\n"

    def test_api_401_uses_public_ashby_policy_with_same_user_agent_and_allows_kueski(self) -> None:
        target = "https://api.ashbyhq.com/posting-api/job-board/kueski"
        protected = _http_error("https://api.ashbyhq.com/robots.txt", 401)
        try:
            with patch.object(
                self.connectors.urllib.request,
                "urlopen",
                side_effect=(protected, _Response(self.public_policy)),
            ) as urlopen:
                self.connectors._robots_check(target, self.user_agent)

            self.assertEqual(urlopen.call_count, 2)
            requests = [entry.args[0] for entry in urlopen.call_args_list]
            self.assertEqual(
                [request.full_url for request in requests],
                ["https://api.ashbyhq.com/robots.txt", "https://jobs.ashbyhq.com/robots.txt"],
            )
            self.assertEqual([request.get_header("User-agent") for request in requests], [self.user_agent] * 2)
            self.assertEqual([entry.kwargs["timeout"] for entry in urlopen.call_args_list], [10, 10])
        finally:
            protected.close()

    def test_public_policy_disallowing_api_or_meeting_remains_blocked(self) -> None:
        for path in ("/api/private", "/meeting/interview"):
            protected = _http_error("https://api.ashbyhq.com/robots.txt", 401)
            try:
                with self.subTest(path=path), patch.object(
                    self.connectors.urllib.request,
                    "urlopen",
                    side_effect=(protected, _Response(self.public_policy)),
                ):
                    with self.assertRaisesRegex(PermissionError, "robots.txt disallows fetching"):
                        self.connectors._robots_check(f"https://api.ashbyhq.com{path}", self.user_agent)
            finally:
                protected.close()

    def test_public_policy_fallback_failures_fail_closed(self) -> None:
        target = "https://api.ashbyhq.com/posting-api/job-board/kueski"
        fallback_failures = (
            _http_error("https://jobs.ashbyhq.com/robots.txt", 403),
            _http_error("https://jobs.ashbyhq.com/robots.txt", 500),
            URLError("public robots unavailable"),
        )
        for public_failure in fallback_failures:
            protected = _http_error("https://api.ashbyhq.com/robots.txt", 401)
            try:
                with self.subTest(failure=repr(public_failure)), patch.object(
                    self.connectors.urllib.request,
                    "urlopen",
                    side_effect=(protected, public_failure),
                ):
                    with self.assertRaisesRegex(RuntimeError, "could not verify Ashby public robots.txt"):
                        self.connectors._robots_check(target, self.user_agent)
            finally:
                protected.close()
                close = getattr(public_failure, "close", None)
                if close is not None:
                    close()

    def test_non_ashby_401_remains_denied_without_fallback(self) -> None:
        target = "https://api.example.com/jobs"
        protected = _http_error("https://api.example.com/robots.txt", 401)
        try:
            with patch.object(self.connectors.urllib.request, "urlopen", side_effect=protected) as urlopen:
                with self.assertRaisesRegex(PermissionError, "robots.txt denied access"):
                    self.connectors._robots_check(target, self.user_agent)
            self.assertEqual(urlopen.call_count, 1)
            self.assertEqual(urlopen.call_args.args[0].full_url, "https://api.example.com/robots.txt")
        finally:
            protected.close()


if __name__ == "__main__":
    unittest.main()
