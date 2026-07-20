"""Explainable, deterministic job/profile compatibility scoring.

The scorer intentionally uses only normalized values and JSON preferences.  It
does not call a model, making results reproducible and safe to persist while an
optional narrative analysis is pending.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import re
import hashlib
import json

from .models import Evaluation, Job, Profile, ProfilePreference
from .repositories import EvaluationRepository, ProfileRepository
from .ollama import LocalAnalysis, LocalModelError, OllamaAnalyzer

DIMENSIONS = ("skills", "experience", "seniority", "language", "location", "modality", "salary", "work_authorization")
DEFAULT_WEIGHTS = {name: 1.0 for name in DIMENSIONS}


def _value(obj: object, name: str, default: Any = None) -> Any:
    return obj.get(name, default) if isinstance(obj, Mapping) else getattr(obj, name, default)


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(str(v) for v in value.values())
    return str(value or "")


def _tokens(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        values = [values]
    return {str(v).strip().casefold() for v in values if str(v).strip()}


def _requirements(job: object, key: str) -> set[str]:
    metadata = _value(job, "metadata_json", {}) or {}
    direct = _value(job, key, None)
    return _tokens(direct if direct is not None else metadata.get(key, []))


def _experience_years(profile: object) -> float:
    """Read normalized experience years without relying on a non-existent profile field."""
    entries = _value(profile, "experience", []) or []
    if isinstance(entries, Mapping):
        entries = [entries]
    total = 0.0
    found = False
    for entry in entries if isinstance(entries, (list, tuple)) else [entries]:
        if isinstance(entry, Mapping):
            for key in ("years", "years_experience", "duration_years"):
                if isinstance(entry.get(key), (int, float)):
                    total += float(entry[key]); found = True; break
            if found:
                continue
            text = _text(entry)
        else:
            text = _text(entry)
        match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:\+\s*)?(?:years?|a(?:ñ|n)os?)", text.casefold())
        if match:
            total += float(match.group(1)); found = True
    return total if found else 0.0


@dataclass(frozen=True)
class ScoreResult:
    score: float
    breakdown: dict[str, Any]
    matches: list[str]
    gaps: list[str]
    exclusions: list[str]
    recommendations: list[str]


class CompatibilityScorer:
    """Score a job from 0 to 100 using configurable weighted dimensions."""

    def __init__(self, weights: Mapping[str, Any] | None = None, *, ruleset_version: str = "deterministic-v1") -> None:
        supplied = {key: float(value) for key, value in (weights or {}).items() if key in DIMENSIONS and isinstance(value, (int, float)) and float(value) >= 0}
        self.weights = {**DEFAULT_WEIGHTS, **supplied}
        self.ruleset_version = ruleset_version

    def score(self, profile: object, job: object, preferences: object | None = None, *, weights_override: Mapping[str, Any] | None = None) -> ScoreResult:
        pref = preferences or _value(profile, "preferences", None)
        if isinstance(pref, (list, tuple)):
            pref = next((p for p in pref if _value(p, "is_current", True)), None)
        pref = pref or {}
        preference_weights = {k: float(v) for k, v in (_value(pref, "weights", {}) or {}).items() if k in DIMENSIONS and isinstance(v, (int, float)) and float(v) >= 0}
        # A call-site override is explicit and wins over persisted preferences;
        # this is useful for previews and versioned experiments without edits.
        explicit_weights = {k: float(v) for k, v in (weights_override or {}).items() if k in DIMENSIONS and isinstance(v, (int, float)) and float(v) >= 0}
        weights = {**self.weights, **preference_weights, **explicit_weights}
        candidate_skills = _tokens(_value(profile, "skills", []))
        required_skills = _requirements(job, "required_skills")
        desirable_skills = _requirements(job, "desirable_skills")
        all_job_text = _text(_value(job, "description", "")) + " " + _text(_value(job, "title", ""))
        if not required_skills and not desirable_skills:
            # No declared requirements are a neutral dimension, not a penalty.
            skill_score = 1.0
        else:
            required_match = len(candidate_skills & required_skills) / len(required_skills) if required_skills else 1.0
            desirable_match = len(candidate_skills & desirable_skills) / len(desirable_skills) if desirable_skills else 1.0
            skill_score = (required_match * 0.7) + (desirable_match * 0.3)
        required_experience = _value(job, "metadata_json", {}).get("required_years", _value(job, "required_years", None)) or 0
        years = _experience_years(profile)
        experience_score = 1.0 if not required_experience else min(1.0, years / float(required_experience))
        seniority = str(_value(pref, "seniority", "") or "").casefold()
        job_seniority = str(_value(job, "metadata_json", {}).get("seniority", "") or "").casefold()
        seniority_score = 1.0 if not seniority or not job_seniority else float(seniority == job_seniority)
        preferred_languages = _tokens(_value(pref, "preferred_languages", []))
        profile_languages = _tokens(_value(profile, "languages", []))
        language_score = 1.0 if not preferred_languages else len(profile_languages & preferred_languages) / len(preferred_languages)
        locations = _tokens(_value(pref, "locations", []))
        job_location = _tokens([_value(job, "location", ""), _value(job, "region", "")])
        location_score = 1.0 if not locations or (job_location & locations) else (1.0 if _value(pref, "willing_to_relocate", False) else 0.0)
        modalities = _tokens(_value(pref, "modalities", []))
        modality = str(_value(job, "modality", "unknown")).casefold()
        modality_score = 1.0 if not modalities or modality in modalities else 0.0
        salary_min, salary_max = _value(job, "salary_min", None), _value(job, "salary_max", None)
        wanted_min = _value(pref, "salary_min", None)
        salary_score = 1.0 if wanted_min is None or salary_max is None else float(salary_max >= wanted_min)
        auth = _tokens(_value(pref, "work_authorization", []))
        job_auth = _tokens(_value(job, "metadata_json", {}).get("work_authorization", []))
        auth_score = 1.0 if not auth or not job_auth or auth & job_auth else 0.0
        values = {"skills": skill_score, "experience": experience_score, "seniority": seniority_score, "language": language_score, "location": location_score, "modality": modality_score, "salary": salary_score, "work_authorization": auth_score}
        total_weight = sum(weights.values()) or 1.0
        score = round(100 * sum(values[key] * weights[key] for key in DIMENSIONS) / total_weight, 2)
        matches = sorted(candidate_skills & (required_skills | desirable_skills))
        gaps = sorted((required_skills | desirable_skills) - candidate_skills)
        exclusions = []
        constraints = _tokens(_value(pref, "excluded_constraints", []))
        job_constraints = _tokens(_value(job, "metadata_json", {}).get("constraints", []))
        exclusions.extend(sorted(constraints & job_constraints))
        # Exclusions are hard constraints: retain the full explanation but do
        # not present an excluded job as compatible.
        if exclusions:
            score = 0.0
        recommendations = [f"Close gap: {gap}" for gap in gaps[:5]]
        breakdown = {key: {"weight": weights[key], "match": round(values[key], 4), "points": round(100 * values[key] * weights[key] / total_weight, 2)} for key in DIMENSIONS}
        breakdown["required"] = {"skills": sorted(required_skills), "gaps": sorted(required_skills - candidate_skills)}
        breakdown["desirable"] = {"skills": sorted(desirable_skills), "gaps": sorted(desirable_skills - candidate_skills)}
        return ScoreResult(score, breakdown, matches, gaps, exclusions, recommendations)


class MatchingService:
    def __init__(self, evaluations: EvaluationRepository, profiles: ProfileRepository) -> None:
        self.evaluations, self.profiles = evaluations, profiles

    def evaluate(self, profile: Profile, job: Job, preferences: ProfilePreference | None = None, *, model_version: str | None = None, analyzer: OllamaAnalyzer | None = None) -> Evaluation:
        result = CompatibilityScorer().score(profile, job, preferences)
        analysis = None
        if analyzer is not None:
            analysis = analyze_with_fallback(profile, job, result=result, analyzer=analyzer)
            if analysis.model != "deterministic-fallback":
                model_version = analysis.model
        breakdown = {**result.breakdown, "input_fingerprint": evaluation_fingerprint(profile, job, ruleset_version="deterministic-v1", model_version=model_version)}
        evaluation = Evaluation(job_id=job.id, profile_id=profile.id, score=result.score, ruleset_version="deterministic-v1", model_version=model_version, score_breakdown=breakdown, matches=(analysis.matches if analysis else result.matches), gaps=(analysis.gaps if analysis else result.gaps), exclusions=result.exclusions, recommendations=(analysis.recommendations if analysis else result.recommendations), status="pending")
        return self.evaluations.add(evaluation)

    def evaluate_sequential(self, profile: Profile, jobs: list[Job], preferences: ProfilePreference | None = None, *, analyzer: OllamaAnalyzer | None = None, max_jobs: int = 100) -> list[Evaluation]:
        """Evaluate a bounded list serially; one model failure never aborts the batch."""
        if max_jobs < 1:
            return []
        return [self.evaluate(profile, job, preferences, analyzer=analyzer) for job in jobs[:max_jobs]]


def evaluation_fingerprint(profile: object, job: object, *, ruleset_version: str = "deterministic-v1", model_version: str | None = None) -> str:
    """Stable input identity used to decide whether a persisted evaluation is stale."""
    get = lambda obj, key, default=None: obj.get(key, default) if isinstance(obj, Mapping) else getattr(obj, key, default)
    payload = {"profile_version": get(profile, "version", 1), "profile": {"skills": get(profile, "skills", []), "experience": get(profile, "experience", []), "languages": get(profile, "languages", []), "preferences": get(profile, "preferences", [])}, "job": {"description": get(job, "description", ""), "title": get(job, "title", ""), "metadata": get(job, "metadata_json", {})}, "ruleset": ruleset_version, "model": model_version or "deterministic"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def needs_reevaluation(previous: object | None, profile: object, job: object, *, ruleset_version: str = "deterministic-v1", model_version: str | None = None) -> bool:
    if previous is None:
        return True
    breakdown = _value(previous, "score_breakdown", {}) or {}
    return breakdown.get("input_fingerprint") != evaluation_fingerprint(profile, job, ruleset_version=ruleset_version, model_version=model_version)


def analyze_with_fallback(profile: object, job: object, *, result: ScoreResult | None = None, analyzer: OllamaAnalyzer) -> LocalAnalysis:
    """Return local narrative or deterministic explanations while preserving score separately."""
    score = result or CompatibilityScorer().score(profile, job)
    try:
        return analyzer.analyze(profile, job)
    except LocalModelError:
        return LocalAnalysis("Local model unavailable; deterministic analysis retained.", list(score.matches), list(score.gaps), list(score.recommendations), "deterministic-fallback")


def score_job(profile: object, job: object, preferences: object | None = None, weights: Mapping[str, Any] | None = None) -> ScoreResult:
    """Convenience API; ``weights`` explicitly overrides persisted preferences."""
    return CompatibilityScorer().score(profile, job, preferences, weights_override=weights)


def analyze_job_locally(profile: object, job: object, *, analyzer: OllamaAnalyzer) -> LocalAnalysis:
    """Generate narrative matching details using only the configured local model."""
    return analyzer.analyze(profile, job)
