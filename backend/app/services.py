"""Domain services composed from repositories, independent of HTTP."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import BinaryIO
from .cv_profile import MAX_CV_BYTES, ParsedCV, parse_cv
from .models import Job, Profile, ProfilePreference
from .repositories import JobRepository, ProfileRepository

class ProfileService:
    def __init__(self, profiles: ProfileRepository) -> None: self.profiles = profiles
    def create(self, name: str, **profile_data: object) -> Profile: return self.profiles.add(Profile(name=name, **profile_data))

    def update_profile(self, profile_id: int, **profile_data: object) -> Profile:
        """Update editable profile dimensions and version the effective change.

        A PATCH may contain fields whose value is already current.  Those fields
        are not considered changed, so a no-op PATCH does not create a new
        profile version or unnecessarily enqueue reevaluation.  When at least
        one value changes, the version marker and metadata are updated together
        so matching workers can identify the exact profile revision to process.
        """
        profile = self.profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"profile {profile_id} does not exist")

        changed_dimensions: list[str] = []
        for key, value in profile_data.items():
            if not hasattr(profile, key):
                raise ValueError(f"unsupported profile field: {key}")
            if getattr(profile, key) != value:
                setattr(profile, key, value)
                changed_dimensions.append(key)

        if changed_dimensions:
            profile.version += 1
            profile.versioned_at = datetime.now(timezone.utc)
            profile.reevaluation_required = True
            profile.reevaluation_reason = "profile_changed"
            profile.reevaluation_metadata = {
                "profile_version": profile.version,
                "changed_dimensions": sorted(changed_dimensions),
                "requested_at": profile.versioned_at.isoformat(),
            }
        self.profiles.session.flush()
        return profile

    def update_preferences(self, profile_id: int, **preference_data: object) -> ProfilePreference:
        """Create a new preference revision and mark the profile for reevaluation.

        Changes to preferences, seniority, authorization, location, modality,
        compensation, or relocation alter matching semantics and therefore
        invalidate previous evaluations.  The metadata records the revision
        and a stable list of affected dimensions for the scheduler.
        """
        profile = self.profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"profile {profile_id} does not exist")
        self.profiles.supersede_preferences(profile_id)
        preferences = ProfilePreference(profile_id=profile_id, **preference_data)
        self.profiles.add_preferences(preferences)
        profile.version += 1
        profile.versioned_at = datetime.now(timezone.utc)
        profile.reevaluation_required = True
        profile.reevaluation_reason = "preferences_changed"
        profile.reevaluation_metadata = {
            "profile_version": profile.version,
            "changed_dimensions": sorted(preference_data.keys()),
            "requested_at": profile.versioned_at.isoformat(),
        }
        self.profiles.session.flush()
        return preferences

    def clear_reevaluation(self, profile_id: int, *, evaluated_version: int) -> Profile:
        """Clear the pending marker only when the evaluated version is current."""
        profile = self.profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"profile {profile_id} does not exist")
        if evaluated_version == profile.version:
            profile.reevaluation_required = False
            profile.reevaluation_reason = None
            profile.reevaluation_metadata = {**profile.reevaluation_metadata, "evaluated_version": evaluated_version}
            self.profiles.session.flush()
        return profile

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
