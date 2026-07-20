"""Application factory and versioned profile HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .database import create_db_engine, create_session_factory
from .models import Base, Evaluation, Job, Profile
from sqlalchemy import asc, desc, func, or_, select
from .repositories import ProfileRepository
from .schemas import (JobDetailResponse, JobEvaluationResponse, JobListItem, PaginatedJobsResponse,
                      PreferencePayload, ProfileResponse, ProfileUpdatePayload, UploadResponse)
from .services import ProfileService

from .config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured FastAPI application.

    Keeping construction explicit makes the service easy to run locally and
    keeps future domain services independent from the HTTP server.
    """

    runtime = settings or Settings.from_env()
    app = FastAPI(
        title=runtime.app_name,
        version="0.1.0",
        description="Local profile and job-discovery API. CV files are parsed locally.",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
    )
    if runtime.database_url.startswith("sqlite:///./"):
        Path(runtime.database_url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_db_engine(runtime)
    session_factory = create_session_factory(engine)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(part) for part in error.get("loc", [])), "message": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Request validation failed", "fields": fields}})

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail: Any = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail, headers=exc.headers)
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": "http_error", "message": str(detail), "fields": []}}, headers=exc.headers)

    def profile_or_404(db: Any, profile_id: int) -> Profile:
        profile = ProfileRepository(db).get(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail={"error": {"code": "profile_not_found", "message": f"Profile {profile_id} does not exist", "fields": []}})
        return profile

    def profile_payload(profile: Profile) -> dict[str, Any]:
        current = next((item for item in profile.preferences if item.is_current), None)
        data = {key: getattr(profile, key) for key in ("id", "name", "cv_text", "cv_filename", "version", "seniority", "reevaluation_required", "reevaluation_reason", "reevaluation_metadata", "versioned_at", "skills", "experience", "education", "languages")}
        data["preferences"] = current
        return data

    def evaluation_payload(item: Evaluation) -> dict[str, Any]:
        return {key: getattr(item, key) for key in ("id", "profile_id", "score", "ruleset_version", "model_version", "score_breakdown", "matches", "gaps", "exclusions", "recommendations", "status", "evaluated_at")}

    def job_item_payload(job: Job, evaluation: Evaluation | float | None = None) -> dict[str, Any]:
        # List queries project a scalar score while detail queries pass an
        # Evaluation entity. Accept both representations to keep one payload
        # serializer and avoid dereferencing ``score`` on a float.
        score = getattr(evaluation, "score", evaluation)
        return {"id": job.id, "title": job.title, "company": job.company, "location": job.location,
                "region": job.region, "modality": job.modality, "status": job.status,
                "description_url": job.description_url, "application_url": job.application_url,
                "published_at": job.published_at, "detected_at": job.detected_at,
                "score": score}

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Return a lightweight liveness response without checking dependencies."""

        return {"status": "ok", "service": runtime.app_name, "environment": runtime.environment}

    @app.on_event("startup")
    def create_tables() -> None:
        # Migrations remain the production mechanism; this keeps a fresh local
        # checkout usable for the profile API without a separate bootstrap step.
        Base.metadata.create_all(engine)

    @app.post("/api/v1/profiles/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED, tags=["profiles"])
    def upload_profile(file: UploadFile = File(...)) -> dict[str, Any]:
        with session_factory() as db:
            try:
                profile, parsed = ProfileService(ProfileRepository(db)).ingest_cv(file.file, file.filename or "", file.content_type)
                db.commit()
                result = profile_payload(profile)
                result["parsed_text_length"] = len(parsed.text)
                return result
            except ValueError as exc:
                db.rollback()
                raise HTTPException(status_code=422, detail={"error": {"code": "cv_validation_error", "message": str(exc), "fields": [{"field": "file", "message": str(exc), "type": "value_error"}]}}) from exc

    @app.get("/api/v1/profiles/{profile_id}", response_model=ProfileResponse, tags=["profiles"])
    def read_profile(profile_id: int) -> dict[str, Any]:
        with session_factory() as db:
            return profile_payload(profile_or_404(db, profile_id))

    @app.patch("/api/v1/profiles/{profile_id}", response_model=ProfileResponse, tags=["profiles"])
    def update_profile(profile_id: int, payload: ProfileUpdatePayload) -> dict[str, Any]:
        """Apply structured edits and expose the resulting reevaluation marker.

        ``ProfileService.update_profile`` owns versioning and sets
        ``reevaluation_required`` plus ``reevaluation_metadata`` whenever an
        effective profile dimension changes.
        """
        with session_factory() as db:
            profile_or_404(db, profile_id)
            profile = ProfileService(ProfileRepository(db)).update_profile(
                profile_id, **payload.model_dump(exclude_unset=True)
            )
            db.commit()
            response = profile_payload(profile)
            # Keep the versioning signals explicit in the PATCH response so
            # clients can schedule matching reevaluation without another read.
            response["reevaluation_required"] = profile.reevaluation_required
            response["reevaluation_metadata"] = profile.reevaluation_metadata
            return response

    @app.put("/api/v1/profiles/{profile_id}/preferences", response_model=ProfileResponse, tags=["profiles"])
    def update_preferences(profile_id: int, payload: PreferencePayload) -> dict[str, Any]:
        with session_factory() as db:
            profile_or_404(db, profile_id)
            ProfileService(ProfileRepository(db)).update_preferences(profile_id, **payload.model_dump())
            db.commit()
            return profile_payload(ProfileRepository(db).get(profile_id))

    @app.get("/api/v1/jobs", response_model=PaginatedJobsResponse, tags=["jobs"])
    def list_jobs(
        page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
        region: str | None = None, modality: str | None = None, status_filter: str | None = Query(None, alias="status"),
        company: str | None = None, source_id: int | None = Query(None, ge=1), q: str | None = None,
        min_score: float | None = Query(None, ge=0, le=100), profile_id: int | None = Query(None, ge=1),
        order: str = Query("detected_at", pattern="^(detected_at|published_at|score|title|company)$"),
        direction: str = Query("desc", pattern="^(asc|desc)$"),
    ) -> dict[str, Any]:
        """List active and historical jobs with deterministic pagination."""
        with session_factory() as db:
            filters = []
            if region: filters.append(Job.region == region.lower())
            if modality: filters.append(Job.modality == modality.lower())
            if status_filter: filters.append(Job.status == status_filter.lower())
            if source_id is not None: filters.append(Job.source_id == source_id)
            if company: filters.append(Job.company.ilike(f"%{company}%"))
            if q: filters.append(or_(Job.title.ilike(f"%{q}%"), Job.description.ilike(f"%{q}%"), Job.company.ilike(f"%{q}%")))
            score_expr = func.max(Evaluation.score)
            join_condition = Evaluation.job_id == Job.id
            # Restrict the outer join itself when a profile is requested. A
            # WHERE predicate would discard jobs that have evaluations for a
            # different profile, instead of returning them with score=null.
            if profile_id is not None:
                join_condition = join_condition & (Evaluation.profile_id == profile_id)
            query = select(Job, score_expr.label("score")).outerjoin(Evaluation, join_condition)
            if min_score is not None: query = query.where(Evaluation.score >= min_score)
            if filters: query = query.where(*filters)
            query = query.group_by(Job.id)
            sort_col = {"detected_at": Job.detected_at, "published_at": Job.published_at, "score": score_expr, "title": Job.title, "company": Job.company}[order]
            query = query.order_by((asc(sort_col) if direction == "asc" else desc(sort_col)), asc(Job.id))
            # Count the same grouped/filtered relation used for the page so
            # score and profile filters do not produce misleading totals.
            count_relation = query.order_by(None).with_only_columns(Job.id).subquery()
            total = db.scalar(select(func.count()).select_from(count_relation)) or 0
            rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
            return {"items": [job_item_payload(job, score if score is not None else None) for job, score in rows], "total": total,
                    "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}

    @app.get("/api/v1/jobs/{job_id}", response_model=JobDetailResponse, tags=["jobs"])
    def read_job(job_id: int, profile_id: int | None = Query(None, ge=1)) -> dict[str, Any]:
        with session_factory() as db:
            job = db.get(Job, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail={"error": {"code": "job_not_found", "message": f"Job {job_id} does not exist", "fields": []}})
            evaluations = list(db.scalars(select(Evaluation).where(Evaluation.job_id == job_id, *( [Evaluation.profile_id == profile_id] if profile_id else [])).order_by(Evaluation.evaluated_at.desc(), Evaluation.id.desc())).all())
            latest = evaluations[0] if evaluations else None
            result = job_item_payload(job, latest)
            result.update({"description": job.description, "canonical_url": job.canonical_url, "salary_min": job.salary_min,
                           "salary_max": job.salary_max, "salary_currency": job.salary_currency, "metadata_json": job.metadata_json or {},
                           "score_breakdown": latest.score_breakdown if latest else {}, "recommendations": latest.recommendations if latest else [],
                           "evaluation": evaluation_payload(latest) if latest else None,
                           "evaluation_history": [evaluation_payload(item) for item in evaluations]})
            return result

    return app
