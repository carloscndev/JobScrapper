# Operations, maintenance, and recovery

These instructions apply to the JobScrapper Docker Compose installation. The
commands are deliberately explicit: volumes are never deleted and a backup is
never restored without `--yes`. Before making any change, keep the `.env` file
outside Git and validate the repository state.

## Restart after reboot

From the checkout, run:

```sh
scripts/ops.sh restart
```

The command recreates the services in the background and checks `/health`. For
automatic startup on Linux, enable a systemd service that runs
`docker compose up -d` after `docker.service`; on macOS/Windows, start Docker
Desktop and use the same command. The daily scheduler is installed separately
with `scripts/jobscrapper.cron.example` and must not run until `check` passes.

## Backup and restore

`scripts/ops.sh backup [directory]` creates a timestamped copy of the `/app/data`
tree (SQLite, WAL, logs, and resumes) and, when present, a second archive for the
persistent Ollama volume. Copy the artifacts to external storage and periodically
verify that they can be listed with `tar tzf`.

To restore, stop the services and require explicit confirmation:

```sh
scripts/ops.sh restore backups/jobscrapper-data-YYYYMMDDTHHMMSSZ.tar.gz --yes
scripts/ops.sh check
```

The restore replaces only the contents of the data volume. Back up the current
state before restoring and retain the original copy; never use
`docker compose down --volumes` as a recovery step.

If you also need to recover local models, stop Compose and restore the Ollama
archive into its volume (after inspecting its contents):

```sh
docker run --rm -i -v "${OLLAMA_DATA_VOLUME:-jobscrapper_ollama}:/target" \
  alpine:3.20 sh -c 'tar xzf - -C /target' < backups/jobscrapper-ollama-YYYYMMDDTHHMMSSZ.tar.gz
```

The Ollama backup is optional; if it does not exist, the backend continues to
work without the model and leaves narrative analysis in the pending state.

## Update and rollback

With a clean working tree:

```sh
scripts/ops.sh update
scripts/ops.sh rollback <known-good-tag-or-commit> --yes
```

`update` uses `git pull --ff-only`, rebuilds images, and verifies health. The
rollback switches the checkout to a known commit, rebuilds, and verifies again.
Record the ref used, resulting hash, and `check` result in the operations log
before re-enabling cron.

## Failures and diagnostics

When a container is unhealthy:

```sh
scripts/ops.sh recover
docker compose logs --since=30m --tail=200
docker compose ps
```

`recover` attempts to recreate services without deleting data and fails if
`/health` remains unresponsive. If there are schema errors, restore a backup and
review the latest migration; if Ollama fails, leave the `local-ollama` profile
disabled: deterministic scoring and the `narrative_pending` queue remain usable.

## Reproducible checks

Run `scripts/ops.sh check` after reboot, restore, update, and rollback. The check
validates the Compose file and queries the local endpoint with a five-second
timeout. Save the output with the backup for auditing. It contains no tokens and
does not print secret values.
