# JobScrapper

JobScrapper is a local application for discovering job openings in Mexico, the
United States, and other regions, comparing them against a professional profile,
and prioritizing them using an explainable compatibility percentage.

Each opening can retain its title, company, region, work arrangement (remote,
hybrid, or on-site), description, description link, application link, salary,
matches, gaps, and recommendations. Results are stored locally in SQLite and can
be synchronized with Notion.

> **AI-assisted development**
>
> This project was created and documented with AI assistance (Codex) within a multi-agent harness. AI helped implement, test, and review changes; product decisions, acceptance of source terms, secret configuration, and commit approval were implemented by the developer.

## Features

- Ingestion from public APIs and JSON feeds, Greenhouse, Lever, and Ashby.
- Sources with explicit terms acceptance, URL validation, `robots.txt`, rate
  limits, retries, and per-source error isolation.
- Regional classification: Mexico City, Guadalajara, the rest of Mexico, the USA,
  and other regions.
- Deduplication by canonical URL and content fingerprint.
- Deterministic compatibility score from 0 to 100, with a breakdown by skills,
  experience, language, location, work arrangement, salary, and work authorization.
- Optional narrative analysis with Ollama; scoring does not depend on the local model.
- Editable profile and PDF/DOCX resume upload with local extraction.
- React dashboard for openings, profile, preferences, sources, and operations.
- Optional synchronization with Notion and regional views.
- Daily cron, concurrent-run locking, JSON logs, and backup/restore.
- Delivery harness using `coder → tester → reviewer → coordinator → commit` with
  Conventional Commits.

## Architecture

```text
React + TypeScript + Vite
            │ HTTP /api/v1
            ▼
FastAPI ── domain services ── MatchingService
   │              │                    │
   │              ├── source connectors └── optional Ollama
   │              ├── SQLite + SQLAlchemy
   │              └── optional Notion synchronization
   ▼
Docker Compose: backend · frontend · optional Ollama
```

### Technical components

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Frontend | React 19, TypeScript, Vite 7 | Accessible dashboard and forms |
| API | Python 3.11+, FastAPI, Uvicorn | Versioned HTTP contracts and OpenAPI |
| Domain | Python, SQLAlchemy 2, Alembic | Profile, sources, normalization, scoring, and runs |
| Persistence | SQLite | Local source of truth, evaluations, snapshots, and run logs |
| Local AI | Ollama | Optional narrative explanations; never required for scoring |
| Integration | Notion REST API | Optional synchronization of openings and regional views |
| Operations | Docker Compose, cron, Bash/Python scripts | Startup, refresh, backup, restore, and recovery |
| Quality | `unittest`, Playwright, multi-agent harness | Unit, integration, and E2E tests, plus delivery gates |

## Requirements

