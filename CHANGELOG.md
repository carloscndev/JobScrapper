# Changelog

All notable product changes will be documented here following Keep a Changelog and Semantic Versioning.

## [Unreleased]

### Added

- `BOOTSTRAP-001`: repository governance for the multi-agent delivery workflow.
- `SKILLS-001`: managed skill manifest with exact upstream revisions, pinned checksums, role authorization, and explicit risk metadata.
- `HARNESS-001` / `HARNESS-002`: dependency-free lifecycle CLI with executable commit gates.
- `DOCS-001`: initial product SDD and delivery backlog.

### BOOTSTRAP-001 — Attempt 1

- Skills: governed project skills with exact revisions; Notion skill marked high risk
- Files: initial repository, harness, skill governance, tests, and SDD
- Commands: harness validation, skill verification, 25 unit tests, syntax/JSON checks, and diff checks
- Tester: PASS — all automated gates passed
- Reviewer: APPROVED — all four review cycles resolved
- Risks: gate evidence must be staged by the coordinator; scope enforcement includes deletions and both sides of renames
- Commit subject: chore(repo): initialize project repository
- Commit hash: 3eb86cab7dd0f988e91981870dd0f37830a462c7

### BACKLOG-001 — Attempt 1

- Expanded the backlog to 46 total executable dependency-tracked tasks spanning repository structure, data, profile, sources, scoring, Notion, API, frontend, operations, security, tests, and release readiness.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `.harness/backlog.json`, `docs/SDD.md`, `docs/DEVELOPMENT_LOG.md`, `CHANGELOG.md`
- Commands: JSON validation, harness validation, topological dependency check, 25 unit tests, py_compile, shell syntax, and diff checks
- Tester: PASS — 46 unique tasks, complete required fields, no unknown dependencies or cycles
- Reviewer: APPROVED — backlog coverage and SDD structure accepted after correcting task count
- Risks: task sequencing must be followed through the existing harness
- Commit subject: docs(backlog): expand application delivery tasks
- Commit hash: 221154cfd1ec043c7a6eb198b7ce57dbec53ee7f

### SKILLS-001 — Attempt 2

- Added fail-closed validation for skill source, immutable revision/checksum, purpose, risk, risk detail, roles, allowlist, and allowed roles.
- Skills: coordinator `skill-installer`; coder none; tester none; reviewer none
- Files: manifest, installer, checker, skills documentation, and harness tests
- Commands: skill verification, 28 unit tests, Python/shell syntax, JSON, and diff checks
- Tester: PASS — mandatory-field, mismatch, and idempotence coverage passes
- Reviewer: APPROVED — no out-of-scope changes
- Risks: `notion-api` remains marked high risk
- Commit subject: chore(skills): add managed skill installation
- Commit hash: 1ad41f9f252283a94844d91c708b51a2097eaffc

### SKILLS-002 — Attempt 1

- Verified all four installed skills against the manifest's pinned SHA-256 values; no reinstall was needed.
- Skills: coordinator `skill-installer`; coder none; tester none; reviewer none
- Files: `docs/SKILLS.md`
- Commands: skill checker, independent checksum comparison, 28 tests, JSON/Python/harness/diff checks
- Tester: PASS — all verification gates passed
- Reviewer: APPROVED — installation and documentation verified
- Risks: `notion-api` remains marked high risk
- Commit subject: chore(skills): install project agent capabilities
- Commit hash: eb086cbded5916763340a2871367a565b7b9d67c

### STRUCTURE-001 — Attempt 1

- Added documented backend, frontend, scripts, and tests directories without premature framework code.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: repository READMEs and root layout documentation
- Commands: 28 tests, skills, Python/Shell, JSON, harness, artifact, and diff checks
- Tester: PASS — structure and artifact checks pass
- Reviewer: APPROVED — scope and ownership verified
- Risks: implementation tasks remain responsible for their own dependencies and allowed paths
- Commit subject: chore(repo): scaffold application directories
- Commit hash: ebbb15de8e07eea5582a2ace24f1fc6ed8e5ff6c

### HARNESS-001 — Attempt 1

