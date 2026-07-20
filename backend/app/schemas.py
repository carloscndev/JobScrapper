"""HTTP schemas for the profile management API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PreferencePayload(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    modalities: list[str] = Field(default_factory=list)
    seniority: str | None = None
    preferred_languages: list[str] = Field(default_factory=list)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    salary_period: str | None = None
    employment_types: list[str] = Field(default_factory=list)
    work_authorization: list[str] = Field(default_factory=list)
    willing_to_relocate: bool = False
    excluded_constraints: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)

class ProfileUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    seniority: str | None = Field(default=None, max_length=40)
    skills: list[Any] | None = None
    experience: list[Any] | None = None
    education: list[Any] | None = None
    languages: list[Any] | None = None


class PreferenceResponse(PreferencePayload):
    model_config = ConfigDict(from_attributes=True)
    id: int
    profile_id: int
    is_current: bool
    created_at: datetime


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    cv_text: str | None
    cv_filename: str | None
    version: int
    seniority: str | None
    reevaluation_required: bool
    reevaluation_reason: str | None
    reevaluation_metadata: dict[str, Any]
    versioned_at: datetime
    skills: list[Any]
    experience: list[Any]
    education: list[Any]
    languages: list[Any]
    preferences: PreferenceResponse | None = None


class UploadResponse(ProfileResponse):
    parsed_text_length: int
