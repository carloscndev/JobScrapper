"""Application factory and versioned profile HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .database import create_db_engine, create_session_factory
from .models import Base, Profile
from .repositories import ProfileRepository
from .schemas import PreferencePayload, ProfileResponse, ProfileUpdatePayload, UploadResponse
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

    return app
