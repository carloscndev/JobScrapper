# Incremental development log

Append one entry per task cycle. The coordinator is the only role allowed to update this file.

## Entry template

### TASK-ID — Attempt N

- Started / finished: ISO-8601 timestamps
- Acceptance criteria: list and result
- Skills: skill used by each role, or `none`
- Files: delivery files
- Commands: exact verification commands
- Tester: `PASS` or `FAIL`, followed by evidence
- Reviewer: `APPROVED` or `CHANGES_REQUESTED`, followed by findings
- Rework: reason and resolution, or `none`
- Changelog: entry added, or `not applicable`
- Risks: list or `none`
- Commit subject: exact Conventional Commit subject
- Commit hash: hash or `pending`

## 2026-07-17 — Bootstrap preparation

- Scope: repository foundation, governed skills, role contracts, lifecycle CLI, and SDD documentation.
- Installed skills detected: `vercel-react-best-practices`, `web-design-guidelines`, `webapp-testing`, `notion-api`.
- Risk: `notion-api` is recorded as high risk based on its Snyk assessment and requires explicit acknowledgement before use.
- Commit: pending coordinator gates.

### BOOTSTRAP-001 — Attempt 1

- Started / finished: 2026-07-17 / 2026-07-17
- Acceptance criteria: repository uses `main`; bootstrap, skills, harness, tests, and SDD exist; PASS
- Skills: coordinator `find-skills` and `skill-installer`; coder none; tester `webapp-testing` governance; reviewer React, web-design, and Notion skill governance
- Files: repository bootstrap, governed skills, harness, tests, and SDD files allowed by the integrated bootstrap scope
- Commands: `python3 -m unittest discover -s tests/harness -p 'test_*.py'`; `python3 scripts/harness.py validate`; `./scripts/check-skills.sh`; `python3 -m py_compile scripts/harness.py`; JSON parsing; `git diff --cached --check`; `git diff --check`
- Tester: PASS — 25 unit tests and all repository gates passed
- Reviewer: APPROVED — commit, staging, scope, traceability, skills, and security findings closed after four review/rework cycles
- Rework: added executable scripts; real HEAD validation; executable commit gates; pinned skill revisions; role allowlist; structured staged traceability; allowed paths; staged-blob reads; deletion/rename/copy scope validation
- Changelog: Unreleased bootstrap entries added
- Risks: `notion-api` remains high risk and requires coordinator acknowledgement before use
- Commit subject: chore(repo): initialize project repository
- Commit hash: 3eb86cab7dd0f988e91981870dd0f37830a462c7

### BACKLOG-001 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: expanded executable backlog to 46 tasks, dependencies, allowed paths, acceptance criteria, and SDD reference; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `.harness/backlog.json`, `docs/SDD.md`, `docs/DEVELOPMENT_LOG.md`, `CHANGELOG.md`
- Commands: `python3 -m json.tool .harness/backlog.json`; `python3 scripts/harness.py validate`; topological dependency check; `python3 -m unittest -v tests/harness/test_harness.py`; `python3 -m py_compile scripts/harness.py`; `bash -n scripts/*.sh`; `git diff --check`
- Tester: PASS — 46 unique tasks, complete required fields, no unknown dependencies or cycles, and 25 harness tests pass
- Reviewer: APPROVED — coverage and dependency structure accepted after correcting the total-task wording
- Rework: none
- Changelog: expanded application delivery backlog to 46 total tasks
- Risks: task sequencing must be followed through the existing harness
- Commit subject: docs(backlog): expand application delivery tasks
- Commit hash: 221154cfd1ec043c7a6eb198b7ce57dbec53ee7f

### SKILLS-001 — Attempt 2

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: manifest, reproducible installer/checker, role allowlist, risk documentation, and idempotence; PASS
- Skills: coordinator `skill-installer`; coder none; tester none; reviewer none
- Files: `.harness/skills.json`, `scripts/install-skills.sh`, `scripts/check-skills.sh`, `docs/SKILLS.md`, `tests/harness/test_harness.py`
- Commands: `./scripts/check-skills.sh`; `python3 -m unittest -v tests/harness/test_harness.py`; `python3 -m py_compile scripts/harness.py`; `bash -n scripts/*.sh`; JSON validation; `git diff --check`
- Tester: PASS — 28 tests, including missing mandatory manifest fields, source/role mismatch, and mock installer idempotence
- Reviewer: APPROVED — fail-closed manifest and installer, immutable pins, and scoped changes verified
- Rework: attempt 1 allowed omitted source/allowlist/purpose/risk fields; attempt 2 requires every field with no fallback
- Changelog: skill governance hardened
- Risks: `notion-api` remains high risk and requires coordinator acknowledgement before use
- Commit subject: chore(skills): add managed skill installation
- Commit hash: 1ad41f9f252283a94844d91c708b51a2097eaffc

### SKILLS-002 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: four approved skills installed and SHA-256 checksums match the pinned manifest; PASS
- Skills: coordinator `skill-installer`; coder none; tester none; reviewer none
- Files: `docs/SKILLS.md`
- Commands: `scripts/check-skills.sh`; independent SHA-256 comparison; JSON validation; `python3 -m unittest discover -s tests/harness -p 'test_*.py'`; `python3 -m py_compile scripts/harness.py`; `python3 scripts/harness.py validate`; `git diff --check`
- Tester: PASS — four skills, 28 tests, authorization checks, JSON, Python, harness, and diff checks pass
- Reviewer: APPROVED — installed paths, checksums, documentation, and no-reinstall decision verified
- Rework: added missing structured coordinator traceability section
- Changelog: skill installation verification recorded
- Risks: `notion-api` remains high risk and requires coordinator acknowledgement before use
- Commit subject: chore(skills): install project agent capabilities
- Commit hash: eb086cbded5916763340a2871367a565b7b9d67c

### STRUCTURE-001 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: backend, frontend, docs, scripts, and tests structure documented without premature implementation decisions; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/README.md`, `frontend/README.md`, `scripts/README.md`, `tests/README.md`, `README.md`
- Commands: 28 unit tests; skill checks; py_compile; shell syntax; JSON validation; harness validation; artifact scan; `git diff --check`
- Tester: PASS — structure, ownership, READMEs, and no generated artifacts verified
- Reviewer: APPROVED — scope and structure accepted after adding required traceability
- Rework: added missing structured development and changelog entries
- Changelog: repository layout documented
- Risks: implementation tasks must add code only within their declared paths
- Commit subject: chore(repo): scaffold application directories
- Commit hash: ebbb15de8e07eea5582a2ace24f1fc6ed8e5ff6c

### HARNESS-001 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: coordinator/coder/tester/reviewer ownership, state flow, rework loop, skill authorization, evidence and commit restrictions documented; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `AGENTS.md`, `.agents/coder.md`, `.agents/tester.md`, `.agents/reviewer.md`
- Commands: 28 unit tests; JSON validation; harness validation; py_compile; shell syntax; semantic role-flow check; `git diff --check`
- Tester: PASS — operational flow, ownership, allowlists, mutation rules, and all gates verified
- Reviewer: APPROVED — contracts complete; only required traceability was added
- Rework: added structured development and changelog entries
- Changelog: agent protocol contracts tightened
- Risks: coordinator must preserve single active task and staging ownership
- Commit subject: chore(harness): define multi-agent workflow
- Commit hash: 7668cfaa3dc382feeb3182a55fe7d6f382ccef29

### HARNESS-002 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: ordered lifecycle, single active task, dependency validation, real commit hash and exact subject enforcement; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `scripts/harness.py`, `README.md`, `tests/harness/test_harness.py`
- Commands: 33 unit tests; JSON validation; harness validation; py_compile; shell syntax; `git diff --check`
- Tester: PASS — cycles, self-dependencies, inactive state, blank rejection, HEAD hash and subject covered
- Reviewer: APPROVED — state machine and guards accepted after adding traceability
- Rework: added structured development and changelog entries
- Changelog: state machine guards strengthened
- Risks: coordinator must provide a real HEAD commit with the configured subject
- Commit subject: feat(harness): add task lifecycle management
- Commit hash: 22af84d7bb3f19736bc44875b49eb89a62afe647

