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

## CV ingestion

`app.cv_profile.parse_cv` accepts only PDF and DOCX streams, with a default
10 MiB limit. It validates extension, MIME type, PDF signature, and the DOCX
ZIP container (encrypted members, traversal paths, and excessive uncompressed
size are rejected) before parsing. Encrypted PDFs and files with empty or
unreadable extracted text are rejected. The result contains original text and
editable `name`, `skills`, `experience`, `education`, `languages`, and
`summary` fields. Extraction is heuristic and does not infer seniority,
preferences, authorization, compensation, or profile versions. Preferences
and reevaluation metadata are managed by `ProfileService.update_preferences`.
Install `pypdf` and `python-docx` from the backend project
dependencies before processing files.
# Backend

The backend domain layer is independent of FastAPI. Source integrations must
implement `app.sources.SourceAdapter` and return `NormalizedJob` values through
`SourceFetchResult`; HTTP endpoints and scheduling are integration concerns.

Source adapters are compliance-bound: they may use only permitted APIs, feeds,
or career pages; must honor the source's terms of use, `robots.txt`, timeout,
rate-limit, and retry settings; and must not bypass authentication, CAPTCHA,
access controls, or bot protections. Credentials are referenced through local
configuration and must never be included in source records, job metadata, or
logs. A source failure is represented in the fetch result so other sources can
continue processing.

## Profile API (v1)

OpenAPI is published at `/api/v1/openapi.json` (interactive docs at
`/api/v1/docs`). Profile operations use a stable validation error envelope:
`{"error":{"code","message","fields":[{"field","message","type"}]}}`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/profiles/upload` | Validate and parse a PDF/DOCX CV |
| `GET` | `/api/v1/profiles/{profile_id}` | Read profile and current preferences |
| `PATCH` | `/api/v1/profiles/{profile_id}` | Update editable structured fields |
| `PUT` | `/api/v1/profiles/{profile_id}/preferences` | Create a preference revision |

Upload failures return `422` with `cv_validation_error`; missing profiles
return `404` with `profile_not_found`. CV contents remain local to the service.
