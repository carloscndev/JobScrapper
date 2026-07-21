"""Persistence repositories with no dependency on FastAPI."""
from __future__ import annotations
from collections.abc import Sequence
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from .jobs import canonicalize_url, content_hash, fingerprint_job
from .models import Evaluation, Job, JobSnapshot, NotionSync, Profile, ProfilePreference, Source

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
    def get_by_id(self, source_id: int) -> Source | None: return self.session.get(Source, source_id)
    def delete(self, source_id: int) -> bool:
        source = self.get_by_id(source_id)
        if source is None:
            return False
        self.session.delete(source)
        self.session.flush()
        return True
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
        job.canonical_url = canonicalize_url(job.canonical_url)
        if not job.fingerprint:
            job.fingerprint = fingerprint_job(job)
        existing = self.by_canonical_url(job.canonical_url) or self.by_fingerprint(job.fingerprint)
        if existing is None:
            self.session.add(job); self.session.flush(); return job
        # Compare the complete effective record, not the partial incoming
        # payload. This prevents a sparse rediscovery from creating a false
        # snapshot merely because optional links were omitted.
        effective_description = job.description or existing.description
        effective_description_url = job.description_url or existing.description_url
        effective_application_url = job.application_url or existing.application_url
        old_hash = content_hash(description=existing.description, description_url=existing.description_url, application_url=existing.application_url)
        new_hash = content_hash(description=effective_description, description_url=effective_description_url, application_url=effective_application_url)
        if old_hash != new_hash:
            previous = self.session.scalar(select(JobSnapshot).where(JobSnapshot.job_id == existing.id, JobSnapshot.content_hash == old_hash))
            if previous is None:
                self.session.add(JobSnapshot(job_id=existing.id, description=existing.description, description_url=existing.description_url, application_url=existing.application_url, content_hash=old_hash))
        # Keep useful existing values when a source sends a partial record.
        for key in ("title", "company", "description", "description_url", "application_url", "canonical_url", "fingerprint", "location", "region", "modality", "salary_min", "salary_max", "salary_currency", "published_at", "status"):
            value = getattr(job, key)
            if value not in (None, "", "unknown", "other") or getattr(existing, key) in (None, "", "unknown", "other"):
                setattr(existing, key, value)
        existing.metadata_json = {**(existing.metadata_json or {}), **(job.metadata_json or {})}
        if existing.source_id is None and job.source_id is not None:
            existing.source_id = job.source_id
        existing.checked_at = job.checked_at or datetime.now(timezone.utc)
        self.session.flush(); return existing

    def mark_missing(self, source_id: int, seen_canonical_urls: set[str]) -> int:
        """Mark previously active source jobs absent from a successful run inactive."""
        jobs = self.session.scalars(select(Job).where(Job.source_id == source_id, Job.status == "active")).all()
        seen = {canonicalize_url(url) for url in seen_canonical_urls}
        changed = 0
        for job in jobs:
            if canonicalize_url(job.canonical_url) not in seen:
                job.status = "inactive"
                changed += 1
        self.session.flush()
        return changed

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
