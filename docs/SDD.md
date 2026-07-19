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

## Functional requirements

### Profile and matching

- The first-run flow accepts a PDF or DOCX CV, reports validation/extraction errors,
  and presents every extracted field for correction before it becomes active.
- Preferences include target roles, seniority, skills, languages, compensation and
  currency, accepted regions, work mode, work authorization, and relocation.
- Required requirements are scored separately from desirable requirements. Hard
  constraints are visible, can cap or exclude a result, and are never hidden inside
  the model-generated explanation.
- A score is reproducible from a versioned profile, ruleset, and job snapshot. A
  changed input creates reevaluation metadata rather than silently overwriting the
  prior evaluation.

### Job discovery and record lifecycle

- Each source adapter declares its name, terms/robots policy, request limits, and
  last successful run. Source errors are isolated and visible in run history.
- A normalized job stores the original description and application links, source
  provenance, publication/detection dates, salary and currency when available,
  region, modality, status, and last checked timestamp.
- Canonical URL plus a stable fingerprint provide idempotent upsert. Rediscovery
  updates provenance and fields; it does not create a second record. Description
  and link changes create snapshots, while withdrawn jobs become `inactive`.

### Presentation and synchronization

- The local dashboard supports pagination, search, sorting, filters for region,
  modality, score, company, source, date, and status, and a detail view with links,
  score breakdown, matches, gaps, constraints, and recommendations.
- Loading, error, empty, pending-analysis, changed, and inactive states are explicit
  in the UI. External links are validated and opened with safe browser attributes.
- Notion uses one master database with views for CDMX, Guadalajara, rest of Mexico,
  USA, and other. A stable local identifier is stored with every synced page so
  retries and reconciliation remain idempotent.

## Architecture

The application is a local single-user monorepo. A FastAPI adapter layer exposes HTTP endpoints, while domain services perform profile extraction, source ingestion, normalization, scoring, local-model analysis, and Notion synchronization. SQLAlchemy repositories isolate persistence behind the domain layer; FastAPI must not be imported by those repositories or services. SQLite is the operational source of truth, with Alembic migrations and documented backup/restore. A guarded pipeline command is shared by manual execution and the daily system cron, and a process lock prevents overlapping runs. The React/TypeScript/Vite dashboard consumes the API through a typed client. Ollama is an optional local worker; deterministic scoring and narrative-pending state remain available when it is unavailable.

### Runtime flow

1. The guarded pipeline acquires a process lock and creates a `PipelineExecution`.
2. Enabled adapters fetch permitted sources with per-source timeout, rate limit, and
   retry policy; each adapter reports success, partial success, or failure.
3. Results are sanitized, normalized, classified, deduplicated, and snapshotted.
4. Deterministic scoring runs for every job. Ollama analysis runs sequentially for
   eligible jobs and writes validated structured output; failures leave narrative
   status pending without losing the score.
5. SQLite is committed before an idempotent Notion sync. Sync outcomes and repair
   evidence are recorded locally.
6. The lock is released and metrics/logs are written. Cron and manual refresh use
   the same command, so they cannot execute concurrently.

### Non-functional requirements

- Local-first operation: the app binds to the local interface by default, has one
  user, and does not require a public account or hosted AI service.
- Resilience: one source, Ollama, or Notion failure must not discard successful
  source results; retries are bounded and safe to repeat.
- Explainability: score inputs, weights, ruleset/model versions, and timestamps are
  retained for audit and displayed in the detail view.
- Resource limits: model concurrency, request rate, retry count, CPU, memory, and
  log retention are configurable and documented for constrained hardware.
- Accessibility and responsive UX: keyboard navigation, semantic labels, visible
  focus, contrast, and desktop/tablet layouts are required for all dashboard views.
- Observability: structured logs and run metrics include correlation/run IDs and
  redact tokens, CV contents, and other sensitive values.

## Core data model

