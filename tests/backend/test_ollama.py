"""Offline contract tests for local Ollama matching analysis."""

from __future__ import annotations

import json
import importlib.util
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.ollama import LocalModelError, OllamaAnalyzer  # noqa: E402


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _Opener:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.request = None
        self.timeout = None

    def __call__(self, request: object, *, timeout: float) -> _Response:
        self.request, self.timeout = request, timeout
        return _Response(self.payload)


class _FailingOpener:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def __call__(self, _request: object, *, timeout: float) -> _Response:
        self.calls += 1
        raise self.error


class OllamaContractTests(unittest.TestCase):
    def test_loopback_only_and_resource_configuration(self) -> None:
        for url in ("https://127.0.0.1:11434", "http://192.168.1.10:11434", "http://127.0.0.1:11434/api/generate"):
            with self.assertRaises(ValueError):
                OllamaAnalyzer(base_url=url)
        opener = _Opener({"response": json.dumps({"summary": "ok", "matches": [], "gaps": [], "recommendations": []})})
        analyzer = OllamaAnalyzer(opener=opener, timeout_seconds=2.5, num_ctx=512, num_thread=3)
        analyzer.analyze({}, {})
        self.assertEqual(opener.timeout, 2.5)
        body = json.loads(opener.request.data)
        self.assertEqual(body["options"], {"num_ctx": 512, "num_thread": 3})

    def test_payload_allowlist_and_explanation_mapping(self) -> None:
        opener = _Opener({"response": json.dumps({"summary": "Strong fit", "matches": ["Python"], "gaps": ["SQL"], "recommendations": ["Practice SQL"]})})
        profile = {"name": "Candidate", "skills": ["Python"], "cv_text": "SECRET", "api_token": "SECRET2", "preferences": {"target_roles": ["Backend"]}}
        job = {"title": "Backend", "company": "Acme", "description": "Build APIs", "metadata_json": {"private": "DO_NOT_SEND"}}
        result = OllamaAnalyzer(opener=opener).analyze(profile, job)
        self.assertEqual(result.summary, "Strong fit")
        self.assertEqual(result.gaps, ["SQL"])
        self.assertEqual(result.recommendations, ["Practice SQL"])
        prompt = json.loads(opener.request.data)["prompt"]
        self.assertFalse(any(secret in prompt for secret in ("SECRET", "SECRET2", "DO_NOT_SEND", "cv_text", "api_token")))

    def test_invalid_structured_output_is_rejected(self) -> None:
        payloads = (
            {"response": "not-json"},
            {"response": json.dumps({"summary": "ok", "matches": "bad", "gaps": [], "recommendations": []})},
            {"response": json.dumps({"summary": "", "matches": [], "gaps": [], "recommendations": []})},
        )
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(LocalModelError):
                OllamaAnalyzer(opener=_Opener(payload)).analyze({}, {})

    def test_timeout_retries_then_reports_local_model_error(self) -> None:
        opener = _FailingOpener(TimeoutError("ollama timed out"))
        analyzer = OllamaAnalyzer(opener=opener, max_retries=1, retry_backoff_seconds=0)
        with patch("app.ollama.time.sleep"):
            with self.assertRaises(LocalModelError):
                analyzer.analyze({}, {})
        self.assertEqual(opener.calls, 2)

    def test_unavailable_model_error_is_converted_to_deterministic_fallback(self) -> None:
        if not importlib.util.find_spec("sqlalchemy"):
            self.skipTest("SQLAlchemy is not installed; matching fallback import is optional")
        from types import SimpleNamespace

        from app.matching import analyze_with_fallback, score_job

        class Unavailable:
            def analyze(self, _profile: object, _job: object) -> object:
                raise LocalModelError("model unavailable")

        profile = SimpleNamespace(skills=["Python"], experience=[], languages=[])
        job = SimpleNamespace(title="Python", description="", metadata_json={"required_skills": ["Python"]}, location="", region="other", modality="unknown")
        result = analyze_with_fallback(profile, job, result=score_job(profile, job), analyzer=Unavailable())
        self.assertEqual(result.model, "deterministic-fallback")
        self.assertIn("python", result.matches)

    def test_settings_read_local_model_limits(self) -> None:
        old = {key: os.environ.get(key) for key in ("OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS", "OLLAMA_NUM_CTX", "OLLAMA_NUM_THREAD")}
        try:
            os.environ.update({"OLLAMA_MODEL": "tiny", "OLLAMA_TIMEOUT_SECONDS": "2.5", "OLLAMA_NUM_CTX": "512", "OLLAMA_NUM_THREAD": "3"})
            settings = Settings.from_env()
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual((settings.ollama_model, settings.ollama_timeout_seconds, settings.ollama_num_ctx, settings.ollama_num_thread), ("tiny", 2.5, 512, 3))


if __name__ == "__main__":
    unittest.main()
