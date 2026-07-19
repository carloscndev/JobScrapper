"""Domain services composed from repositories, independent of HTTP."""
from __future__ import annotations
from typing import BinaryIO
from .cv_profile import MAX_CV_BYTES, ParsedCV, parse_cv
from .models import Job, Profile
from .repositories import JobRepository, ProfileRepository

class ProfileService:
    def __init__(self, profiles: ProfileRepository) -> None: self.profiles = profiles
    def create(self, name: str, **profile_data: object) -> Profile: return self.profiles.add(Profile(name=name, **profile_data))

    def ingest_cv(self, file: BinaryIO, filename: str, content_type: str | None = None, *, max_bytes: int = MAX_CV_BYTES) -> tuple[Profile, ParsedCV]:
        """Create an editable profile from a validated CV stream.

        Preferences, constraints, and versioning are intentionally deferred to
        PROFILE-002.
        """
        parsed = parse_cv(file, filename, content_type, max_bytes=max_bytes)
        data = parsed.profile
        profile = Profile(
            name=data.get("name") or parsed.filename.rsplit(".", 1)[0],
            cv_text=parsed.text,
            cv_filename=parsed.filename,
            skills=data["skills"],
            experience=data["experience"],
            education=data["education"],
            languages=data["languages"],
        )
        return self.profiles.add(profile), parsed

class JobIngestionService:
    def __init__(self, jobs: JobRepository) -> None: self.jobs = jobs
    def save(self, job: Job) -> Job: return self.jobs.upsert(job)
