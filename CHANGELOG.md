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
