# Backend

The backend will host the FastAPI service, domain services, persistence, and
scheduled ingestion workers. Production modules should remain independent of
the HTTP layer so they can also be run by the scheduler.

Ownership: backend coder tasks. Tests for backend behavior belong in `tests/`.

## Local bootstrap

From the repository root, create a virtual environment and install the service
dependencies:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e backend
```

Start the development server with:

```sh
cd backend
python -m app
```

The default liveness endpoint is `http://127.0.0.1:8000/health`. Configure the
host, port, environment label, and title with `JOBSCRAPPER_HOST`,
`JOBSCRAPPER_PORT`, `JOBSCRAPPER_ENV`, and `JOBSCRAPPER_APP_NAME` respectively.
The endpoint intentionally checks only process liveness; dependency checks will
be added with the persistence and integration tasks.
