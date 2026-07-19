# JobScrapper

Local, explainable job discovery for Mexico and the United States, with local-model analysis and idempotent Notion synchronization.

The repository currently contains the delivery harness and SDD. Product implementation starts only after the harness passes coder, tester, reviewer, and coordinator gates.

## Current delivery state

The canonical backlog contains 46 ordered tasks. The harness permits exactly one
active task and requires the complete `coder -> tester -> reviewer -> coordinator ->
commit` lifecycle before its dependent tasks unlock. Start with the task reported by
`status`; do not edit `.harness/current-task.json` manually.

## Repository layout

- `backend/`: FastAPI service, domain logic, persistence, and workers.
- `frontend/`: React/TypeScript dashboard.
- `docs/`: SDD, skills policy, and coordinator-owned development history.
- `scripts/`: harness and operational utilities.
- `tests/`: harness, unit, integration, and end-to-end tests.

Each subsystem README records its ownership boundaries. New tasks should keep
production code in `backend/` or `frontend/`, tests in `tests/`, and orchestration
in `scripts/`.

## Harness quick start

```sh
python3 scripts/harness.py validate
python3 scripts/harness.py status
python3 scripts/harness.py start TASK-ID
python3 scripts/harness.py record coder --result pass --evidence "files and verification"
python3 scripts/harness.py handoff tester
python3 scripts/harness.py record tester --result pass --evidence "test command output"
python3 scripts/harness.py handoff reviewer
python3 scripts/harness.py record reviewer --result pass --evidence "APPROVED: findings"
python3 scripts/harness.py approve
python3 scripts/harness.py commit-ready
```

`commit-ready` runs configured skill, unit-test, syntax, JSON, staging, secret-scan, per-task path-scope, and documentation gates. It checks deletions plus both sides of renames. Both traceability documents are read from Git's staged index—not the working tree—and must contain a complete section for the active task and attempt, so unstaged or stale approvals cannot satisfy a new cycle. After the coordinator creates the printed commit, record its hash with `python3 scripts/harness.py complete --commit HASH`; it must resolve to the current Git `HEAD`.

The state machine validates the complete ordered lifecycle (`coding` → `testing` → `review` → `approved` → `committed`), rejects dependency cycles and unknown dependencies, permits only one active task, and verifies that the recorded commit is the current `HEAD` with the task's configured Conventional Commit subject.

## Skills

Use `scripts/check-skills.sh` for read-only verification. `scripts/install-skills.sh` performs approved global installs and requires explicit network/filesystem authorization. See `docs/SKILLS.md`, including the high-risk warning for `notion-api`.

## Documentation

- `docs/SDD.md`: product story, requirements, and delivery sequence.
- `docs/DEVELOPMENT_LOG.md`: coordinator-owned incremental task history.
- `AGENTS.md`: mandatory multi-agent protocol.

The SDD defines the user story, functional and non-functional requirements, runtime
flow, API/data contracts, security boundaries, Notion mapping, and the readable
backlog phase index. Operational procedures for cron, backup/restore, and recovery
are delivered by the corresponding `OPS-*` tasks and must be reflected here before
the `RELEASE-001` gate.