The persistence model includes: `Profile` and versioned `ProfilePreferences`; `Source` and `SourceRun`; `Job` with canonical URL, fingerprint, normalized fields, region, modality, provenance, status, and timestamps; `JobSnapshot` for description/link changes; `Evaluation` with rule/model versions, score breakdown, matches, gaps, exclusions, and recommendations; `PipelineExecution` with per-source outcomes and metrics; and `NotionSync` with stable external identifier, sync state, retry metadata, and reconciliation evidence. Indexes cover canonical URL, fingerprint, region, score, dates, and status. Secrets are configuration references only and never persisted in job content or logs.

The minimum Notion property mapping is: title/company, region, modality, salary and
currency, source, description URL, application URL, published/detected/checked dates,
compatibility score, score explanation, matches, gaps, recommendations, active status,
and the stable local job identifier. Long descriptions remain in SQLite and are linked
from Notion when property limits would truncate them.

## API contracts

The API is versioned under `/api/v1` and publishes OpenAPI schemas for success and error responses. Profile endpoints support CV upload, structured profile read/update, preferences, constraints, weights, and version metadata. Vacancy endpoints provide paginated/filterable lists, safe detail links, score breakdown, recommendation state, and snapshot history. Operations endpoints expose source configuration, execution history, metrics, health for API/SQLite/Ollama/Notion, and a manual refresh that returns a conflict when a run is already locked. Validation failures use a consistent field-error shape; all list endpoints return stable pagination metadata. The frontend generates or consumes TypeScript types from these schemas rather than duplicating wire shapes.

All endpoints are local-only in the initial release and use JSON except CV upload.
The API rejects malformed URLs, oversized/unsupported files, invalid pagination, and
unknown enum values with a stable error object containing `code`, `message`, and
optional field details. Health responses distinguish unavailable optional services
from an unhealthy operational database. Manual refresh returns HTTP 409 while the
pipeline lock is held.

## Security and compliance

- Secrets are read from environment/configuration references, excluded from Git, and
  redacted in exception messages and structured logs.
- Uploaded CVs are size/type validated, stored outside public static paths, and parsed
  with bounded resource usage. Untrusted HTML is sanitized before persistence or
  model input; URL schemes are restricted to HTTP(S).
- Source collection uses only permitted APIs, feeds, or public career pages and
  honors terms, robots directives, authentication boundaries, CAPTCHA, and rate
  limits. No evasion or automatic application is implemented.
- The local database and CV files are user data: backup, retention, deletion, and
  restore procedures are documented before release.

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

The executable backlog is intentionally explicit so implementation can proceed through
the harness one task at a time:

| Phase | Tasks |
| --- | --- |
| Bootstrap and governance | `BOOTSTRAP-001`, `BACKLOG-001`, `STRUCTURE-001`, `SKILLS-001`, `SKILLS-002`, `HARNESS-001`, `HARNESS-002`, `HARNESS-003`, `DOCS-001` |
| Service and data | `BACKEND-001`, `FRONTEND-001`, `DATA-001`, `DATA-002` |
| Profile and sources | `PROFILE-001`, `PROFILE-002`, `SOURCES-001`, `SOURCES-002`, `SOURCES-003` |
| Jobs and matching | `JOBS-001`, `JOBS-002`, `MATCH-001`, `MATCH-002`, `MATCH-003` |
| Notion and API | `NOTION-001`, `NOTION-002`, `NOTION-003`, `API-001`, `API-002`, `API-003` |
| Dashboard | `FRONTEND-002`, `FRONTEND-003`, `FRONTEND-004`, `FRONTEND-005` |
| Operations | `OPS-001`, `OPS-002`, `OPS-003`, `OPS-004`, `OPS-005` |
| Verification | `TEST-001`, `TEST-002`, `TEST-003`, `TEST-004`, `TEST-005`, `TEST-006`, `TEST-007` |
| Release | `RELEASE-001` |

`.harness/backlog.json` is authoritative for dependencies, acceptance criteria,
allowed paths, state, and Conventional Commit subject; this table is the readable
phase index and must be updated if task IDs change.
