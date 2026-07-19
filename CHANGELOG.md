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
