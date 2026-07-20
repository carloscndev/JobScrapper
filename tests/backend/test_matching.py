"""Tests for MATCH-001 deterministic compatibility scoring.

The pure scoring contract is exercised with SQLAlchemy domain objects when the
optional persistence dependency is installed.  Static checks still run in the
minimal environment so a missing dependency is explicit rather than hidden.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
MATCHING = BACKEND / "app" / "matching.py"


def _available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _matching_module():
    backend_path = str(BACKEND)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    return __import__("app.matching", fromlist=["*"])


class MatchingContractTests(unittest.TestCase):
    def test_scoring_contract_declares_dimensions_and_explainable_result(self) -> None:
        source = MATCHING.read_text()
        tree = ast.parse(source, filename=str(MATCHING))
        classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        self.assertIn("CompatibilityScorer", classes)
        self.assertIn("ScoreResult", classes)
        for dimension in ("skills", "experience", "seniority", "language", "location", "modality", "salary", "work_authorization"):
            self.assertIn(f'"{dimension}"', source)
        for field in ("breakdown", "matches", "gaps", "exclusions", "recommendations"):
            self.assertIn(field, source)
        self.assertIn("ruleset_version", source)


@unittest.skipUnless(_available("sqlalchemy"), "SQLAlchemy is not installed; runtime matching tests are optional")
class MatchingRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _matching_module()
        models = _matching_module().__dict__["Profile"].__module__
        cls.models = __import__(models, fromlist=["*"])

    def _objects(self):
        profile = self.models.Profile(
            name="Candidate",
            skills=["Python", "FastAPI"],
            # ``Profile`` stores structured CV experience in JSON; years are
            # read from this field by the scorer (not from a non-existent
            # profile metadata column).
            experience=[{"title": "Backend Engineer", "years": 4}],
            languages=["English"],
        )
        preference = self.models.ProfilePreference(
            profile=profile,
            preferred_languages=["English", "Spanish"],
            locations=["CDMX"],
            modalities=["remote"],
            seniority="senior",
            salary_min=50000,
            excluded_constraints=["relocation_required"],
            weights={"skills": 2, "experience": 1},
        )
        job = self.models.Job(
            title="Senior Python Engineer",
            company="Acme",
            description="Build APIs",
            description_url="https://jobs.example/1",
            application_url="https://apply.example/1",
            canonical_url="https://jobs.example/1",
            fingerprint="match-1",
            location="CDMX",
            modality="remote",
            salary_max=70000,
            metadata_json={
                "required_skills": ["Python", "SQL"],
                "desirable_skills": ["FastAPI"],
                "required_years": 3,
                "seniority": "senior",
            },
        )
        return profile, preference, job

    def test_score_is_reproducible_bounded_and_explainable(self) -> None:
        profile, preference, job = self._objects()
        result = self.module.score_job(profile, job, preference)
        self.assertGreaterEqual(result.score, 0)
        self.assertLessEqual(result.score, 100)
        self.assertEqual(result, self.module.score_job(profile, job, preference))
        self.assertEqual(result.matches, ["fastapi", "python"])
        self.assertIn("sql", result.gaps)
        self.assertEqual(result.breakdown["required"]["skills"], ["python", "sql"])
        self.assertEqual(result.breakdown["desirable"]["skills"], ["fastapi"])
        self.assertTrue(result.recommendations)

    def test_weights_are_configurable_and_exclusion_is_hard_constraint(self) -> None:
        profile, preference, job = self._objects()
        weighted = self.module.score_job(profile, job, preference, weights={"skills": 10, "experience": 0})
        baseline = self.module.score_job(profile, job, preference)
        self.assertNotEqual(weighted.score, baseline.score)
        self.assertEqual(weighted.breakdown["skills"]["weight"], 10.0)
        self.assertEqual(weighted.breakdown["experience"]["weight"], 0.0)
        job.metadata_json["constraints"] = ["relocation_required"]
        excluded = self.module.score_job(profile, job, preference)
        self.assertEqual(excluded.score, 0.0)
        self.assertEqual(excluded.exclusions, ["relocation_required"])

    def test_required_years_uses_structured_profile_experience(self) -> None:
        profile, preference, job = self._objects()
        full = self.module.score_job(profile, job, preference)
        profile.experience = [{"title": "Backend Engineer", "years": 1}]
        partial = self.module.score_job(profile, job, preference)
        self.assertEqual(full.breakdown["experience"]["match"], 1.0)
        self.assertAlmostEqual(partial.breakdown["experience"]["match"], 1 / 3)
        self.assertLess(partial.score, full.score)

    def test_matching_service_persists_breakdown_and_explanations(self) -> None:
        database = __import__("app.database", fromlist=["*"])
        repositories = __import__("app.repositories", fromlist=["*"])
        engine = database.create_db_engine(database_url="sqlite:///:memory:")
        self.models.Base.metadata.create_all(engine)
        factory = database.create_session_factory(engine)
        try:
            with factory() as session:
                profile, preference, job = self._objects()
                session.add_all([profile, job])
                session.flush()
                evaluation = self.module.MatchingService(
                    repositories.EvaluationRepository(session), repositories.ProfileRepository(session)
                ).evaluate(profile, job, preference, model_version="local-test")
                session.commit()
                self.assertEqual(evaluation.ruleset_version, "deterministic-v1")
                self.assertEqual(evaluation.model_version, "local-test")
                self.assertIn("required", evaluation.score_breakdown)
                self.assertIn("sql", evaluation.gaps)
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
