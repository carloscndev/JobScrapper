"""Persistence repositories with no dependency on FastAPI."""
from __future__ import annotations
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Evaluation, Job, NotionSync, Profile, ProfilePreference, Source

class ProfileRepository:
    def __init__(self, session: Session) -> None: self.session = session
    def get(self, profile_id: int) -> Profile | None: return self.session.get(Profile, profile_id)
    def add(self, profile: Profile) -> Profile:
        self.session.add(profile); self.session.flush(); return profile
    def current_preferences(self, profile_id: int) -> ProfilePreference | None:
        return self.session.scalar(select(ProfilePreference).where(ProfilePreference.profile_id == profile_id, ProfilePreference.is_current.is_(True)))
    def add_preferences(self, preferences: ProfilePreference) -> ProfilePreference:
        """Persist a preference revision; callers manage superseding revisions."""
        self.session.add(preferences); self.session.flush(); return preferences
    def supersede_preferences(self, profile_id: int) -> None:
        current = self.current_preferences(profile_id)
        if current is not None:
            current.is_current = False
            self.session.flush()

class SourceRepository:
    def __init__(self, session: Session) -> None: self.session = session
    def enabled(self) -> Sequence[Source]: return self.session.scalars(select(Source).where(Source.enabled.is_(True)).order_by(Source.name)).all()
    def get(self, name: str) -> Source | None: return self.session.scalar(select(Source).where(Source.name == name))
    def get_or_create(self, name: str, **values: object) -> Source:
        source = self.get(name)
        if source is None:
            source = Source(name=name, **values); self.session.add(source); self.session.flush()
        return source

class JobRepository:
    def __init__(self, session: Session) -> None: self.session = session
    def by_canonical_url(self, canonical_url: str) -> Job | None: return self.session.scalar(select(Job).where(Job.canonical_url == canonical_url))
    def by_fingerprint(self, fingerprint: str) -> Job | None: return self.session.scalar(select(Job).where(Job.fingerprint == fingerprint))
    def upsert(self, job: Job) -> Job:
        existing = self.by_canonical_url(job.canonical_url) or self.by_fingerprint(job.fingerprint)
        if existing is None:
            self.session.add(job); self.session.flush(); return job
        for key in ("title", "company", "description", "description_url", "application_url", "fingerprint", "location", "region", "modality", "salary_min", "salary_max", "salary_currency", "published_at", "status", "metadata_json"):
            setattr(existing, key, getattr(job, key))
        self.session.flush(); return existing

class EvaluationRepository:
    def __init__(self, session: Session) -> None: self.session = session
    def latest(self, job_id: int, profile_id: int) -> Evaluation | None:
        return self.session.scalar(select(Evaluation).where(Evaluation.job_id == job_id, Evaluation.profile_id == profile_id).order_by(Evaluation.evaluated_at.desc()))
    def add(self, evaluation: Evaluation) -> Evaluation:
        self.session.add(evaluation); self.session.flush(); return evaluation

class NotionSyncRepository:
    def __init__(self, session: Session) -> None: self.session = session
    def for_job(self, job_id: int) -> NotionSync | None: return self.session.scalar(select(NotionSync).where(NotionSync.job_id == job_id))
    def upsert(self, sync: NotionSync) -> NotionSync:
        existing = self.for_job(sync.job_id)
        if existing is None:
            self.session.add(sync); self.session.flush(); return sync
        for key in ("external_id", "state", "attempts", "last_error", "reconciliation", "synced_at"): setattr(existing, key, getattr(sync, key))
        self.session.flush(); return existing