- Docker Desktop with Compose v2 (recommended for the complete environment).
- Python 3.11 or later for local development.
- Node.js 20+ and [pnpm](https://pnpm.io/) for the frontend.
- Ollama installed on the host or the `local-ollama` Compose profile (optional).
- A Notion integration and database ID (optional).

## Getting started with Docker

```sh
git clone <YOUR-REPOSITORY-URL>
cd JobScrapper
cp .env.example .env
```

Edit `.env` before starting. For Ollama installed on the host, Docker Desktop
uses `http://host.docker.internal:11434`:

```dotenv
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma3:1b
DATABASE_URL=sqlite:///./data/jobscrapper.db
```

Start the API and dashboard:

```sh
docker compose up --build -d
```

Main URLs:

- Dashboard: <http://127.0.0.1:5173>
- Health: <http://127.0.0.1:8000/health>
- Operations: <http://127.0.0.1:8000/api/v1/operations/health>
- OpenAPI: <http://127.0.0.1:8000/api/v1/docs>

To run Ollama inside Compose:

```sh
docker compose --profile local-ollama up --build -d
set -a
. ./.env
set +a
docker compose exec ollama ollama pull "$OLLAMA_MODEL"
```

In that case, use `OLLAMA_BASE_URL=http://ollama:11434` in `.env`. The
`jobscrapper_ollama` volume retains the models; `jobscrapper_data` retains
SQLite, resumes, and logs.

## Local development without Docker

### Backend

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e backend
cd backend
python -m app
```

### Frontend

In another terminal:

```sh
cd frontend
pnpm install
pnpm dev
```

The frontend expects the API at `http://127.0.0.1:8000`. For a production build:

```sh
pnpm build
pnpm preview --host 127.0.0.1 --port 4173
```

## Notion and Ollama configuration

### Notion

1. Create an integration in Notion.
2. Create a job openings database and share it with the integration.
3. Copy the database ID to `.env`.
4. Configure `NOTION_API_TOKEN` and `NOTION_DATABASE_ID`.

Configuration and property mapping are documented in
[`docs/NOTION.md`](docs/NOTION.md). Secrets are read at runtime and are not
persisted in sources, openings, or logs.

### Ollama

Check the local model:

```sh
ollama list
ollama pull gemma3:1b
curl http://127.0.0.1:11434/api/tags
```

The health endpoint reports the configured model. If Ollama is unavailable,
JobScrapper retains the deterministic percentage and marks the narrative analysis
as pending or fallback.

## Sources and refresh

Sources are created from the dashboard or through `POST /api/v1/sources`. Each
source must have an adapter and reviewed terms; the base URL is required in
network mode, and `allow_network=true` enables remote requests. In fixture mode,
the base URL may be omitted. The repository does not preconfigure remote sources:
add your permitted endpoints and accept their terms before enabling them.

After enabling a source:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/operations/refresh
```

The result includes openings found, sources with errors, evaluations created,
and scoring errors. A failure in one source does not discard the others.

## Cron and operations

Install the cron job after adjusting the absolute checkout path:

```sh
crontab scripts/jobscrapper.cron.example
```

The scheduler uses the same pipeline and lock as the manual refresh. For daily
operations, backup, and recovery:

```sh
scripts/ops.sh check
scripts/ops.sh restart
scripts/ops.sh backup backups
scripts/ops.sh restore backups/jobscrapper-data-YYYYMMDDTHHMMSSZ.tar.gz --yes
```

Read [`docs/OPERATIONS.md`](docs/OPERATIONS.md) before restoring or updating an
environment that contains data.

## Testing and quality

```sh
# Harness and task validation
python3 scripts/harness.py validate

# Backend (with the virtual environment activated)
python -m unittest discover -s tests/backend -p 'test_*.py' -v

# Frontend (Python tests + TypeScript/Vite build)
python3 -m unittest discover -s tests/frontend -p 'test_*.py' -v
(cd frontend && pnpm build)

# Optional E2E with Playwright
JOBSCRAPPER_E2E_COMMAND="pnpm preview --host 127.0.0.1 --port 4173" \
JOBSCRAPPER_E2E_URL="http://127.0.0.1:4173" \
python3 -m unittest tests.e2e.test_ingestion_dashboard -v
```

Environment-dependent failures (Chromium, Docker, Notion credentials, or
Ollama) must be recorded as evidence, not hidden.

## Security and compliance

- CAPTCHA, authentication, access controls, and `robots.txt` are not bypassed.
- Sources require terms review and configurable limits.
- URLs are validated as HTTP(S); `example.com` fallbacks are not used.
- Tokens are kept in environment variables and redacted from logs.
- Do not commit `.env`, SQLite databases, backups, resumes, or volumes to the repository.

## Repository structure

```text
backend/       FastAPI, domain, connectors, and persistence
frontend/      React, TypeScript, Vite, and dashboard
tests/         backend, frontend, harness, and E2E tests
scripts/       scheduler, operations, installation, and harness
docs/          SDD, Notion, operations, skills, and incremental log
.agents/       coder, tester, and reviewer contracts
.harness/      backlog, states, configuration, and allowlisted skills
```

## Contribution workflow

1. Review `AGENTS.md` and `.harness/backlog.json`.
2. Work on only one active task.
3. Complete the `coder → tester → reviewer → coordinator → commit` flow.
4. Use Conventional Commits (`feat`, `fix`, `test`, `docs`, `chore`, etc.).
5. Update `docs/DEVELOPMENT_LOG.md` and `CHANGELOG.md`.
6. Never include secrets or temporary artifacts in a commit.

## Publishing to GitHub

Before publishing, confirm that `.env`, SQLite databases, backups, resumes, logs,
and volumes are not staged:

```sh
git status --short
git diff --check
python3 scripts/harness.py validate
```

Create an empty repository on GitHub and publish the `main` branch:

```sh
git remote add origin https://github.com/<USER>/<REPOSITORY>.git
git push -u origin main
```

Do not upload Notion tokens, cookies, resumes, or `.env` files. Configure them as
secrets or environment variables in the deployment environment.

## Additional documentation

- [SDD and requirements](docs/SDD.md)
- [Operations, backup, and restore](docs/OPERATIONS.md)
- [Sources and compliance](docs/SOURCES.md)
- [Notion integration](docs/NOTION.md)
- [Skills policy](docs/SKILLS.md)
- [Development log](docs/DEVELOPMENT_LOG.md)
- [Backend](backend/README.md)

## License

This repository does not currently declare a public license. Add a `LICENSE`
file before distributing it publicly on GitHub.
