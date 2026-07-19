"""Domain services composed from repositories, independent of HTTP."""
from __future__ import annotations
from .models import Job, Profile
from .repositories import JobRepository, ProfileRepository

class ProfileService:
    def __init__(self, profiles: ProfileRepository) -> None: self.profiles = profiles
    def create(self, name: str, **profile_data: object) -> Profile: return self.profiles.add(Profile(name=name, **profile_data))

class JobIngestionService:
    def __init__(self, jobs: JobRepository) -> None: self.jobs = jobs
    def save(self, job: Job) -> Job: return self.jobs.upsert(job)
