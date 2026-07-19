# JobScrapper software design description

## User story

As a professional seeking work in Mexico and the United States, I want a local application to discover jobs daily, compare them with my CV and preferences using local models and explainable rules, and synchronize results to Notion, so I can prioritize strong opportunities without sending my profile to external AI services.

## Product behavior

- Import PDF/DOCX CV data into an editable profile containing skills, experience, seniority, languages, education, desired roles, compensation, work modes, locations, work authorization, and relocation preferences.
- Discover jobs daily from allowed APIs, feeds, and career pages without bypassing authentication, CAPTCHA, robots directives, or access controls.
- Normalize company, role, description, requirements, location, work mode, salary, source, dates, description URL, and application URL.
- Classify locations into CDMX, Guadalajara, rest of Mexico, USA, or other; classify mode as remote, hybrid, on-site, or unknown.
- Deduplicate jobs across sources, retain provenance and description history, and mark unavailable jobs inactive rather than deleting them.
- Calculate a 0-100 compatibility score from auditable weighted rules. Local models produce summaries, matches, gaps, and recommendations; deterministic scoring remains available if the model fails.
- Present searchable, sortable, filterable job lists and detailed score explanations in a local single-user dashboard.
- Upsert a master Notion database idempotently and expose regional filtered views.
- Record each scheduled run, isolate source failures, prevent overlapping executions, retry safely, and redact secrets from logs.
- Never auto-apply in the first release.

## Architecture

The application is a local single-user monorepo. A FastAPI adapter layer exposes HTTP endpoints, while domain services perform profile extraction, source ingestion, normalization, scoring, local-model analysis, and Notion synchronization. SQLAlchemy repositories isolate persistence behind the domain layer; FastAPI must not be imported by those repositories or services. SQLite is the operational source of truth, with Alembic migrations and documented backup/restore. A guarded pipeline command is shared by manual execution and the daily system cron, and a process lock prevents overlapping runs. The React/TypeScript/Vite dashboard consumes the API through a typed client. Ollama is an optional local worker; deterministic scoring and narrative-pending state remain available when it is unavailable.

## Core data model

The persistence model includes: `Profile` and versioned `ProfilePreferences`; `Source` and `SourceRun`; `Job` with canonical URL, fingerprint, normalized fields, region, modality, provenance, status, and timestamps; `JobSnapshot` for description/link changes; `Evaluation` with rule/model versions, score breakdown, matches, gaps, exclusions, and recommendations; `PipelineExecution` with per-source outcomes and metrics; and `NotionSync` with stable external identifier, sync state, retry metadata, and reconciliation evidence. Indexes cover canonical URL, fingerprint, region, score, dates, and status. Secrets are configuration references only and never persisted in job content or logs.

## API contracts

The API is versioned under `/api/v1` and publishes OpenAPI schemas for success and error responses. Profile endpoints support CV upload, structured profile read/update, preferences, constraints, weights, and version metadata. Vacancy endpoints provide paginated/filterable lists, safe detail links, score breakdown, recommendation state, and snapshot history. Operations endpoints expose source configuration, execution history, metrics, health for API/SQLite/Ollama/Notion, and a manual refresh that returns a conflict when a run is already locked. Validation failures use a consistent field-error shape; all list endpoints return stable pagination metadata. The frontend generates or consumes TypeScript types from these schemas rather than duplicating wire shapes.

## Acceptance criteria

1. A valid CV produces an editable structured profile.
2. Failure of one source does not stop other sources.
3. Every record contains available normalized fields, provenance, and last-check time.
4. URLs, uploaded files, and scraped HTML are validated or sanitized.
5. Rediscovery updates a stable record instead of duplicating it.
6. Every job has region, mode, and deterministic score, permitting unknown classifications.
7. Score detail separates matches, gaps, and hard constraints.
8. A local-model outage leaves deterministic results intact and narrative analysis pending.
9. Notion regional views reflect the master database without duplicate records.
10. Removed jobs remain as inactive history.
11. Daily scheduling operates for seven days without overlapping runs.
12. Sources and profile preferences can be changed without code edits.

## Delivery backlog

The canonical executable backlog is `.harness/backlog.json` and contains 46 dependency-tracked tasks. Its delivery phases are: repository structure; persistence and migrations; profile/CV parsing and preferences; compliant source adapters; normalization and deduplication; deterministic scoring and local-model analysis; Notion synchronization; FastAPI endpoints; React dashboard; Docker and daily scheduling; observability and recovery; security, contract, component, and end-to-end testing; and version 0.1.0 release readiness. Each task defines acceptance criteria, allowed paths, and its Conventional Commit subject.

Initial technical defaults are Python/FastAPI/SQLAlchemy/SQLite, React/TypeScript/Vite, Ollama with a small quantized model and deterministic fallback, Docker Compose, and a system cron invoking one guarded pipeline command.