- Tightened coordinator, coder, tester, and reviewer contracts for state transitions, failure loops, skill authorization, evidence, and commit ownership.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `AGENTS.md` and `.agents/*.md`
- Commands: 28 tests, JSON/harness/Python/Shell checks, semantic protocol checks, and diff checks
- Tester: PASS — protocol and ownership rules verified
- Reviewer: APPROVED — contracts complete and within scope
- Risks: coordinator preserves single active task and no agent bypasses commit gates
- Commit subject: chore(harness): define multi-agent workflow
- Commit hash: 7668cfaa3dc382feeb3182a55fe7d6f382ccef29

### HARNESS-002 — Attempt 1

- Strengthened task lifecycle validation for states, dependencies, rejection reasons, active-task consistency, and real commit identity.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `scripts/harness.py`, `README.md`, and harness tests
- Commands: 33 tests, JSON/harness/Python/Shell checks, and diff checks
- Tester: PASS — lifecycle edge cases and exact commit subject/hash covered
- Reviewer: APPROVED — implementation is within scope
- Risks: completion requires the current HEAD and configured Conventional Commit subject
- Commit subject: feat(harness): add task lifecycle management
- Commit hash: 22af84d7bb3f19736bc44875b49eb89a62afe647

### HARNESS-003 — Attempt 1

- Added tests for read-only active status and invalid transitions that attempt to skip the tester gate.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `tests/harness/test_harness.py`
- Commands: 35 unit tests and Python/Shell/JSON/harness/diff checks
- Tester: PASS — all lifecycle coverage passes
- Reviewer: APPROVED — tests are scoped and meaningful
- Risks: pytest is unavailable; unittest remains the configured runner
- Commit subject: test(harness): cover task lifecycle gates
- Commit hash: 942028fe7a5bc319a119fca60fa62ed66a782c21

### DOCS-001 — Attempt 1

- Expanded SDD and README with functional/NFR requirements, runtime flow, architecture, data model, API contracts, Notion mapping, security, UX, operations, and the 46-task phase index.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `docs/SDD.md`, `README.md`
- Commands: 35 tests, JSON/harness/Python/Shell/diff checks
- Tester: PASS — documentation and task index verified
- Reviewer: APPROVED — dependency order corrected and content in scope
- Risks: backlog JSON is authoritative for exact sequencing
- Commit subject: docs(sdd): add product requirements and backlog
- Commit hash: f023dfd3602a9124c23f6c174171920727fe6d9e

### BACKEND-001 — Attempt 3

