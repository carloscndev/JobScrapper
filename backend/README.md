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
Configure persistence with `DATABASE_URL` (default:
`sqlite:///./data/jobscrapper.db`) and optionally enable SQL logging with
`JOBSCRAPPER_DB_ECHO=true`. SQLAlchemy sessions are created through the
`app.database` lifecycle helpers so API and scheduler code share the same
engine configuration without depending on FastAPI.
The endpoint intentionally checks only process liveness; dependency checks will
be added with the persistence and integration tasks.

## Migrations

Alembic reads `DATABASE_URL` and falls back to `alembic.ini`. From the repository
root, after installing the backend package, run:

```sh
alembic upgrade head
```

The first domain tables will be introduced by the data-model task; this
foundation intentionally has no application entities yet.

## SQLite backup and restore

Stop API and scheduler writers before making a file-level copy. With the
default URL, the operational database is `data/jobscrapper.db`:

```sh
mkdir -p backups
sqlite3 data/jobscrapper.db ".backup 'backups/jobscrapper-$(date +%Y%m%d-%H%M%S).db'"
```

To restore, preserve the original, copy the selected backup, and run migrations:

```sh
cp data/jobscrapper.db data/jobscrapper-before-restore.db
cp backups/jobscrapper-YYYYMMDD-HHMMSS.db data/jobscrapper.db
alembic upgrade head
```

For non-file SQLite URLs or a future server database, use that database's native
backup tooling instead. Never commit database files or credentials.
