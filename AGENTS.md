# JobScrapper agent protocol

The coordinator owns task state, logs, staging, and commits. Exactly one backlog task may be active.

Required flow: `coder -> tester -> reviewer -> coordinator -> commit`. A failed test or requested change returns the task to `coder`, increments the attempt, and repeats every gate.

## Shared rules

- Work on one task and its acceptance criteria only.
- Never expose secrets, bypass access controls, or silently expand scope.
- Use only skills authorized in `.harness/skills.json` for the current role.
- Do not claim a gate passed without command output or a review report as evidence.
- Preserve unrelated user changes and report any overlap to the coordinator.
- Follow Conventional Commits configured in `.harness/config.json`.

## Ownership

- Coder: production code, configuration, and requested documentation; no tests or commits.
- Tester: tests, fixtures, and test utilities; no production fixes or commits.
- Reviewer: read-only inspection; returns `APPROVED` or `CHANGES_REQUESTED`.
- Coordinator: state transitions, development log, changelog, staging, commit, and dispatch.

See `.agents/` for role-specific contracts. Repository-level instructions apply to all agents and nested agents.
