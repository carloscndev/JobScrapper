# Scripts

Repository and operations scripts live here, including the task harness,
skill checks, local scheduler helpers, and development commands.

Scripts must be deterministic, avoid secrets, and document any required
environment variables.

## Daily scheduler and locking

Run `python3 scripts/scheduler.py` for one scheduled refresh. It delegates to
`run_pipeline.py`, so API manual refreshes and scheduled/manual workers share
the same advisory lock (`JOBSCRAPPER_LOCK_FILE`, default
`data/jobscrapper.pipeline.lock`). Concurrent scheduled execution exits with
status `75` and emits a JSON `pipeline_in_progress` record. Successful runs
remain auditable through `PipelineExecution`; install the daily cron example
from `scripts/jobscrapper.cron.example` after editing its absolute path.
