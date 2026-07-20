"""Application factory and versioned profile HTTP routes."""

from __future__ import annotations

from pathlib import Path
import os
from datetime import datetime, timezone
from urllib.request import Request as UrlRequest, urlopen
from urllib.parse import urlparse
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .database import create_db_engine, create_session_factory
from .models import Base, Evaluation, Job, Profile, PipelineExecution, Source, SourceRun
from sqlalchemy import asc, desc, func, or_, select
from .repositories import ProfileRepository, JobRepository
from .schemas import (JobDetailResponse, JobEvaluationResponse, JobListItem, PaginatedJobsResponse,
                      PreferencePayload, ProfileResponse, ProfileUpdatePayload, UploadResponse)
from .services import ProfileService
from .connectors import DEFAULT_ADAPTERS
from .jobs import canonicalize_url, fingerprint_job
from .sources import SourceConfig, SourceKind
from .notion import NotionConfig
from .process_lock import ProcessLock

from .config import Settings
from .observability import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured FastAPI application.

    Keeping construction explicit makes the service easy to run locally and
    keeps future domain services independent from the HTTP server.
    """

    runtime = settings or Settings.from_env()
    configure_logging(level=runtime.log_level, path=runtime.log_file,
                      max_bytes=runtime.log_max_bytes, backup_count=runtime.log_backup_count)
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
    # File-backed lock coordinates API requests with scheduler/manual workers
    # running in other processes, not only requests in this server process.
    refresh_lock = ProcessLock()
    app.state.refresh_lock = refresh_lock

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

    def _safe_source_config(source: Source) -> dict[str, Any]:
        config = source.config or {}
        redacted = {key: value for key, value in config.items()
                    if not any(marker in key.casefold() for marker in ("token", "secret", "password", "cookie"))}
        return {"id": source.id, "name": source.name, "kind": source.kind, "base_url": source.base_url,
                "terms_url": source.terms_url, "enabled": source.enabled, "config": redacted,
                "robots_checked_at": source.robots_checked_at}

    def _execution_payload(item: PipelineExecution) -> dict[str, Any]:
        return {"id": item.id, "run_id": item.run_id, "status": item.status, "started_at": item.started_at,
                "finished_at": item.finished_at, "metrics": item.metrics or {}, "error": item.error,
                "source_runs": [{"id": run.id, "source_id": run.source_id, "status": run.status,
                                  "jobs_found": run.jobs_found, "error": run.error,
                                  "started_at": run.started_at, "finished_at": run.finished_at}
                                 for run in item.source_runs]}

    def _dependency_health() -> dict[str, Any]:
        # The process-level API check is deliberately independent from
        # downstream dependencies so operators can distinguish liveness from
        # readiness failures in a single response.
        checks: dict[str, Any] = {
            "api": {"status": "ok", "service": runtime.app_name, "version": "0.1.0"}
        }
        try:
            with session_factory() as db:
                db.execute(select(func.count()).select_from(Source)).scalar_one()
            checks["database"] = {"status": "ok"}
        except Exception as exc:
            checks["database"] = {"status": "error", "message": str(exc)[:200]}
        try:
            parsed = urlparse(runtime.ollama_base_url)
            if parsed.hostname not in {"localhost", "127.0.0.1", "::1", "host.docker.internal", "ollama"}:
                raise ValueError("Ollama endpoint is not an approved local host")
            request = UrlRequest(runtime.ollama_base_url.rstrip("/") + "/api/tags", headers={"User-Agent": "JobScrapper-health/1.0"})
            with urlopen(request, timeout=min(runtime.ollama_timeout_seconds, 2.0)):
                pass
            checks["ollama"] = {"status": "ok", "model": runtime.ollama_model}
        except Exception as exc:
            checks["ollama"] = {"status": "unavailable", "model": runtime.ollama_model, "message": str(exc)[:200]}
        notion = NotionConfig.from_settings(runtime)
        checks["notion"] = {"status": "configured" if notion.database_id and os.getenv(notion.token_env) else "unconfigured",
                             "config": notion.redacted()}
        overall = "ok" if checks["database"]["status"] == "ok" else "degraded"
        return {"status": overall, "checks": checks, "checked_at": datetime.now(timezone.utc)}

    @app.get("/api/v1/operations/health", tags=["operations"])
    @app.get("/api/v1/health", tags=["operations"])
    def operations_health() -> dict[str, Any]:
        """Report API liveness and dependency readiness without exposing secrets."""
        return _dependency_health()

    @app.get("/api/v1/operations/sources", tags=["operations"])
    @app.get("/api/v1/sources", tags=["operations"])
    def list_sources(enabled: bool | None = None) -> dict[str, Any]:
        with session_factory() as db:
            query = select(Source).order_by(Source.name)
            if enabled is not None:
                query = query.where(Source.enabled.is_(enabled))
            items = db.scalars(query).all()
            return {"items": [_safe_source_config(item) for item in items], "total": len(items)}

    @app.get("/api/v1/operations/executions", tags=["operations"])
    @app.get("/api/v1/executions", tags=["operations"])
    def list_executions(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status_filter: str | None = Query(None, alias="status")) -> dict[str, Any]:
        with session_factory() as db:
            query = select(PipelineExecution).order_by(PipelineExecution.started_at.desc(), PipelineExecution.id.desc())
            if status_filter:
                query = query.where(PipelineExecution.status == status_filter)
            total = db.scalar(select(func.count()).select_from(PipelineExecution).where(*( [PipelineExecution.status == status_filter] if status_filter else []))) or 0
            rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
            return {"items": [_execution_payload(item) for item in rows], "total": total, "page": page,
                    "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}

    @app.get("/api/v1/operations/executions/{run_id}", tags=["operations"])
    @app.get("/api/v1/executions/{run_id}", tags=["operations"])
    def read_execution(run_id: str) -> dict[str, Any]:
        with session_factory() as db:
            item = db.scalar(select(PipelineExecution).where(PipelineExecution.run_id == run_id))
            if item is None:
                raise HTTPException(status_code=404, detail={"error": {"code": "execution_not_found", "message": f"Execution {run_id} does not exist", "fields": []}})
            return _execution_payload(item)

    @app.get("/api/v1/operations/metrics", tags=["operations"])
    @app.get("/api/v1/metrics", tags=["operations"])
    def metrics() -> dict[str, Any]:
        with session_factory() as db:
            return {"jobs": {"total": db.scalar(select(func.count()).select_from(Job)) or 0,
                              "active": db.scalar(select(func.count()).select_from(Job).where(Job.status == "active")) or 0},
                    "sources": {"total": db.scalar(select(func.count()).select_from(Source)) or 0,
                                 "enabled": db.scalar(select(func.count()).select_from(Source).where(Source.enabled.is_(True))) or 0},
                    "executions": {"total": db.scalar(select(func.count()).select_from(PipelineExecution)) or 0,
                                    "running": db.scalar(select(func.count()).select_from(PipelineExecution).where(PipelineExecution.status == "running")) or 0},
                    "generated_at": datetime.now(timezone.utc)}

    def _run_refresh() -> PipelineExecution:
        with session_factory() as db:
            started_clock = datetime.now(timezone.utc)
            execution = PipelineExecution(status="running", started_at=datetime.now(timezone.utc), metrics={})
            db.add(execution); db.flush()
            found = failed = 0
            enabled_sources = db.scalars(select(Source).where(Source.enabled.is_(True)).order_by(Source.name)).all()
            issues_total = 0
            for source in enabled_sources:
                started = datetime.now(timezone.utc)
                source_config = SourceConfig(name=source.name, kind=SourceKind(source.kind), base_url=source.base_url,
                    terms_url=source.terms_url, terms_accepted=bool((source.config or {}).get("terms_accepted")), settings=source.config or {})
                adapter = next((item for item in DEFAULT_ADAPTERS if item.name == (source.config or {}).get("adapter", source.name)), None)
                if adapter is None:
                    adapter = next((item for item in DEFAULT_ADAPTERS if item.name == source.kind), None)
                result = adapter.fetch(source_config) if adapter else None
                run = SourceRun(execution_id=execution.id, source_id=source.id, status=result.status if result else "failed",
                                jobs_found=len(result.jobs) if result else 0, error=result.error if result else "No adapter configured",
                                started_at=started, finished_at=datetime.now(timezone.utc))
                db.add(run)
                if result:
                    found += len(result.jobs)
                    failed += 1 if result.error else 0
                    issues_total += 1 if result.error else 0
                    for normalized in result.jobs:
                        JobRepository(db).upsert(Job(source_id=source.id, title=normalized.title, company=normalized.company, description=normalized.description,
                                    description_url=normalized.description_url, application_url=normalized.application_url,
                                    canonical_url=canonicalize_url(normalized.effective_canonical_url), fingerprint=fingerprint_job(normalized),
                                    location=normalized.location, region=normalized.region, modality=str(normalized.modality),
                                    salary_min=normalized.salary_min, salary_max=normalized.salary_max, salary_currency=normalized.salary_currency,
                                    published_at=normalized.published_at, metadata_json={**dict(normalized.metadata), "source": source.name}))
            execution.status = "failed" if failed and not found else ("partial" if failed else "success")
            execution.finished_at = datetime.now(timezone.utc)
            execution.metrics = {"jobs_found": found, "sources_failed": failed,
                                 "sources_total": len(enabled_sources), "issues_total": issues_total,
                                 "duration_seconds": round((datetime.now(timezone.utc) - started_clock).total_seconds(), 3),
                                 "max_concurrency": runtime.max_concurrency}
            db.commit(); db.refresh(execution)
            return execution

    @app.post("/api/v1/refresh", status_code=status.HTTP_202_ACCEPTED, tags=["operations"])
    @app.post("/api/v1/operations/refresh", status_code=status.HTTP_202_ACCEPTED, tags=["operations"])
    def manual_refresh() -> dict[str, Any]:
        if not refresh_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail={"error": {"code": "refresh_in_progress", "message": "A refresh is already running", "fields": []}})
        try:
            return _execution_payload(_run_refresh())
        finally:
            refresh_lock.release()

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
