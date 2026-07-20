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
- `docs/RELEASE.md`: version 0.1.0 release gate and operational checklist.
- `docs/DEVELOPMENT_LOG.md`: coordinator-owned incremental task history.
- `AGENTS.md`: mandatory multi-agent protocol.

## Start the backend

The initial FastAPI service can be installed and run locally with the commands
below (see `backend/README.md` for environment options):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e backend
cd backend && python -m app
```

Check liveness at `http://127.0.0.1:8000/health`.

The SDD defines the user story, functional and non-functional requirements, runtime
flow, API/data contracts, security boundaries, Notion mapping, and the readable
backlog phase index. Operational procedures for cron, backup/restore, and recovery
are delivered by the corresponding `OPS-*` tasks and must be reflected here before
the `RELEASE-001` gate.

For the Compose deployment, use `scripts/ops.sh` for restart, backup/restore,
update, rollback, recovery, and reproducible health checks. The complete runbook
is [docs/OPERATIONS.md](docs/OPERATIONS.md); it documents explicit confirmation
and clean-working-tree guards for state-changing operations.

## Container startup

Docker Compose runs the API on `http://localhost:8000` and the dashboard on
`http://localhost:5173`. The SQLite database is stored in the named
`jobscrapper_data` volume, so recreating containers does not remove job data.

```sh
cp .env.example .env
docker compose up --build
```

To run Ollama in a Compose-managed container (and persist its models), enable
the local profile and pull the configured model once:

```sh
docker compose --profile local-ollama up --build -d
docker compose exec ollama ollama pull "${OLLAMA_MODEL:-llama3.2:3b}"
```

For a host-managed or remote Ollama instance, leave the profile disabled and set
`OLLAMA_BASE_URL` in `.env` to a URL reachable from the backend container (for a
host service on Docker Desktop, use `http://host.docker.internal:11434`). The
backend never requires Ollama for its liveness endpoint; model availability is
reported by the operations health endpoint. Set `NOTION_API_TOKEN` and
`NOTION_DATABASE_ID` only when Notion synchronization is enabled.

Stop services with `docker compose down`; named volumes remain intact. Remove
them explicitly only when intentionally deleting local state:
`docker compose down --volumes`.
