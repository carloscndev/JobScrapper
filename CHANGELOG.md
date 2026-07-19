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
- Commit hash: pending
