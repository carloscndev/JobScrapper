# JobScrapper agent protocol

The coordinator owns task state, logs, staging, and commits. Exactly one backlog task may be active.

Required flow: `pending -> coding -> testing -> review -> approved -> committed`. The operational handoff is `coder -> tester -> reviewer -> coordinator -> commit`. A failed test or requested change returns the task to `rework`, increments the attempt, and sends it back to `coder`; every gate is repeated before approval. Only one task may be active at a time.

## Shared rules

- Work on one task and its acceptance criteria only.
- Never expose secrets, bypass access controls, or silently expand scope.
- Use only skills authorized in `.harness/skills.json` for the current role.
- Do not claim a gate passed without command output or a review report as evidence.
- Preserve unrelated user changes and report any overlap to the coordinator.
- Follow Conventional Commits configured in `.harness/config.json`.
- Use only the skills listed in `.harness/skills.json` and allowlisted for the current role; a skill outside that allowlist requires coordinator approval and a log entry.
- Provide command output, test evidence, or a review report for every gate; assertions without evidence do not advance state.

## Ownership

- Coder: production code, configuration, and requested documentation; no tests or commits.
- Tester: tests, fixtures, and test utilities; no production fixes, state transitions, or commits.
- Reviewer: read-only inspection; returns exactly `APPROVED` or `CHANGES_REQUESTED` followed by actionable findings; no file edits or commits.
- Coordinator: state transitions, development log, changelog, staging, commit, and dispatch. The coordinator alone may approve a state transition or create a commit, after verifying coder, tester, and reviewer evidence.

## Failure and commit protocol

- A tester failure or reviewer `CHANGES_REQUESTED` result records the evidence, moves the task to `rework`, and increments `attempt` before returning to the coder.
- The coder addresses all findings, then hands off to the tester; the tester reruns new and related checks; the reviewer rechecks the complete diff.
- `commit-ready` is valid only after successful tests, reviewer `APPROVED`, a clean scope check, and updated logs. The coordinator stages only allowed paths and creates the configured Conventional Commit.
- A task is not complete, and the next task cannot start, until its commit hash is recorded as `committed`.

See `.agents/` for role-specific contracts. Repository-level instructions apply to all agents and nested agents.
