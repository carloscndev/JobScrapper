"""Offline resilience tests for MATCH-003 local analysis orchestration."""

from __future__ import annotations

import sys
import unittest
import importlib.util
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None
from app.ollama import LocalModelError, OllamaAnalyzer  # noqa: E402
if SQLALCHEMY_AVAILABLE:
    from app.matching import (  # noqa: E402
        CompatibilityScorer,
        MatchingService,
        analyze_with_fallback,
        evaluation_fingerprint,
        needs_reevaluation,
    )
else:  # pragma: no cover - exercised by the optional-dependency skip
    CompatibilityScorer = MatchingService = object  # type: ignore[misc,assignment]



class _AlwaysFail:
    def analyze(self, *_args: object, **_kwargs: object) -> object:
        raise LocalModelError("offline")


class _FailingOpener:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *_args: object, **_kwargs: object) -> object:
        self.calls += 1
        raise OSError("timeout")


class OllamaResilienceTests(unittest.TestCase):
    def test_retries_are_bounded_and_exponential_backoff_is_capped_by_attempts(self) -> None:
        opener = _FailingOpener()
        analyzer = OllamaAnalyzer(opener=opener, max_retries=2, retry_backoff_seconds=0.25)
        with patch("app.ollama.time.sleep") as sleep:
            with self.assertRaises(LocalModelError):
                analyzer.analyze({}, {})
        self.assertEqual(opener.calls, 3)  # initial request plus two retries
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.25, 0.5])

@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy is not installed; runtime matching tests are optional")
class MatchingResilienceTests(unittest.TestCase):
    def test_ollama_failure_returns_deterministic_fallback(self) -> None:
        profile = {"skills": ["Python"]}
        job = {"title": "Backend", "description": "", "metadata_json": {"required_skills": ["Python", "SQL"]}}
        score = CompatibilityScorer().score(profile, job)
        fallback = analyze_with_fallback(profile, job, result=score, analyzer=_AlwaysFail())
        self.assertEqual(fallback.model, "deterministic-fallback")
        self.assertEqual(fallback.matches, score.matches)
        self.assertEqual(fallback.gaps, score.gaps)
        self.assertEqual(fallback.recommendations, score.recommendations)

    def test_sequential_processing_is_bounded_and_preserves_order(self) -> None:
        service = MatchingService.__new__(MatchingService)
        seen: list[int] = []

        def evaluate(profile: object, job: object, *_args: object, **_kwargs: object) -> int:
            seen.append(job["id"])
            return job["id"]

        service.evaluate = evaluate  # type: ignore[method-assign]
        jobs = [{"id": index} for index in range(5)]
        self.assertEqual(service.evaluate_sequential({}, jobs, max_jobs=3), [0, 1, 2])
        self.assertEqual(seen, [0, 1, 2])
        self.assertEqual(service.evaluate_sequential({}, jobs, max_jobs=0), [])

    def test_fingerprint_changes_trigger_reevaluation(self) -> None:
        profile = {"version": 1, "skills": ["Python"], "experience": [], "languages": [], "preferences": []}
        job = {"title": "Backend", "description": "Build APIs", "metadata_json": {"required_skills": ["Python"]}}
        fingerprint = evaluation_fingerprint(profile, job)
        previous = {"score_breakdown": {"input_fingerprint": fingerprint}}
        self.assertFalse(needs_reevaluation(previous, profile, job))
        changed_profile = {**profile, "skills": ["Python", "SQL"]}
        changed_job = {**job, "description": "Build distributed APIs"}
        self.assertTrue(needs_reevaluation(previous, changed_profile, job))
        self.assertTrue(needs_reevaluation(previous, profile, changed_job))
        self.assertTrue(needs_reevaluation(previous, profile, job, ruleset_version="deterministic-v2"))
        self.assertTrue(needs_reevaluation(previous, profile, job, model_version="llama3.2:3b"))


if __name__ == "__main__":
    unittest.main()