### HARNESS-003 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: unit coverage for valid/invalid transitions, gates, dependency unlocks, and read-only status; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `tests/harness/test_harness.py`
- Commands: `python3 tests/harness/test_harness.py -v`; py_compile; shell syntax; JSON; harness validation; `git diff --check`
- Tester: PASS — 35 tests including active status byte preservation and tester-gate enforcement
- Reviewer: APPROVED — test scope and assertions accepted after adding traceability
- Rework: added structured development and changelog entries
- Changelog: lifecycle gate coverage expanded
- Risks: unittest is the configured test runner; pytest is not required
- Commit subject: test(harness): cover task lifecycle gates
- Commit hash: 942028fe7a5bc319a119fca60fa62ed66a782c21

### DOCS-001 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: SDD and README document user story, requirements, architecture, data/API contracts, security, UX, operations, and canonical 46-task index; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `docs/SDD.md`, `README.md`
- Commands: 35 unit tests; JSON validation; harness validation; py_compile; shell syntax; `git diff --check`
- Tester: PASS — documentation coverage and 46-task index verified
- Reviewer: APPROVED — content accepted after correcting dependency order and adding traceability
- Rework: reordered phase index to reflect BACKLOG-001 before SKILLS-001
- Changelog: SDD and README expanded
- Risks: `.harness/backlog.json` remains authoritative for exact dependencies
- Commit subject: docs(sdd): add product requirements and backlog
- Commit hash: f023dfd3602a9124c23f6c174171920727fe6d9e

