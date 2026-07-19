# Backend

The backend will host the FastAPI service, domain services, persistence, and
scheduled ingestion workers. Production modules should remain independent of
the HTTP layer so they can also be run by the scheduler.

Ownership: backend coder tasks. Tests for backend behavior belong in `tests/`.