- Added FastAPI factory, environment-backed settings, `/health`, package metadata, and stdlib backend tests.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/**`, `tests/backend/test_health.py`, `README.md`
- Commands: backend tests `5 pass, 1 skip`, 35 harness tests, Python/Shell/JSON/harness/diff checks
- Tester: PASS — runtime health test is explicitly skipped until FastAPI is installed
- Reviewer: APPROVED — production and test scope are correct
- Risks: dependency installation is required for runtime route coverage
- Commit subject: feat(api): bootstrap FastAPI service
- Commit hash: 920d796d30baf3516423840fb89c5efea63301dc

### FRONTEND-001 — Attempt 2

- Added React/TypeScript/Vite scaffold with typed health client, responsive accessible view, and loading/error/status states.
- Skills: coordinator none; coder `vercel-react-best-practices`; tester `webapp-testing`; reviewer `web-design-guidelines`
- Files: `frontend/**`, `tests/frontend/test_frontend_bootstrap.py`, `README.md`
- Commands: 45 tests total; static frontend checks; JSON/Python/Shell/diff checks; npm install/build attempted
- Tester: PASS — endpoint/client regressions pass; npm build awaits network dependencies
- Reviewer: APPROVED — UI and scope verified
- Risks: npm registry DNS prevented installing TypeScript/Vite for build execution
- Commit subject: feat(web): bootstrap React dashboard
- Commit hash: be8cda8c41671d7fe8587984abc2092383b1f954

### DATA-001 — Attempt 1

- Added configurable SQLAlchemy/SQLite engine and sessions, Alembic configuration/checkpoint, and backup/restore documentation.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: backend database configuration, Alembic files, backend database tests, and docs
- Commands: 50 tests total with 3 dependency skips; JSON/Python/Shell/harness/diff checks
- Tester: PASS — database config/static tests pass with explicit SQLAlchemy skips
- Reviewer: APPROVED — scope and lifecycle behavior verified
- Risks: SQLAlchemy/Alembic runtime tests require dependency installation
- Commit subject: feat(data): add database foundation
- Commit hash: 8779e82ac5e8ba4e44ef493d4721da66aa6f2555

### DATA-002 — Attempt 2

- Added profile, preference, source, job, snapshot, evaluation, execution, and Notion sync models with repositories/services independent of FastAPI.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: domain models, repositories, services, Alembic metadata/migration, and model tests
- Commands: 56 tests with 4 dependency skips; JSON/Python/Shell/skills/harness/diff checks
- Tester: PASS — migration safety and domain contracts covered
- Reviewer: APPROVED — explicit migration operations and scope verified
- Risks: live SQLAlchemy/Alembic execution requires dependency installation
- Commit subject: feat(data): add core domain models
- Commit hash: a5661fdb63aa0f286fa7b01626e744269fc607df

### PROFILE-001 — Attempt 1

- Added secure PDF/DOCX validation and extraction into an editable profile service.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: CV validator/extractor, profile service, backend dependencies/docs, and CV tests
- Commands: 66 tests with 5 skips; JSON/Python/Shell/skills/harness/diff checks
- Tester: PASS — malicious/invalid file fixtures and structured profile behavior covered
- Reviewer: APPROVED — security and scope verified
- Risks: optional document parser dependencies require installation for full runtime coverage
- Commit subject: feat(profile): add CV ingestion and profile extraction
- Commit hash: f2af923f2c7bbd79470f965186d5b0017fe48089

### PROFILE-002 — Attempt 1

- Added configurable professional preferences, constraints, versioned superseding, and reevaluation metadata.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: profile models/repositories/services, migration 0003, backend docs, and preference tests
- Commands: 72 tests with 7 skips; JSON/Python/Shell/skills/harness/diff checks
- Tester: PASS — preference and reevaluation contracts pass
- Reviewer: APPROVED — implementation is within scope
- Risks: live preference persistence tests require SQLAlchemy installation
- Commit subject: feat(profile): add job preferences and versioning
- Commit hash: 645cade3bc6d4c162b2b2ebde4fc93a132359a52

### SOURCES-001 — Attempt 1

- Added source adapter/configuration contracts, normalized job/fetch results, safe URL and rate-limit validation, and enablement service.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: source contracts/service, backend docs, and source tests
- Commands: 38 backend tests with 12 skips; 35 harness tests; JSON/Python/Shell/skills/harness/diff checks
- Tester: PASS — source contract and safety checks pass
- Reviewer: APPROVED — scope and compliance constraints verified
- Risks: real connectors are deferred to SOURCES-002; SQLAlchemy remains optional in this environment
- Commit subject: feat(sources): define job source adapters
- Commit hash: 2268fa9cdfe6745830ea4ba8c04804a8c86cd583

### SOURCES-002 — Attempt 4

- Added fixture-first JSON/feed, Greenhouse, and Lever connectors with normalized job fields and URL handling.
- Added opt-in network fetching with robots.txt and identifiable user-agent checks, source failure isolation, and mandatory `terms_accepted` compliance validation persisted by `SourceService`.
- Tests: 7 connector tests pass with 7 explicit SQLAlchemy skips; reviewer APPROVED after href parsing and documentation rework.
- Conventional Commit: `feat(sources): add initial job connectors`
- Commit hash: f4c55a95dae9f1d3532755b346c920324ef842aa

### SOURCES-003 — Attempt 2

- Added bounded per-source rate limiting, exponential retries, safe HTML sanitization, URL validation, and per-item failure isolation while preserving robots and identifiable user-agent controls.
- Added regression coverage for modality inference from remote locations.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/connectors.py`, `tests/backend/test_connectors.py`
- Commands: 11 connector tests pass under forced runtime; related suite 38 tests with 12 skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — ingestion controls and modality regression covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: live SQLAlchemy coverage requires dependency installation; network remains opt-in and robots/terms constrained
- Commit subject: feat(sources): harden ingestion controls
- Commit hash: bc37edb54fabe89fd07378e2da6bee01ac99305e

### JOBS-001 — Attempt 1

- Added normalized requirements, salary period/currency/source metadata, URL validation, geographic region buckets, and modality classification.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/sources.py`, `backend/app/connectors.py`, `tests/backend/test_sources.py`
- Commands: 52 backend tests with 26 explicit optional-dependency skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — normalized fields and region/modality contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: SQLAlchemy/FastAPI runtime coverage requires optional dependency installation
- Commit subject: feat(jobs): normalize job records and regions
- Commit hash: 121a0b4e6d1edf06c114aa6986ab9a31a48b0e3e

### JOBS-002 — Attempt 2

- Added canonical URL normalization, stable fingerprints, deduplication, provenance merge, content snapshots, and inactive history tracking.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/jobs.py`, `backend/app/repositories.py`, `tests/backend/test_jobs.py`, `docs/JOBS.md`
- Commands: 58 backend tests with 32 explicit optional-dependency skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — identity, snapshots, history, and partial-upsert regression covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: SQLAlchemy runtime coverage requires optional dependency installation
- Commit subject: feat(jobs): deduplicate and version job changes
- Commit hash: 035454175e0e9c470f0a06d6eaecd3e50a7df41d

### MATCH-001 — Attempt 3

- Added deterministic compatibility scoring from 0 to 100 with configurable weights, required/desirable requirements, hard exclusions, explainable breakdowns, matches, gaps, recommendations, and persistence.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/matching.py`, `tests/backend/test_matching.py`
- Commands: 63 backend tests with 36 explicit optional-dependency skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — matching behavior and weight precedence covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: SQLAlchemy runtime persistence checks require optional dependency installation
- Commit subject: feat(match): add explainable compatibility scoring
- Commit hash: 5d537456331cf4c52961825688b9309affd65cd5

### MATCH-002 — Attempt 1

- Added loopback-only Ollama analysis with configurable model/resources, allowlisted prompts, structured JSON validation, and summary/gap/recommendation mapping.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/ollama.py`, `backend/app/config.py`, `backend/app/matching.py`, `tests/backend/test_ollama.py`, `.env.example`
- Commands: 67 backend tests with 36 explicit optional-dependency skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — local boundary and structured output contract covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: Ollama runtime availability is operator-managed; endpoint remains loopback-only
- Commit subject: feat(match): add local Ollama analysis
- Commit hash: aa3d379722c75f1ac8c03637bdce8c4fa616b482

### MATCH-003 — Attempt 1

- Added bounded retry/backoff and sequential evaluation for local analysis, deterministic fallback preserving scores, and stable reevaluation fingerprints.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/ollama.py`, `backend/app/matching.py`, `tests/backend/test_match_resilience.py`
- Commands: 71 backend tests with 39 explicit optional-dependency skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — resilience and reevaluation contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: SQLAlchemy runtime checks require optional dependency installation; Ollama remains local and operator-managed
- Commit subject: feat(match): add resilient local analysis fallback
- Commit hash: cc7bba9fdb5b149f80522ca4d81038a965df20cc

### NOTION-001 — Attempt 2

- Added secure environment-only Notion credentials, normalized vacancy schema, and regional view definitions for five locations.
- Skills: coordinator `notion-api`; coder `notion-api`; tester none; reviewer `notion-api`
- Files: `backend/app/notion.py`, `backend/app/config.py`, `tests/backend/test_notion.py`, `.env.example`, `docs/NOTION.md`
- Commands: 76 backend tests with 39 explicit optional-dependency skips; 5 Notion tests pass; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — offline security and schema tests
- Reviewer: APPROVED — implementation re-review passed after traceability correction
- Risks: no network or destructive Notion operations performed; API runtime remains operator-managed
- Commit subject: feat(notion): define vacancy database integration
- Commit hash: 9e141e6d29e2c4a16b69fce34333d8dfb593d1fd

### NOTION-002 — Attempt 2

- Added idempotent Notion upserts by stable fingerprint, evaluated property synchronization, pagination, rate limiting, Retry-After/backoff, and persisted sync outcomes with accurate attempts and errors.
- Skills: coordinator `notion-api`; coder `notion-api`; tester none; reviewer `notion-api`
- Files: `backend/app/notion_sync.py`, `tests/backend/test_notion_sync.py`, `docs/NOTION.md`
- Commands: 85 backend tests with 39 explicit optional-dependency skips; 9 Notion sync tests pass; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — sync contracts and persistence metadata covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: no live Notion calls in tests; API credentials and runtime remain operator-managed
- Commit subject: feat(notion): sync evaluated jobs idempotently
- Commit hash: 212d81bd2a6b97e1336abe79c0a523dd07845eea

### NOTION-003 — Attempt 2

- Added auditable SQLite/Notion reconciliation reports, retryable repairs, orphan detection, and safe non-destructive handling of fingerprint-less pages.
- Skills: coordinator `notion-api`; coder `notion-api`; tester none; reviewer `notion-api`
- Files: `backend/app/notion_sync.py`, `tests/backend/test_notion_sync.py`
- Commands: 89 backend tests with 39 explicit optional-dependency skips; 13 Notion tests pass; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — reconciliation and repair contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: no live Notion calls; orphan repair is intentionally non-destructive
- Commit subject: feat(notion): add synchronization reconciliation
- Commit hash: 5a283bd820c22e2731c5ac7af6f0af3e89cf8b14

### API-001 — Attempt 3

- Added versioned profile upload/read/update and preferences endpoints with consistent validation errors and explicit reevaluation metadata on effective PATCH changes.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/app/services.py`, `backend/app/schemas.py`, `backend/README.md`, `tests/backend/test_api_profile.py`, `backend/pyproject.toml`
- Commands: 8 API tests pass with 5 explicit FastAPI/SQLAlchemy skips; 95 backend tests with 43 skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — API contracts and reevaluation behavior covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: full HTTP runtime coverage requires FastAPI/SQLAlchemy dependencies
- Commit subject: feat(api): expose profile management endpoints
- Commit hash: 60fb12751d61fbb54fe6bca9bc2a4ba192738060

### API-002 — Attempt 2

- Added paginated vacancy list filters/order and detail responses with score breakdown, recommendations, links, and evaluation history.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/app/schemas.py`, `tests/backend/test_api_jobs.py`
- Commands: 6 API tests pass with 4 explicit HTTP dependency skips; 103 backend tests with 48 skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — search/detail and profile-specific score contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: full HTTP runtime coverage requires FastAPI/SQLAlchemy dependencies
- Commit subject: feat(api): expose vacancy search endpoints
- Commit hash: 353af10cfe2b4dbf8e85aa9bb6219afe70985b75

### API-003 — Attempt 2

- Added source/execution observability, metrics, API/SQLite/Ollama/Notion health checks, guarded manual refresh, and OpenAPI operation/error contracts.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/README.md`, `tests/backend/test_api_operations.py`
- Commands: 4 API tests pass with 1 explicit dependency skip; 107 backend tests with 49 skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — health and operations contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: full HTTP runtime coverage requires FastAPI/SQLAlchemy dependencies
- Commit subject: feat(api): expose operations and health endpoints
- Commit hash: 35e2d0f5c53e870790e5e58aeb14c15d174f063d

### FRONTEND-002 — Attempt 3

- Added accessible CV review/edit and preference configuration screens with compatibility weights, profile versioning, and reevaluation warning.
- Skills: coder/reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `frontend/src/styles.css`, `tests/frontend/test_frontend_profile.py`, `tests/frontend/test_frontend_bootstrap.py`
- Commands: frontend suite 8/8 pass; `git diff --check`; build/Playwright skipped for missing dependencies/browser
- Tester: PASS — CV/profile, weights, reevaluation and accessibility contracts covered
- Reviewer: APPROVED — UI/accessibility/performance review complete
- Risks: install frontend dependencies before build and browser E2E validation
- Commit subject: feat(web): add profile configuration screens
- Commit hash: ba255f900fc137ae0d66a306115010479c6f567e

### FRONTEND-003 — Attempt 1

- Added paginated vacancy dashboard with composed filters, sorting, lifecycle status indicators, empty state and responsive accessible layout.
- Skills: coder/reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `frontend/src/styles.css`, `tests/frontend/test_frontend_dashboard.py`
- Commands: frontend suite 13 tests pass; compileall; `git diff --check`; npm build skipped because node_modules/tsc unavailable
- Tester: PASS — dashboard contracts covered
- Reviewer: APPROVED — UI/accessibility/performance review complete
- Risks: install frontend dependencies before build and browser E2E validation
- Commit subject: feat(web): add vacancy search dashboard
- Commit hash: ed64711c8cde79cccf40cdd7ceadae823a4b3285

### FRONTEND-004 — Attempt 1

- Added accessible vacancy detail view with compatibility explanation, recommendations, gaps, full links and safe external link attributes.
- Skills: coder/reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `frontend/src/styles.css`, `tests/frontend/test_frontend_detail.py`
- Commands: frontend suite 17 tests pass; compileall; `git diff --check`; npm build skipped because node_modules/tsc unavailable
- Tester: PASS — detail and link safety contracts covered
- Reviewer: APPROVED — UI/accessibility/performance review complete
- Risks: install frontend dependencies before build and browser E2E validation
- Commit subject: feat(web): add vacancy detail and recommendations
- Commit hash: d2e3a74f66fc06f0303f3694bd217a80b064246e

### FRONTEND-005 — Attempt 2

- Added operations dashboard with source toggles, metrics, health, executions, errors, refresh, loading/error/empty states and reduced-motion support.
- Skills: coder/reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/styles.css`, `tests/frontend/test_frontend_operations.py`
- Commands: frontend suite 23 tests pass; compileall; `git diff --check`; npm build skipped because node_modules/tsc unavailable
- Tester: PASS — operations and accessibility contracts covered
- Reviewer: APPROVED — UI/accessibility/performance review complete
- Risks: install frontend dependencies before build and browser E2E validation
- Commit subject: feat(web): add operations dashboard
- Commit hash: 27504d74048a1f966097a3ff3e91794e0419dd90

### OPS-001 — Attempt 1

- Added backend/frontend Dockerfiles, Compose services, persistent data/model volumes, healthcheck, nginx SPA/API proxy, and local/external Ollama configuration.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `README.md`
- Commands: docker compose configs pass; backend 107 tests with 49 skips; compileall; harness validation; `git diff --check`; Docker build skipped daemon unavailable
- Tester: PASS — container/static contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: Docker daemon unavailable for image build; frontend dependency lockfile remains future hardening
- Commit subject: build(ops): add local container orchestration
- Commit hash: 68a3857721766ef653ffe8e6cabca4b1fb12f490

### OPS-002 — Attempt 3

- Added one-command pipeline for ingestion, normalization, deterministic scoring, optional local analysis and Notion synchronization with per-stage failure isolation and partial status reporting.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/pipeline.py`, `scripts/run_pipeline.py`, `tests/backend/test_pipeline.py`
- Commands: 109 backend tests with 50 explicit optional-dependency skips; compileall backend/scripts; py_compile; harness validation; `git diff --check`
- Tester: PASS — pipeline ordering, CLI flags and persisted source errors covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: live SQLAlchemy/Notion/Ollama runtime requires dependencies and services
- Commit subject: feat(ops): add end-to-end job pipeline command
- Commit hash: 30e709dc8d076a01afe5315cd9f0b23e6248bc90

### OPS-003 — Attempt 3

- Added shared flock locking across manual/API/scheduler runs, daily cron example with safe log directory creation, and auditable skip status.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/process_lock.py`, `backend/app/factory.py`, `scripts/run_pipeline.py`, `scripts/scheduler.py`, `scripts/jobscrapper.cron.example`, `tests/backend/test_scheduler_lock.py`, `scripts/README.md`, `backend/README.md`
- Commands: scheduler lock suite 5 tests pass with 1 explicit API dependency skip; compileall; py_compile; bash syntax; harness validation; `git diff --check`
- Tester: PASS — lock and scheduler contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: Docker/system service runtime remains environment-dependent
- Commit subject: feat(ops): add daily scheduler and run locking
- Commit hash: fd01a629ab82d7448035ab437915a22e5a221b3c

### OPS-004 — Attempt 2

- Added JSON rotating/redacted logs, configurable CPU/memory/concurrency limits, Compose resource limits, and persisted duration/source/error/concurrency metrics.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/observability.py`, `backend/app/config.py`, `backend/app/factory.py`, `backend/app/pipeline.py`, `scripts/run_pipeline.py`, `docker-compose.yml`, `tests/backend/test_observability.py`, `backend/README.md`
- Commands: 118 backend tests with 51 explicit optional-dependency skips; observability 4 tests pass; compileall; py_compile; compose config; harness validation; `git diff --check`
- Tester: PASS — observability and limits covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: live container resource enforcement depends on runtime platform
- Commit subject: feat(ops): add observable resource-bounded execution
- Commit hash: 995f132d1314447a94994d5b0f2c5d5f643523ce

### OPS-005 — Attempt 1

- Added operations script and documentation for reboot restart, backups/restores, updates, rollback, recovery and health checks with destructive confirmations.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `scripts/ops.sh`, `docs/OPERATIONS.md`, `README.md`
- Commands: bash syntax/help/static safeguard checks; compileall; harness validation; `git diff --check`; shellcheck unavailable
- Tester: PASS — maintenance safeguards covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: shellcheck unavailable; runtime Docker/service checks remain environment-dependent
- Commit subject: docs(ops): document recovery and maintenance
- Commit hash: 4e75c423fd82cdb66c20873c6b7ca1a2f1cdfea4

### TEST-001 — Attempt 1

- Added representative and ambiguous fixtures for job parsing, normalization, regions/modalities, canonical identity, content hashes and deterministic snapshots.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `tests/backend/test_job_fixtures.py`
- Commands: related suite 23 tests with 23 explicit SQLAlchemy skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — fixture contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: runtime persistence fixtures require SQLAlchemy installation
- Commit subject: test(jobs): cover parsing normalization and deduplication
- Commit hash: 4ee0851ae05cb8b24433d7aada4635dd7f9474af

### TEST-004 — Attempt 1

- Added API 404/422 envelope tests and React component contracts for profile, preferences, vacancy list/detail and operations views.
- Skills: coder vercel-react-best-practices, web-design-guidelines; tester webapp-testing; reviewer vercel-react-best-practices, web-design-guidelines
- Files: `tests/backend/test_api_jobs.py`, `tests/frontend/test_frontend_contracts.py`
- Commands: API/frontend suite 44 tests with 11 optional skips; compileall; harness validation; `git diff --check`
- Tester: PASS — API and UI contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: runtime API tests depend on optional FastAPI/SQLAlchemy packages
- Commit subject: test(app): cover API contracts and UI components
- Commit hash: 48faecd0155fece17afc0a2cac17e9514969e9e2

### TEST-003 — Attempt 1

- Added retry-safe Notion reconciliation coverage for 429 responses, audit attempts, idempotency and source isolation contracts.
- Skills: coordinator none; coder notion-api; tester none; reviewer notion-api
- Files: `tests/backend/test_notion_sync.py`
- Commands: pipeline/connectors/Notion suites 27 tests with 12 optional skips; compileall; harness validation; `git diff --check`
- Tester: PASS — integration resilience covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: connector runtime tests require SQLAlchemy installation
- Commit subject: test(integration): cover source and Notion synchronization
- Commit hash: 7b61bce5825108d29ae37fb8cbbb308b0abe6dd6

### TEST-002 — Attempt 1

- Added tests for bounded/reproducible compatibility scores, Ollama retries and deterministic fallback when the local model is unavailable.
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `tests/backend/test_matching.py`, `tests/backend/test_ollama.py`
- Commands: matching/ollama suites 16 tests with 9 optional skips; compileall; harness validation; `git diff --check`
- Tester: PASS — scoring and local model resilience covered
- Reviewer: APPROVED — implementation and scope verified
- Risks: runtime fallback test requires SQLAlchemy installation
- Commit subject: test(match): cover scoring and local model fallback
- Commit hash: 4cf7ff545a9b6b1615f9bba7f7cdbadd8fbc2da8
