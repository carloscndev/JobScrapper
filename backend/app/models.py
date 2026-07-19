"""SQLAlchemy persistence models for JobScrapper's domain entities.

The models deliberately contain persistence concerns only.  Domain workflows
use the repositories and services in :mod:`app.repositories` and
:mod:`app.services`, keeping them independent from FastAPI.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base metadata for all application tables."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cv_text: Mapped[str | None] = mapped_column(Text)
    cv_filename: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    skills: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    experience: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    education: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    languages: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)

    preferences: Mapped[list[ProfilePreference]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    evaluations: Mapped[list[Evaluation]] = relationship(back_populates="profile")


class ProfilePreference(TimestampMixin, Base):
    __tablename__ = "profile_preferences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    target_roles: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    locations: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    modalities: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    work_authorization: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    willing_to_relocate: Mapped[bool] = mapped_column(default=False, nullable=False)
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_current: Mapped[bool] = mapped_column(default=True, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="preferences")
    __table_args__ = (Index("ix_profile_preferences_current", "profile_id", "is_current"),)


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False, default="career_page")
    base_url: Mapped[str | None] = mapped_column(String(2048))
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    terms_url: Mapped[str | None] = mapped_column(String(2048))
    robots_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    jobs: Mapped[list[Job]] = relationship(back_populates="source")
    runs: Mapped[list[SourceRun]] = relationship(back_populates="source", cascade="all, delete-orphan")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    application_url: Mapped[str | None] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    region: Mapped[str] = mapped_column(String(40), nullable=False, default="other")
    modality: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    published_at: Mapped[date | None] = mapped_column(Date)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    source: Mapped[Source | None] = relationship(back_populates="jobs")
    snapshots: Mapped[list[JobSnapshot]] = relationship(back_populates="job", cascade="all, delete-orphan")
    evaluations: Mapped[list[Evaluation]] = relationship(back_populates="job", cascade="all, delete-orphan")
    notion_syncs: Mapped[list[NotionSync]] = relationship(back_populates="job", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("canonical_url", name="uq_jobs_canonical_url"),
        UniqueConstraint("fingerprint", name="uq_jobs_fingerprint"),
        Index("ix_jobs_region", "region"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_detected_at", "detected_at"),
        Index("ix_jobs_published_at", "published_at"),
    )


class JobSnapshot(Base):
    __tablename__ = "job_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    application_url: Mapped[str | None] = mapped_column(String(2048))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    job: Mapped[Job] = relationship(back_populates="snapshots")
    __table_args__ = (UniqueConstraint("job_id", "content_hash", name="uq_job_snapshot_hash"), Index("ix_job_snapshots_captured_at", "captured_at"))


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100))
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    matches: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    gaps: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    exclusions: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    recommendations: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    job: Mapped[Job] = relationship(back_populates="evaluations")
    profile: Mapped[Profile] = relationship(back_populates="evaluations")
    __table_args__ = (Index("ix_evaluations_score", "score"), Index("ix_evaluations_status", "status"), Index("ix_evaluations_evaluated_at", "evaluated_at"))


class PipelineExecution(TimestampMixin, Base):
    __tablename__ = "pipeline_executions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    source_runs: Mapped[list[SourceRun]] = relationship(back_populates="execution", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_pipeline_executions_status", "status"), Index("ix_pipeline_executions_started_at", "started_at"))


class SourceRun(Base):
    __tablename__ = "source_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("pipeline_executions.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution: Mapped[PipelineExecution] = relationship(back_populates="source_runs")
    source: Mapped[Source] = relationship(back_populates="runs")
    __table_args__ = (Index("ix_source_runs_status", "status"), Index("ix_source_runs_started_at", "started_at"))


class NotionSync(Base):
    __tablename__ = "notion_syncs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    reconciliation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    job: Mapped[Job] = relationship(back_populates="notion_syncs")
    __table_args__ = (UniqueConstraint("job_id", name="uq_notion_sync_job"), UniqueConstraint("external_id", name="uq_notion_sync_external_id"), Index("ix_notion_syncs_state", "state"))
