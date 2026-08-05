# Release 0.1.0 checklist

This list is the release gate for the first local version. The coordinator must
retain evidence from every command in `docs/DEVELOPMENT_LOG.md` and must not
publish a version with tasks that are not `committed`.

## Preparation

- [ ] `python3 scripts/harness.py validate` passes with no active tasks or invalid states.
- [ ] `python3 scripts/check-skills.sh` confirms installed skills and checksums.
- [ ] `git diff --check` and the secret scan report no findings.
- [ ] `.env` is not versioned; copy `.env.example` and configure secrets locally only.

## Quality

- [ ] The backend, static frontend, and harness suites pass; optional skips are documented.
- [ ] `python3 -m compileall backend scripts tests` passes.
- [ ] `npm run build` passes when frontend dependencies are installed; otherwise,
      record the network/dependency blocker without hiding it.
- [ ] The Playwright E2E runs with `JOBSCRAPPER_E2E_COMMAND` in an environment
      with a browser and retains browser/server logs.

## Operations and recovery

- [ ] `scripts/ops.sh check` passes with Compose running.
- [ ] A backup is tested and validated with `tar tzf`; restore requires `--yes`
      and a prior backup of the current state.
- [ ] Cron points to `scripts/scheduler.py`, uses the shared lock, and leaves logs.
- [ ] Seven daily runs are simulated: a transient failure recovers, runs do not
      overlap, and CPU, memory, concurrency, retry, and log-retention limits are recorded.
- [ ] Ollama and Notion can be unavailable without losing deterministic scores or
      previously persisted results; Notion repairs are auditable.

## Publishing

- [ ] The SDD and backlog reflect the implemented behavior and its risks.
- [ ] `CHANGELOG.md` contains `[0.1.0]` and the release Conventional Commit hash.
- [ ] Create the annotated `v0.1.0` tag only after recording the final commit.
- [ ] Save the completed checklist with the release artifact.

Checks that require Docker, npm, Playwright, SQLAlchemy, or real credentials are
explicitly environment-dependent; they are never replaced with an unsupported
claim.