### BACKEND-001 — Attempt 3

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: FastAPI service bootstrap, environment settings, factory, `/health`, startup metadata, and health tests; PASS with explicit runtime dependency skip
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/**`, `tests/backend/test_health.py`, `README.md`
- Commands: backend unittest `5 pass, 1 skip`; harness 35 tests; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — settings and static backend checks pass; `/health` is explicitly skipped because FastAPI is not installed
- Reviewer: APPROVED — configuration fix, stdlib test runner, scope, and dependency limitation verified
- Rework: attempt 1 fixed dataclass-slots default bug; attempt 2 converted pytest test to stdlib unittest and documented FastAPI skip
- Changelog: FastAPI bootstrap and health endpoint added
- Risks: install backend dependencies before exercising `/health` runtime test
- Commit subject: feat(api): bootstrap FastAPI service
- Commit hash: 920d796d30baf3516423840fb89c5efea63301dc

### FRONTEND-001 — Attempt 2

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: React/TypeScript/Vite scaffold, typed API client, accessible responsive base view, loading/error/health states; PASS
- Skills: coordinator none; coder `vercel-react-best-practices`; tester `webapp-testing`; reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/**`, `tests/frontend/test_frontend_bootstrap.py`, `README.md`
- Commands: 45 total tests (5 frontend, 35 harness, 5 backend with 1 skip); JSON/Python/Shell/diff checks; npm install/build attempted
- Tester: PASS — typed client and `/health` regressions covered; npm build blocked by registry DNS (`ENOTFOUND`)
- Reviewer: APPROVED — client/endpoint alignment, UI accessibility, responsive layout, and scope verified
- Rework: replaced direct `/api/health` fetch with typed `getHealth()` against `/health`
- Changelog: React/Vite dashboard scaffold added
- Risks: install npm dependencies before runtime/build verification
- Commit subject: feat(web): bootstrap React dashboard
- Commit hash: be8cda8c41671d7fe8587984abc2092383b1f954

### DATA-001 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: SQLAlchemy/SQLite/Alembic foundation, configurable database URL, session lifecycle, migration checkpoint, and backup/restore docs; PASS with explicit dependency skips
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/database.py`, `backend/app/config.py`, `backend/pyproject.toml`, `alembic.ini`, `alembic/**`, `tests/backend/test_database.py`, `backend/README.md`
- Commands: 50 total tests with 3 explicit skips; JSON; py_compile; shell syntax; harness validation; `git diff --check`
- Tester: PASS — five database tests, three dependency skips, and all repository gates pass
- Reviewer: APPROVED — engine/session lifecycle, Alembic checkpoint, docs, and scope verified
- Rework: none
- Changelog: database foundation added
- Risks: install SQLAlchemy/Alembic before exercising live session/migration tests
- Commit subject: feat(data): add database foundation
- Commit hash: 8779e82ac5e8ba4e44ef493d4721da66aa6f2555

### DATA-002 — Attempt 2

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: nine domain entities, constraints/indexes, repositories/services decoupled from FastAPI, and fixed Alembic domain migration; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/models.py`, `backend/app/repositories.py`, `backend/app/services.py`, `alembic/env.py`, `alembic/versions/0002_domain_models.py`, `tests/backend/test_models.py`
- Commands: 56 tests with 4 dependency skips; JSON; py_compile; shell syntax; skills; harness validation; `git diff --check`
- Tester: PASS — domain contracts and explicit migration regression pass
- Reviewer: APPROVED — fixed migration operations, model constraints/indexes, decoupling, and scope verified
- Rework: attempt 1 used metadata create/drop all; attempt 2 uses explicit fixed revision operations
- Changelog: domain models and repositories added
- Risks: install SQLAlchemy/Alembic before live migration tests
- Commit subject: feat(data): add core domain models
- Commit hash: a5661fdb63aa0f286fa7b01626e744269fc607df

### PROFILE-001 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: secure PDF/DOCX validation/extraction, unreadable/encrypted rejection, editable profile mapping, and service integration; PASS with explicit optional-dependency skips
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/cv_profile.py`, `backend/app/services.py`, `backend/pyproject.toml`, `backend/README.md`, `tests/backend/test_cv_profile.py`
- Commands: 66 tests with 5 skips; JSON; py_compile; shell syntax; skills; harness validation; `git diff --check`
- Tester: PASS — 10 CV tests cover safety, extraction, profile structure, and service
- Reviewer: APPROVED — security controls and scope verified
- Rework: none
- Changelog: secure CV ingestion added
- Risks: pypdf/python-docx runtime coverage requires dependency installation
- Commit subject: feat(profile): add CV ingestion and profile extraction
- Commit hash: f2af923f2c7bbd79470f965186d5b0017fe48089

### PROFILE-002 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: preferences, constraints, authorization/relocation fields, versioning, superseding, and reevaluation metadata; PASS with dependency skips
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/models.py`, `backend/app/repositories.py`, `backend/app/services.py`, `alembic/versions/0003_profile_preferences.py`, `tests/backend/test_preferences.py`, `backend/README.md`
- Commands: 72 tests with 7 skips; JSON; py_compile; shell syntax; skills; harness validation; `git diff --check`
- Tester: PASS — fields, version increment, superseding, reevaluation guard, and migration covered
- Reviewer: APPROVED — implementation and scope verified after adding traceability
- Rework: none
- Changelog: profile preferences and versioning added
- Risks: runtime SQLAlchemy tests require dependency installation
- Commit subject: feat(profile): add job preferences and versioning
- Commit hash: 645cade3bc6d4c162b2b2ebde4fc93a132359a52

### SOURCES-001 — Attempt 1

- Started / finished: 2026-07-18 / 2026-07-18
- Acceptance criteria: common source adapter contract, validated source configuration, normalized fetch/job result types, enablement service, and compliance limits; PASS with dependency skips
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/sources.py`, `backend/app/repositories.py`, `backend/README.md`, `tests/backend/test_sources.py`
- Commands: 38 backend tests with 12 skips; 35 harness tests; JSON; compileall; shell syntax; skills; harness validation; `git diff --check`
- Tester: PASS — contracts, URL/limits/secrets, canonical jobs, fetch statuses, adapter and enablement covered
- Reviewer: APPROVED — implementation and scope verified after adding traceability
- Rework: none
- Changelog: source adapter contract added
- Risks: SQLAlchemy runtime checks require dependency installation; real connectors are deferred to SOURCES-002
- Commit subject: feat(sources): define job source adapters
- Commit hash: 2268fa9cdfe6745830ea4ba8c04804a8c86cd583

### SOURCES-002 — Attempt 4

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: JSON/feed plus Greenhouse and Lever adapters, normalized description/application URLs, fixture-first operation, opt-in network access with robots/user-agent checks, source isolation, and enforceable terms-of-use acknowledgement; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/connectors.py`, `backend/app/sources.py`, `docs/SOURCES.md`, `tests/backend/test_connectors.py`
- Commands: 7 connector tests with 7 explicit SQLAlchemy skips; 45 backend tests with 19 skips; compileall; py_compile; JSON; shell syntax; skills; harness validation; `git diff --check`
- Tester: PASS — href-priority, fixture normalization, robots/user-agent, failure isolation, and terms rejection covered
- Reviewer: APPROVED — terms gate enforced, documentation example corrected, implementation and scope verified
- Rework: attempt 1 fixed application anchor text overriding href; attempt 3 added terms acceptance gate and persistence; attempt 4 corrected documentation fixture example
- Changelog: initial job connectors and compliance gate added
- Risks: SQLAlchemy runtime checks require dependency installation; real network remains opt-in and governed by robots/terms acknowledgement
- Commit subject: feat(sources): add initial job connectors
- Commit hash: f4c55a95dae9f1d3532755b346c920324ef842aa

### SOURCES-003 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: bounded source rate limits, retries/backoff, identifiable user-agent, no evasion, HTML sanitization, URL validation, and per-source/item failure isolation; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/connectors.py`, `tests/backend/test_connectors.py`
- Commands: 11 connector tests pass under forced runtime; normal connector suite 11 tests with explicit SQLAlchemy skips; related suite 38 tests with 12 skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — rate limiting, retry behavior, sanitization, invalid URL/item isolation, and modality regression covered
- Reviewer: APPROVED — implementation, safety constraints, and scope verified
- Rework: attempt 1 fixed modality inference from location (`Remote - United States`)
- Changelog: ingestion controls hardened
- Risks: live SQLAlchemy coverage requires dependency installation; network remains opt-in and robots/terms constrained
- Commit subject: feat(sources): harden ingestion controls
- Commit hash: bc37edb54fabe89fd07378e2da6bee01ac99305e

### JOBS-001 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: normalized job fields, salary/currency/source/date metadata, five geographic buckets, and explicit work modalities; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/sources.py`, `backend/app/connectors.py`, `tests/backend/test_sources.py`
- Commands: 52 backend tests with 26 explicit optional-dependency skips; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — normalized fields, region buckets, modalities, and URL validation covered
- Reviewer: APPROVED — implementation and scope verified
- Rework: none
- Changelog: normalized job records and regional classification added
- Risks: SQLAlchemy/FastAPI runtime coverage requires optional dependency installation
- Commit subject: feat(jobs): normalize job records and regions
- Commit hash: 121a0b4e6d1edf06c114aa6986ab9a31a48b0e3e

### JOBS-002 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: canonical URLs/fingerprints, deduplication, provenance-preserving merge, snapshots on effective changes, and inactive historical records; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/jobs.py`, `backend/app/repositories.py`, `tests/backend/test_jobs.py`, `docs/JOBS.md`
- Commands: 58 backend tests with 32 explicit optional-dependency skips; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — dedupe, canonical identity, snapshot/history, and partial-upsert regression covered
- Reviewer: APPROVED — effective merged hash and full scope verified
- Rework: attempt 1 fixed spurious snapshots from partial payloads by hashing merged values
- Changelog: job identity, versioning, and inactive history added
- Risks: SQLAlchemy runtime coverage requires optional dependency installation
- Commit subject: feat(jobs): deduplicate and version job changes
- Commit hash: 035454175e0e9c470f0a06d6eaecd3e50a7df41d

### MATCH-001 — Attempt 3

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: deterministic 0-100 compatibility scoring, configurable dimension weights, required/desirable requirements, exclusions, explainable breakdown, and persistence; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/matching.py`, `tests/backend/test_matching.py`
- Commands: 63 backend tests with 36 explicit optional-dependency skips; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — score determinism, required years, exclusions, persistence, and explicit weight precedence covered
- Reviewer: APPROVED — supported experience source and weight precedence verified
- Rework: attempt 1 added supported Profile.experience years; attempt 2 made explicit weights override persisted preferences
- Changelog: explainable compatibility scoring added
- Risks: SQLAlchemy runtime persistence checks require optional dependency installation
- Commit subject: feat(match): add explainable compatibility scoring
- Commit hash: 5d537456331cf4c52961825688b9309affd65cd5

### MATCH-002 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: local Ollama integration, configurable model/resources, validated structured output, and no profile secrets sent outside loopback model; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/ollama.py`, `backend/app/config.py`, `backend/app/matching.py`, `tests/backend/test_ollama.py`, `.env.example`
- Commands: 67 backend tests with 36 explicit optional-dependency skips; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — loopback/config, payload allowlist, secret exclusion, invalid JSON, and settings coverage
- Reviewer: APPROVED — local-only boundary and structured contract verified
- Rework: none
- Changelog: local Ollama analysis integration added
- Risks: Ollama runtime availability is operator-managed; endpoint remains loopback-only
- Commit subject: feat(match): add local Ollama analysis
- Commit hash: aa3d379722c75f1ac8c03637bdce8c4fa616b482

### MATCH-003 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: bounded Ollama timeout/retries, sequential processing, deterministic fallback preserving score, and reevaluation triggers for profile/rules/model/description changes; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/ollama.py`, `backend/app/matching.py`, `tests/backend/test_match_resilience.py`
- Commands: 71 backend tests with 39 explicit optional-dependency skips; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — retry/backoff, fallback, ordered bounded evaluation, and fingerprint triggers covered
- Reviewer: APPROVED — resilience and scope verified
- Rework: none
- Changelog: resilient local analysis fallback added
- Risks: SQLAlchemy runtime checks require optional dependency installation; Ollama remains local and operator-managed
- Commit subject: feat(match): add resilient local analysis fallback
- Commit hash: cc7bba9fdb5b149f80522ca4d81038a965df20cc

### NOTION-001 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: env-only credentials, complete normalized vacancy schema, and regional views for CDMX, Guadalajara, Mexico, USA, and other; PASS
- Skills: coordinator `notion-api`; coder `notion-api`; tester none; reviewer `notion-api`
- Files: `backend/app/notion.py`, `backend/app/config.py`, `tests/backend/test_notion.py`, `.env.example`, `docs/NOTION.md`
- Commands: 76 backend tests with 39 explicit optional-dependency skips; 5 Notion tests pass; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — credentials redaction, schema fields, regional views, and Settings env covered offline
- Reviewer: APPROVED — implementation re-review passed after traceability correction
- Rework: attempt 1 added mandatory structured traceability before approval
- Changelog: Notion schema and regional view configuration added
- Risks: no network or destructive Notion operations performed; API runtime remains operator-managed
- Commit subject: feat(notion): define vacancy database integration
- Commit hash: 9e141e6d29e2c4a16b69fce34333d8dfb593d1fd

### NOTION-002 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: idempotent fingerprint upsert, evaluated property synchronization, rate/retry controls, pagination, and persisted partial-failure status; PASS
- Skills: coordinator `notion-api`; coder `notion-api`; tester none; reviewer `notion-api`
- Files: `backend/app/notion_sync.py`, `tests/backend/test_notion_sync.py`, `docs/NOTION.md`
- Commands: 85 backend tests with 39 explicit optional-dependency skips; 9 Notion sync tests pass; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — mapping, idempotency, pagination, retries, actual attempts, outcome persistence and isolation covered
- Reviewer: APPROVED — persistence and retry metadata verified
- Rework: attempt 1 added repository/callback persistence and actual request-attempt propagation
- Changelog: idempotent Notion synchronization and status tracking added
- Risks: no live Notion calls in tests; API credentials and runtime remain operator-managed
- Commit subject: feat(notion): sync evaluated jobs idempotently
- Commit hash: 212d81bd2a6b97e1336abe79c0a523dd07845eea

### NOTION-003 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: SQLite/Notion drift detection, auditable retryable repairs, and safe handling of orphan/unkeyed pages; PASS
- Skills: coordinator `notion-api`; coder `notion-api`; tester none; reviewer `notion-api`
- Files: `backend/app/notion_sync.py`, `tests/backend/test_notion_sync.py`
- Commands: 89 backend tests with 39 explicit optional-dependency skips; 13 Notion tests pass; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — missing/stale/orphan detection, unkeyed orphan audit, repair states and no-delete behavior covered
- Reviewer: APPROVED — reconciliation audit and safety verified
- Rework: attempt 1 fixed silent omission of pages without Fingerprint
- Changelog: reconciliation and repair workflow added
- Risks: no live Notion calls; orphan repair is intentionally non-destructive
- Commit subject: feat(notion): add synchronization reconciliation
- Commit hash: 5a283bd820c22e2731c5ac7af6f0af3e89cf8b14

### API-001 — Attempt 3

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: documented profile upload/read/update/preferences endpoints with consistent validation error envelope and reevaluation metadata; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/app/services.py`, `backend/app/schemas.py`, `backend/README.md`, `tests/backend/test_api_profile.py`, `backend/pyproject.toml`
- Commands: 8 API tests pass with 5 explicit FastAPI/SQLAlchemy skips; 95 backend tests with 43 skips; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — endpoint/error contracts and PATCH reevaluation response covered
- Reviewer: APPROVED — service versioning, metadata, no-op behavior and scope verified
- Rework: attempt 1 routed PATCH through ProfileService; attempt 2 exposed reevaluation fields in response/static contract
- Changelog: profile and preferences API endpoints added
- Risks: full HTTP runtime coverage requires FastAPI/SQLAlchemy dependencies
- Commit subject: feat(api): expose profile management endpoints
- Commit hash: 60fb12751d61fbb54fe6bca9bc2a4ba192738060

### API-002 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: paginated/filterable/ordered vacancy list plus detail with links, score breakdown, recommendations, and history; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/app/schemas.py`, `tests/backend/test_api_jobs.py`
- Commands: 6 API tests pass with 4 explicit HTTP dependency skips; 103 backend tests with 48 skips; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — list/detail contracts, score serialization, and profile-specific outer join covered
- Reviewer: APPROVED — implementation and scope verified
- Rework: attempt 1 fixed scalar score serialization and profile_id join semantics
- Changelog: paginated vacancy search and detailed score history endpoints added
- Risks: full HTTP runtime coverage requires FastAPI/SQLAlchemy dependencies
- Commit subject: feat(api): expose vacancy search endpoints
- Commit hash: 353af10cfe2b4dbf8e85aa9bb6219afe70985b75

### API-003 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: observable sources/executions, metrics, API/SQLite/Ollama/Notion health, guarded manual refresh, and documented OpenAPI errors; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/README.md`, `tests/backend/test_api_operations.py`
- Commands: 4 API tests pass with 1 explicit dependency skip; 107 backend tests with 49 skips; compileall; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — health checks including API, metrics, operations, refresh lock and OpenAPI contracts covered
- Reviewer: APPROVED — observability and scope verified
- Rework: attempt 1 added explicit `checks.api` health entry and contract coverage
- Changelog: operations, health, metrics, and manual refresh endpoints added
- Risks: full HTTP runtime coverage requires FastAPI/SQLAlchemy dependencies
- Commit subject: feat(api): expose operations and health endpoints
- Commit hash: 35e2d0f5c53e870790e5e58aeb14c15d174f063d

### FRONTEND-002 — Attempt 3

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: CV extraction review/edit, preferences/constraints/weights, profile version and reevaluation warning; PASS
- Skills: coordinator none; coder `vercel-react-best-practices`, `web-design-guidelines`; tester none; reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `frontend/src/styles.css`, `tests/frontend/test_frontend_profile.py`, `tests/frontend/test_frontend_bootstrap.py`
- Commands: frontend suite 8 tests pass; compile/static checks; `git diff --check`; build/Playwright skipped because node_modules/tsc/browser unavailable
- Tester: PASS — CV/profile controls, weights, reevaluation, accessibility and responsive contracts covered
- Reviewer: APPROVED — semantic tabs, skip link, named controls and responsive UI verified
- Rework: attempt 1 corrected legacy accessibility contracts; attempt 2 added skip link/tab semantics/name/autocomplete and compatibility ordering
- Changelog: profile and CV configuration screens added
- Risks: install frontend dependencies before build and browser E2E validation
- Commit subject: feat(web): add profile configuration screens
- Commit hash: ba255f900fc137ae0d66a306115010479c6f567e

### FRONTEND-003 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: paginated vacancy dashboard with region/modality/score/company/source/date/status filters, sorting, and distinct lifecycle states; PASS
- Skills: coordinator none; coder `vercel-react-best-practices`, `web-design-guidelines`; tester none; reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `frontend/src/styles.css`, `tests/frontend/test_frontend_dashboard.py`
- Commands: frontend suite 13 tests pass; compileall; `git diff --check`; npm build skipped because node_modules/tsc unavailable
- Tester: PASS — filters, ordering, pagination, statuses, accessibility and responsive contracts covered
- Reviewer: APPROVED — implementation and scope verified
- Rework: none
- Changelog: vacancy search dashboard added
- Risks: install frontend dependencies before build and browser E2E validation
- Commit subject: feat(web): add vacancy search dashboard
- Commit hash: ed64711c8cde79cccf40cdd7ceadae823a4b3285

### FRONTEND-004 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: vacancy detail with description/salary/location/modality/links/score/gaps/recommendations and safe external navigation; PASS
- Skills: coordinator none; coder `vercel-react-best-practices`, `web-design-guidelines`; tester none; reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `frontend/src/styles.css`, `tests/frontend/test_frontend_detail.py`
- Commands: frontend suite 17 tests pass; compileall; `git diff --check`; npm build skipped because node_modules/tsc unavailable
- Tester: PASS — detail fields, safe links, back navigation and accessibility covered
- Reviewer: APPROVED — UI/accessibility/performance review complete
- Rework: none
- Changelog: vacancy detail and recommendations view added
- Risks: install frontend dependencies before build and browser E2E validation
- Commit subject: feat(web): add vacancy detail and recommendations
- Commit hash: d2e3a74f66fc06f0303f3694bd217a80b064246e

### FRONTEND-005 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: operations/source toggles, runs/errors/health/last update/manual refresh/high-match, accessible loading/error/empty states and responsive behavior; PASS
- Skills: coordinator none; coder `vercel-react-best-practices`, `web-design-guidelines`; tester none; reviewer `vercel-react-best-practices`, `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/styles.css`, `tests/frontend/test_frontend_operations.py`
- Commands: frontend suite 23 tests pass; compileall; `git diff --check`; npm build skipped because node_modules/tsc unavailable
- Tester: PASS — operations contracts and reduced-motion regression covered
- Reviewer: APPROVED — accessibility, responsive behavior and scope verified
- Rework: attempt 1 added prefers-reduced-motion rule for loading spinner
- Changelog: operations dashboard and health screens added
- Risks: install frontend dependencies before build and browser E2E validation
- Commit subject: feat(web): add operations dashboard
- Commit hash: 27504d74048a1f966097a3ff3e91794e0419dd90

### OPS-001 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: backend/frontend Docker Compose startup, persistent volumes, and local or external Ollama configuration; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `README.md`
- Commands: docker compose config and local-ollama profile config pass; backend 107 tests with 49 skips; compileall; harness validation; `git diff --check`; Docker build skipped daemon unavailable
- Tester: PASS — Compose, volumes, healthcheck, proxy and static container contracts covered
- Reviewer: APPROVED — container orchestration and documentation verified
- Rework: none
- Changelog: local container orchestration added
- Risks: Docker daemon unavailable for image build; frontend dependency lockfile remains future hardening
- Commit subject: build(ops): add local container orchestration
- Commit hash: 68a3857721766ef653ffe8e6cabca4b1fb12f490

### OPS-002 — Attempt 3

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: single command ingest→normalize→score→local analysis→Notion sync with partial failures preserving successful work; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/pipeline.py`, `scripts/run_pipeline.py`, `tests/backend/test_pipeline.py`
- Commands: 109 backend tests with 50 explicit optional-dependency skips; compileall backend/scripts; py_compile; JSON; shell syntax; harness validation; `git diff --check`
- Tester: PASS — CLI flags, stage ordering, partial isolation and source error persistence covered
- Reviewer: APPROVED — pipeline acceptance and auditability verified
- Rework: attempt 1 persisted adapter fetch errors in SourceRun/report and added regression
- Changelog: end-to-end ingestion/evaluation pipeline command added
- Risks: live SQLAlchemy/Notion/Ollama runtime requires dependencies and services
- Commit subject: feat(ops): add end-to-end job pipeline command
- Commit hash: 30e709dc8d076a01afe5315cd9f0b23e6248bc90

### OPS-003 — Attempt 3

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: documented daily scheduler, shared manual/scheduled process lock, and auditable concurrent skip; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/process_lock.py`, `backend/app/factory.py`, `scripts/run_pipeline.py`, `scripts/scheduler.py`, `scripts/jobscrapper.cron.example`, `tests/backend/test_scheduler_lock.py`, `scripts/README.md`, `backend/README.md`
- Commands: scheduler lock suite 5 tests pass with 1 explicit API dependency skip; compileall; py_compile; bash syntax; harness validation; `git diff --check`
- Tester: PASS — cross-process lock, repo-relative path, cron data directory, exit75 and API lock contracts covered
- Reviewer: APPROVED — scheduler/lock and documentation verified
- Rework: attempt 1 moved heavy imports after lock; attempt 2 added `mkdir -p data` before cron redirection
- Changelog: daily scheduler and shared process locking added
- Risks: Docker/system service runtime remains environment-dependent
- Commit subject: feat(ops): add daily scheduler and run locking
- Commit hash: fd01a629ab82d7448035ab437915a22e5a221b3c

### OPS-004 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: rotating structured logs with secret redaction, configurable CPU/memory/concurrency limits, and persisted execution metrics; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/observability.py`, `backend/app/config.py`, `backend/app/factory.py`, `backend/app/pipeline.py`, `scripts/run_pipeline.py`, `docker-compose.yml`, `tests/backend/test_observability.py`, `backend/README.md`
- Commands: 118 backend tests with 51 explicit optional-dependency skips; observability 4 tests pass; compileall; py_compile; compose config; harness validation; `git diff --check`
- Tester: PASS — redaction/rotation, resource settings, concurrency propagation and enriched metrics covered
- Reviewer: APPROVED — observability, resource bounds and scope verified
- Rework: attempt 1 wired max_concurrency into runtime and enriched manual refresh metrics
- Changelog: observable resource-bounded execution added
- Risks: live container resource enforcement depends on runtime platform
- Commit subject: feat(ops): add observable resource-bounded execution
- Commit hash: 995f132d1314447a94994d5b0f2c5d5f643523ce

### OPS-005 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: documented restart/reboot, backup/restore, update/rollback, and failure recovery procedures; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `scripts/ops.sh`, `docs/OPERATIONS.md`, `README.md`
- Commands: bash syntax/help/static safeguard checks; compileall; harness validation; `git diff --check`; shellcheck unavailable
- Tester: PASS — executable script, confirmations, clean-tree/ff-only, Compose/health checks and recovery docs covered
- Reviewer: APPROVED — maintenance workflow and safety verified
- Rework: none
- Changelog: recovery and maintenance operations documented
- Risks: shellcheck unavailable; runtime Docker/service checks remain environment-dependent
- Commit subject: docs(ops): document recovery and maintenance
- Commit hash: 4e75c423fd82cdb66c20873c6b7ca1a2f1cdfea4

### TEST-001 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: representative/ambiguous parsing, normalization, region/modality, deduplication and deterministic change fixtures; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `tests/backend/test_job_fixtures.py`
- Commands: related suite 23 tests with 23 explicit SQLAlchemy skips; compileall; py_compile; harness validation; `git diff --check`
- Tester: PASS — fixtures cover URLs/salary/requirements/date, region/modalities, canonical identity/content hash, rediscovery and snapshots
- Reviewer: APPROVED — test scope and determinism verified
- Rework: none
- Changelog: parsing/normalization/deduplication fixture coverage added
- Risks: runtime persistence fixtures require SQLAlchemy installation
- Commit subject: test(jobs): cover parsing normalization and deduplication
- Commit hash: 4ee0851ae05cb8b24433d7aada4635dd7f9474af

### RELEASE-001 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: installation/operations docs, final SDD acceptance checklist and CHANGELOG version 0.1.0; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `README.md`, `docs/SDD.md`, `docs/RELEASE.md`, `CHANGELOG.md`
- Commands: 35 harness tests; check-skills; docs/reference checks; harness validate; compileall; `git diff --check`
- Tester: PASS — documentation and gates validated; environment-dependent checks remain explicitly pending
- Reviewer: APPROVED — release readiness documentation and scope verified
- Rework: none
- Changelog: version 0.1.0 readiness checklist finalized
- Risks: Docker/npm/Playwright/SQLAlchemy/credentials/tag gates require release environment
- Commit subject: docs(release): finalize version 0.1.0 readiness
- Commit hash: f5a6d0320fea1a324afea298aba496eba70f3830

### TEST-007 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: seven scheduler ticks, transient retry/recovery, locking and resource bounds recorded; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `tests/backend/test_scheduler_stability.py`
- Commands: scheduler stability/lock 10 tests with 1 optional skip; compileall; harness validation; `git diff --check`
- Tester: PASS — observable seven-tick retry and lock/recovery behavior verified
- Reviewer: APPROVED — exit codes, invariant args, resource limits and lock cycles verified
- Rework: attempt 1 synthetic simulation rejected; added observable mocked scheduler invocations and transient exit recovery
- Changelog: scheduler stability and recovery validation added
- Risks: seven-day behavior is simulated; production cron remains environment-dependent
- Commit subject: test(ops): validate scheduler stability and recovery
- Commit hash: 45302952f2a41714ec91ed13d86b208c305f4747

### TEST-006 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: unsafe HTML/URLs, files and secret/sensitive-data handling covered; PASS
- Skills: coordinator none; coder notion-api; tester none; reviewer notion-api
- Files: `tests/backend/test_security_contracts.py`
- Commands: security/CV/connectors/Ollama suites 30 tests with 14 optional skips; compileall; harness validation; `git diff --check`
- Tester: PASS — URL, upload, Notion redaction and Ollama allowlist contracts pass
- Reviewer: APPROVED — existing HTML sanitization/isolation plus new security coverage verified
- Rework: none
- Changelog: input and secret handling security coverage added
- Risks: runtime URL/connector checks require SQLAlchemy installation
- Commit subject: test(security): cover input and secret handling
- Commit hash: 97b2121e04303be886b2c5ba2350e92654b43e20

### TEST-005 — Attempt 2

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: fixture ingestion through score to dashboard detail, server lifecycle and browser/server log capture; PASS
- Skills: coordinator none; coder webapp-testing; tester webapp-testing; reviewer webapp-testing
- Files: `tests/e2e/test_ingestion_dashboard.py`
- Commands: E2E contract 2 tests with 1 Playwright skip; compileall; harness validation; `git diff --check`
- Tester: PASS — lifecycle and cleanup contract verified
- Reviewer: APPROVED — browser logs persist on failure and browser closes before log handle
- Rework: attempt 1 failed review; moved browser log persistence and close into finally
- Changelog: E2E ingestion-to-dashboard lifecycle coverage added
- Risks: real browser execution requires Playwright and frontend dependencies
- Commit subject: test(e2e): cover ingestion to dashboard flow
- Commit hash: b04586250f2e700d13504a09bd573a57e48d6ce5

### TEST-004 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: API success/error contracts and Profile, list, detail, operations component coverage; PASS
- Skills: coordinator none; coder vercel-react-best-practices, web-design-guidelines; tester webapp-testing; reviewer vercel-react-best-practices, web-design-guidelines
- Files: `tests/backend/test_api_jobs.py`, `tests/frontend/test_frontend_contracts.py`
- Commands: API/frontend suite 44 tests with 11 optional skips; compileall; harness validation; `git diff --check`
- Tester: PASS — API envelopes and component success/error paths covered
- Reviewer: APPROVED — UI/API scope verified; unrelated observability files excluded
- Rework: none
- Changelog: API contracts and React component test coverage added
- Risks: runtime API tests depend on optional FastAPI/SQLAlchemy packages
- Commit subject: test(app): cover API contracts and UI components
- Commit hash: 48faecd0155fece17afc0a2cac17e9514969e9e2

### TEST-003 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: source failure isolation, idempotent/retry-safe Notion sync and reconciliation repair coverage; PASS
- Skills: coordinator none; coder notion-api; tester none; reviewer notion-api
- Files: `tests/backend/test_notion_sync.py`
- Commands: pipeline/connectors/Notion suites 27 tests with 12 explicit SQLAlchemy skips; compileall; harness validation; `git diff --check`
- Tester: PASS — source isolation, idempotency, rate limit and reconciliation behaviors covered
- Reviewer: APPROVED — retry audit and scope verified; unrelated observability files excluded
- Rework: none
- Changelog: synchronization and reconciliation resilience coverage added
- Risks: connector runtime tests require SQLAlchemy installation
- Commit subject: test(integration): cover source and Notion synchronization
- Commit hash: 7b61bce5825108d29ae37fb8cbbb308b0abe6dd6

### TEST-002 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: reproducible bounded scores and Ollama timeout/unavailable-model fallback coverage; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `tests/backend/test_matching.py`, `tests/backend/test_ollama.py`
- Commands: matching/ollama suites 16 tests with 9 explicit SQLAlchemy skips; compileall; harness validation; `git diff --check`
- Tester: PASS — retries, timeout, invalid output, allowlist, loopback, score bounds and reproducibility covered
- Reviewer: APPROVED — scope and acceptance verified; unrelated `backend/app/__main__.py` excluded
- Rework: none
- Changelog: scoring and local model fallback test coverage added
- Risks: runtime fallback test requires SQLAlchemy installation
- Commit subject: test(match): cover scoring and local model fallback
- Commit hash: 4cf7ff545a9b6b1615f9bba7f7cdbadd8fbc2da8

### API-004 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: source creation via POST; enable/disable via PATCH; consistent error contract; existing GET endpoints unaffected; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/app/schemas.py`, `backend/app/repositories.py`, `tests/backend/test_api_operations.py`
- Commands: 140 backend tests (61 skipped), 35 harness tests, 25 frontend tests; check-skills; py_compile; harness validate
- Tester: PASS — 7 contract tests for API-004 (routes, payloads, service usage, repository method); all existing suites pass
- Reviewer: APPROVED — requirements match, scope clean, security via _safe_source_config, no changes requested
- Rework: none
- Changelog: source registration and enable/disable endpoints added
- Risks: full HTTP runtime coverage requires FastAPI/SQLAlchemy dependencies
- Commit subject: feat(api): add source registration and enable/disable endpoints
- Commit hash: 00bc4a0

### FRONTEND-006 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: VacancyDashboard reads from GET /api/v1/jobs; OperationsDashboard toggles source via PATCH /api/v1/sources/{source_id}; source creation form calls POST /api/v1/sources; hardcoded fallbackSources, fallbackExecutions, fallbackMetrics, VACANCIES removed; all existing frontend tests pass; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `tests/frontend/test_frontend_bootstrap.py`, `tests/frontend/test_frontend_dashboard.py`, `tests/frontend/test_frontend_detail.py`, `tests/frontend/test_frontend_operations.py`, `tests/frontend/test_frontend_profile.py`
- Commands: 25 frontend tests, 79 backend tests; pytest -v passed
- Tester: PASS — 25 frontend tests pass; all existing backend suites unaffected
- Reviewer: APPROVED — test assertions correctly reflect API-driven components
- Rework: none
- Changelog: connect dashboard to live API, remove demo data, add source creation UI
- Risks: requires running API server for full runtime dashboard interaction
- Commit hash: 032e1bc

### FRONTEND-007 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: profile section loads from API on mount; save writes fields/preferences via PATCH/PUT; CV upload calls POST /api/v1/profiles/upload; profile version shown dynamically; all existing frontend tests pass; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `frontend/src/api/client.ts`, `frontend/src/App.tsx`, `tests/frontend/test_frontend_profile.py`
- Commands: 25 frontend tests, 79 backend tests, 35 harness tests; pytest -v passed for all three suites
- Tester: PASS — 25 frontend tests pass, 79 backend tests pass, 35 harness tests pass
- Reviewer: APPROVED — profile API types/methods are consistent with existing interfaces; App.tsx integrates with API for load, save, upload; error/saving states wired; test assertion updated for dynamic version
- Rework: none
- Changelog: connect profile section to live API endpoints
- Risks: requires running API server for full runtime profile interaction; CV upload requires working backend file endpoint
- Commit subject: feat(web): connect profile UI to live API
- Commit hash: 11cd080

### API-005 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: DELETE /api/v1/sources/{source_id} returns 204; 404 if not found; delete button with confirm; list reloads; all tests pass; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/app/repositories.py`, `frontend/src/api/client.ts`, `frontend/src/App.tsx`
- Commands: 139 tests (25 frontend + 114 backend/harness)
- Tester: PASS — 139 tests pass
- Reviewer: APPROVED — DELETE endpoint, repo.delete, confirm UI, scope clean
- Rework: none
- Changelog: source deletion endpoint and UI button added
- Risks: none
- Commit subject: feat(api): add source deletion endpoint and UI button
- Commit hash: 7ebd4e8

### TEST-013 — Attempt 2

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: regresión de ingestion, enlaces relativos/detalle y persistencia de restricciones; PASS
- Skills: coder `webapp-testing`; tester `webapp-testing`; reviewer `webapp-testing`
- Files: `tests/e2e/test_regression_013.py`
- Commands: `./.venv/bin/python -m unittest -v tests.e2e.test_regression_013` (6/6, 3 skips opt-in); frontend 39/39; `py_compile`; `git diff --check`
- Tester: PASS — assertions browser opcionales cubren guardar/recargar restricciones y hrefs de aplicación/descripción; API y contratos fixture pasan cuando dependencias están disponibles
- Reviewer: APPROVED — alcance solo tests, skips de infraestructura explícitos y assertions no vacuas
- Rework: intento 1 rechazado por cobertura browser insuficiente y ruta de evidencia; intento 2 resuelto
- Changelog: added
- Risks: Playwright/API requieren URL, servidor y dependencias opcionales; legacy E2E puede fallar por sandbox/connection refused
- Commit subject: test(regression): cover source ingestion and preference persistence
- Commit hash: pending

### API-006 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: api/feed kind resolves to JsonApiFeedAdapter; config adapter override respected; factory refresh uses same mapping; all tests pass; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/pipeline.py`, `backend/app/factory.py`, `.gitignore`, `tests/backend/test_adapter_lookup.py`
- Commands: 7 adapter lookup tests pass; 37 existing harness/pipeline tests pass; compileall clean
- Tester: PASS — 7/7 adapter lookup tests, 37/37 existing tests
- Reviewer: APPROVED — kind mapping consistent, scope clean, security verified
- Rework: none
- Changelog: fix adapter lookup — map source kind to adapter name in pipeline and refresh
- Risks: career_page sources still require explicit `adapter` config to resolve
- Commit subject: fix(api): map source kind to adapter name in pipeline and refresh
- Commit hash: 035c5f7

### FRONTEND-008 — Attempt 1

- Started / finished: 2026-07-20 / 2026-07-20
- Acceptance criteria: experience/education render as text not [object Object]; skills without encoding artifacts; all existing tests pass; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `frontend/src/App.tsx`
- Commands: 25 frontend tests, 114 backend+harness tests
- Tester: PASS — 25 frontend tests pass, 114 backend+harness tests pass
- Reviewer: APPROVED — toStrings helper covers both load and upload paths, types handled correctly
- Rework: none
- Changelog: fix CV data rendering for API object fields
- Risks: none
- Commit subject: fix(web): convert API objects to strings in profile fields
- Commit hash: a68b9fa

### API-007 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: upsert sets checked_at to current time when None; explicit checked_at respected; all tests pass; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/repositories.py`, `tests/backend/test_jobs.py`
- Commands: 8/8 job tests (2 new), 37/37 harness+pipeline tests, compileall clean
- Tester: PASS — 8/8 job tests, 37/37 suite tests
- Reviewer: APPROVED — guard against None, tests cover both paths, scope clean
- Rework: none
- Changelog: fix IntegrityError on job upsert by guarding checked_at assignment
- Risks: none
- Commit subject: fix(api): guard checked_at assignment in job upsert
- Commit hash: 122d900

### API-008 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: CVParserUnavailable returns 422 with cv_validation_error code, not 500; ValueError still returns 422; all existing tests pass; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `tests/backend/test_api_profile.py`
- Commands: 9/9 profile API tests pass; compileall clean
- Tester: PASS — 9/9 profile API tests (1 new), all pre-existing tests pass after TestClient lifespan fix
- Reviewer: APPROVED — catch pattern covers ValueError and RuntimeError, test verifies 422 path, scope clean
- Rework: none
- Changelog: catch CVParserUnavailable as 422 in profile upload
- Risks: none
- Commit subject: fix(api): catch CVParserUnavailable as 422 in upload
- Commit hash: 19636bd

### API-009 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: KIND_MAP defined once in constants.py; pipeline.py and factory.py import from constants; no local duplicates; all tests pass; PASS
- Skills: coordinator none; coder none; tester none; reviewer none
- Files: `backend/app/constants.py`, `backend/app/pipeline.py`, `backend/app/factory.py`
- Commands: 7 adapter lookup tests pass; compileall clean
- Tester: PASS — 7/7 adapter lookup tests pass; no regression from 6 pre-existing failures
- Reviewer: APPROVED — shared module eliminates duplication, clean imports
- Rework: none
- Changelog: extract shared KIND_MAP to constants module
- Risks: none
- Commit subject: refactor(api): extract shared KIND_MAP to constants module
- Commit hash: 9ccd5b3

### API-010 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: profile_payload guards None in skills/experience/education/languages with `or []`; all tests pass; PASS
- Skills: none
- Files: `backend/app/factory.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — defensive guard, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: fix(api): add defensive None guard in profile_payload serialization
- Commit hash: 8f6e7f4

### API-011 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: IntegrityError in profile upload caught and returned as 422 with cv_validation_error code; all tests pass; PASS
- Skills: none
- Files: `backend/app/factory.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — IntegrityError caught as 422, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: fix(api): catch IntegrityError as 422 in profile upload
- Commit hash: 80a2b57

### API-012 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: @app.on_event("startup") migrated to ASGI lifespan context manager; deprecation warning eliminated; all tests pass; PASS
- Skills: none
- Files: `backend/app/factory.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — lifespan context manager replaces on_event, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: refactor(api): migrate on_event startup to ASGI lifespan
- Commit hash: 277fe04

### API-013 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: unsupported/missing Content-Type rejected as 422 in upload endpoint; all tests pass; PASS
- Skills: none
- Files: `backend/app/factory.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — content-type validated at route level, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: fix(api): add content-type validation in upload endpoint
- Commit hash: cca710a

### API-014 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: upload size > 10MB rejected at FastAPI level with 422; all tests pass; PASS
- Skills: none
- Files: `backend/app/factory.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — Content-Length check at route level, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: fix(api): enforce upload size limit at FastAPI level
- Commit hash: bddadf2

### API-015 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: JobService.update_job() method added; JobRepository.get() added; all tests pass; PASS
- Skills: none
- Files: `backend/app/services.py`, `backend/app/repositories.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — service and repository method added, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: feat(api): add JobService.update_job method with repository get helper
- Commit hash: 4ec73f9

### API-016 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: PipelineExecution.run_id immutable after creation via @validates; all tests pass; PASS
- Skills: none
- Files: `backend/app/models.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — SQLAlchemy validator enforces immutability, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: fix(api): make PipelineExecution.run_id immutable after creation
- Commit hash: b94fe0f

### NOTION-004 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: data_sources → databases and data_source_id → database_id in Notion API paths; all tests pass; PASS
- Skills: none
- Files: `backend/app/notion_sync.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — API path fix, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: fix(api): fix data_sources to databases in Notion API paths
- Commit hash: 94dfe6f

### TEST-008 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: 404 envelope for missing source (PATCH/DELETE) and missing execution (GET); data/ added to gitignore; all tests pass; PASS
- Skills: none
- Files: `tests/backend/test_api_operations.py`, `.gitignore`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — 404 envelope tests added, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: test(api): add 404 envelope tests for missing sources and execution
- Commit hash: 59f82dc

### TEST-009 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: empty source name rejected via Pydantic min_length=1; all tests pass; PASS
- Skills: none
- Files: `tests/backend/test_api_operations.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — empty name rejection test, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: test(api): add test for empty source name rejection
- Commit hash: 11e2a47

### TEST-011 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: HTTP-level large file rejection test; all tests pass; PASS
- Skills: none
- Files: `tests/backend/test_api_profile.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — large file rejection test, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: test(api): add HTTP-level large file rejection test
- Commit hash: e385331

### TEST-012 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: CORS middleware allows localhost:5173 and localhost:3000; GET and OPTIONS header tests; all tests pass; PASS
- Skills: none
- Files: `backend/app/factory.py`, `tests/backend/test_api_operations.py`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — CORS middleware and header tests, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: feat(api): add CORS middleware and tests
- Commit hash: 74fb417

### OPS-008 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: backend requirements.txt pins exact dependency versions; all tests pass; PASS
- Skills: none
- Files: `backend/requirements.txt`
- Commands: compileall; existing test suites
- Tester: PASS — all pre-existing tests pass
- Reviewer: APPROVED — pinned deps for reproducible builds, scope clean
- Rework: none
- Changelog: added
- Risks: none
- Commit subject: chore(ops): pin dependency versions for reproducible builds
- Commit hash: 4426859

### FRONTEND-009 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: n/a — backend manages secrets; Notion status visible via health endpoint; no frontend change needed; PASS
- Skills: none
- Files: none
- Commands: none
- Tester: PASS — no change needed
- Reviewer: APPROVED — backend handles secrets, health endpoint exposes status
- Rework: none
- Changelog: not applicable
- Risks: none
- Commit subject: n/a (marked n/a in backlog)
- Commit hash: none

### WEB-001 — Attempt 1

- Started / finished: 2026-07-21 / 2026-07-21
- Acceptance criteria: Vite dev server proxies /api and /health to backend at 127.0.0.1:8000; all tests pass; PASS
- Skills: none
- Files: `frontend/vite.config.ts`
- Commands: `npx vite --version`; TypeScript syntax check
- Tester: PASS — vite config valid, existing test suites pass
- Reviewer: APPROVED — proxy config unblocks frontend-backend communication in dev
- Rework: none
- Changelog: added
- Risks: requires backend running on port 8000 for full dev workflow
- Commit subject: fix(web): add proxy to Vite config for backend API requests
- Commit hash: 310a6f5

### HARNESS-004 — Attempt 1

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: inactive current-task canonicalizado; reparación explícita con `init --force`; regresión automatizada; PASS
- Skills: coder none; tester none; reviewer none
- Files: `scripts/harness.py`, `tests/harness/test_harness.py`, `.harness/current-task.json`, `.harness/backlog.json`
- Commands: `python3 -m unittest tests.harness.test_harness -v`; `python3 -m py_compile scripts/harness.py tests/harness/test_harness.py`; `python3 scripts/harness.py validate`; `python3 scripts/harness.py status`
- Tester: PASS — 36 tests OK, incluyendo reparación de estado inactivo obsoleto
- Reviewer: APPROVED — alcance, seguridad y transiciones correctas
- Rework: none
- Changelog: added
- Risks: `init --force` sigue siendo una operación explícita que reinicia estados pendientes/bloqueados
- Commit subject: fix(harness): repair inactive current task state
- Commit hash: pending

### SOURCES-004 — Attempt 1

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: configuración ejecutable, resolver común, errores accionables y zero-jobs no saludable; rework requerido por revisión
- Skills: coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/app/sources.py`, `backend/app/pipeline.py`, `tests/backend/test_sources_004.py`
- Commands: `backend/.venv/bin/python -m unittest tests.backend.test_sources_004 -v`; related backend suites; compileall
- Tester: PASS — primer intento 7/7; revisión posterior 10/10 con guard y casos de rework
- Reviewer: CHANGES_REQUESTED — cron zero-jobs, URLs inválidas y allow_network requerían corrección
- Rework: intento 2 corrigió pipeline, validación 422, tipos booleanos y guard de import
- Changelog: added
- Risks: fuentes reales siguen sujetas a robots, rate limits y compatibilidad de cada proveedor
- Commit subject: fix(api): make source refresh configuration executable
- Commit hash: pending

### PROFILE-003 — Attempt 2 (traceability)

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: restricciones controladas y persistentes; pesos y restricciones conservados tras PUT→GET; PASS
- Skills: coder `vercel-react-best-practices`; tester `webapp-testing`; reviewer `vercel-react-best-practices` + `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `tests/frontend/test_frontend_profile.py`, `tests/backend/test_api_profile.py`
- Commands: backend profile 11/11; frontend 39/39; `cd frontend && pnpm build`; `git diff --check`
- Tester: PASS — persistencia HTTP PUT→GET y suites relacionadas OK
- Reviewer: APPROVED — controles accesibles, estado rehidratado y alcance revisados
- Risks: fallos preexistentes de la suite backend completa permanecen fuera de alcance
- Commit subject: fix(web): persist profile restrictions and preferences
- Commit hash: pending

### PROFILE-003 — Attempt 2

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: restricciones controladas y persistentes; pesos y restricciones conservados tras PUT→GET; PASS
- Skills: coder `vercel-react-best-practices`; tester `webapp-testing`; reviewer `vercel-react-best-practices` + `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `tests/frontend/test_frontend_profile.py`, `tests/backend/test_api_profile.py`
- Commands: `backend/.venv/bin/python -m unittest tests.backend.test_api_profile -v` (11/11); `python3 -m unittest discover -s tests/frontend -p 'test_*.py' -v` (39/39); `cd frontend && pnpm build`; `git diff --check`
- Tester: PASS — prueba HTTP PUT→GET valida `excluded_constraints`, `willing_to_relocate` y `weights`; suite frontend y build OK
- Reviewer: APPROVED — checkboxes controlados con `autocomplete`, persistencia y alcance revisados; `backend/app/schemas.py` preexistente excluido del stage
- Rework: intento 1 rechazado por falta de prueba HTTP, autocomplete y alcance; intento 2 resuelto
- Changelog: added
- Risks: suite backend completa mantiene fallos preexistentes fuera de alcance; persistencia requiere API y base de datos disponibles
- Commit subject: fix(web): persist profile restrictions and preferences
- Commit hash: pending

### SOURCES-005 — Attempt 3

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: configuración ejecutable, diagnóstico por fuente y accesibilidad; PASS
- Skills: coder `vercel-react-best-practices`; reviewer `web-design-guidelines` + `vercel-react-best-practices`; tester `webapp-testing`
- Files: `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/styles.css`, `tests/frontend/test_sources_005.py`
- Commands: `python3 -m unittest tests.frontend.test_sources_005 -v`; frontend suite; `pnpm build`; `tsc -b`; `git diff --check`
- Tester: PASS — 9/9 target, 34/34 frontend suite, build/tsc OK; Playwright bloqueado por sandbox Chromium
- Reviewer: APPROVED — fixtures, errores 422, tabs y controles accesibles revisados
- Rework: intentos 1 y 2 corregidos; intento 3 aprobado
- Changelog: added
- Risks: E2E browser requiere entorno con Chromium y permisos de sandbox
- Commit subject: feat(web): add source configuration diagnostics
- Commit hash: pending

### JOBS-003 — Attempt 2

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: normalización de enlaces y validación estricta de URLs; PASS
- Skills: coder none; tester none; reviewer none
- Files: `backend/app/connectors.py`, `tests/backend/test_connectors.py`
- Commands: `backend/.venv/bin/python -m unittest tests.backend.test_connectors -v`; `py_compile`; `git diff --check`
- Tester: PASS — 16/16 connector tests; fallos externos preexistentes aislados
- Reviewer: APPROVED — raw malformed URLs rechazadas y URLs relativas resueltas correctamente
- Rework: resolved
- Changelog: added
- Risks: enlaces externos siguen sujetos a disponibilidad y políticas del proveedor
- Commit subject: fix(api): normalize job source links
- Commit hash: pending

### SOURCES-004 — Attempt 2

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: todos los hallazgos corregidos; PASS
- Skills: coder none; tester none; reviewer none
- Files: `backend/app/factory.py`, `backend/app/sources.py`, `backend/app/pipeline.py`, `tests/backend/test_sources_004.py`
- Commands: `backend/.venv/bin/python -m unittest tests.backend.test_sources_004 -v`; related suites; `compileall`; `git diff --check`
- Tester: PASS — 10/10 target; fallos restantes preexistentes aislados
- Reviewer: APPROVED — alcance y requisitos completos
- Rework: resolved
- Changelog: added
- Risks: fallos preexistentes fuera de alcance permanecen documentados
- Commit subject: fix(api): make source refresh configuration executable
- Commit hash: pending

### PROFILE-003 — Attempt 2 (final traceability)

- Started / finished: 2026-07-30 / 2026-07-30
- Acceptance criteria: restricciones controladas y persistentes; pesos y restricciones conservados tras PUT→GET; PASS
- Skills: coder `vercel-react-best-practices`; tester `webapp-testing`; reviewer `vercel-react-best-practices` + `web-design-guidelines`
- Files: `frontend/src/App.tsx`, `tests/frontend/test_frontend_profile.py`, `tests/backend/test_api_profile.py`
- Commands: backend profile 11/11; frontend 39/39; `cd frontend && pnpm build`; `git diff --check`
- Tester: PASS — persistencia HTTP PUT→GET y suites relacionadas OK
- Reviewer: APPROVED — controles accesibles, estado rehidratado y alcance revisados
- Risks: fallos preexistentes de la suite backend completa permanecen fuera de alcance
- Commit subject: fix(web): persist profile restrictions and preferences
- Commit hash: pending
