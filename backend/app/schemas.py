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


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    company: str
    location: str | None = None
    region: str
    modality: str
    status: str
    description_url: str
    application_url: str | None = None
    published_at: Any = None
    detected_at: datetime | None = None
    score: float | None = None


class JobEvaluationResponse(BaseModel):
    id: int
    profile_id: int
    score: float
    ruleset_version: str
    model_version: str | None = None
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    matches: list[Any] = Field(default_factory=list)
    gaps: list[Any] = Field(default_factory=list)
    exclusions: list[Any] = Field(default_factory=list)
    recommendations: list[Any] = Field(default_factory=list)
    status: str
    evaluated_at: datetime | None = None


class JobDetailResponse(JobListItem):
    description: str
    canonical_url: str
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[Any] = Field(default_factory=list)
    evaluation: JobEvaluationResponse | None = None
    evaluation_history: list[JobEvaluationResponse] = Field(default_factory=list)


class PaginatedJobsResponse(BaseModel):
    items: list[JobListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
