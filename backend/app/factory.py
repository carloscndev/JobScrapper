"""Application factory and HTTP routes."""

from fastapi import FastAPI

from .config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured FastAPI application.

    Keeping construction explicit makes the service easy to run locally and
    keeps future domain services independent from the HTTP server.
    """

    runtime = settings or Settings.from_env()
    app = FastAPI(title=runtime.app_name, version="0.1.0")

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Return a lightweight liveness response without checking dependencies."""

        return {"status": "ok", "service": runtime.app_name, "environment": runtime.environment}

    return app
