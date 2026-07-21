"""Single-command ingestion, matching, local analysis, and Notion sync.

The pipeline is deliberately defensive: every source, job, evaluation, and
Notion page is isolated.  A failure is recorded in the report while work that
already succeeded is committed and retained for the next run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4
from time import monotonic
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .connectors import DEFAULT_ADAPTERS
from .jobs import canonicalize_url, fingerprint_job
from .matching import MatchingService
from .models import Job, PipelineExecution, Profile, Source, SourceRun
from .notion_sync import NotionSyncService, SyncOutcome
from .repositories import EvaluationRepository, JobRepository, ProfileRepository
from .sources import SourceAdapter, SourceConfig, SourceKind


@dataclass(frozen=True)
class PipelineIssue:
    stage: str
    message: str
    source: str | None = None
    job: str | None = None


@dataclass
class PipelineReport:
    run_id: str
    status: str
    jobs_ingested: int = 0
    evaluations_created: int = 0
    notion_synced: int = 0
    notion_failed: int = 0
    source_runs: list[dict[str, Any]] = field(default_factory=list)
    issues: list[PipelineIssue] = field(default_factory=list)
    execution_id: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id, "execution_id": self.execution_id,
            "status": self.status,
            "metrics": {"jobs_ingested": self.jobs_ingested, "evaluations_created": self.evaluations_created,
                         "notion_synced": self.notion_synced, "notion_failed": self.notion_failed},
            "source_runs": self.source_runs,
            "issues": [issue.__dict__ for issue in self.issues],
        }


class JobPipeline:
    """Orchestrate one bounded run against a SQLAlchemy session."""

    def __init__(self, session: Session, *, adapters: Sequence[SourceAdapter] = DEFAULT_ADAPTERS,
                 notion: NotionSyncService | None = None, analyzer: Any | None = None,
                 max_jobs: int = 100, max_concurrency: int = 1) -> None:
        if max_jobs < 1:
            raise ValueError("max_jobs must be greater than zero")
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be greater than zero")
        self.session, self.notion, self.analyzer = session, notion, analyzer
        self.max_jobs, self.max_concurrency = max_jobs, max_concurrency
        self.adapters = {adapter.name: adapter for adapter in adapters}

    _KIND_MAP = {"api": "json-api-feed", "feed": "json-api-feed"}

    def _adapter(self, source: Source, config: Mapping[str, Any]) -> SourceAdapter | None:
        name = str(config.get("adapter") or source.name)
        adapter = self.adapters.get(name)
        if adapter:
            return adapter
        mapped = self._KIND_MAP.get(source.kind)
        if mapped:
            return self.adapters.get(mapped)
        return self.adapters.get(source.kind)

    @staticmethod
    def _config(source: Source) -> SourceConfig:
        values = source.config or {}
        return SourceConfig(name=source.name, kind=SourceKind(source.kind), base_url=source.base_url,
                            terms_url=source.terms_url, terms_accepted=bool(values.get("terms_accepted")),
                            timeout_seconds=float(values.get("timeout_seconds", 20)),
                            requests_per_minute=int(values.get("requests_per_minute", 30)),
                            max_retries=int(values.get("max_retries", 2)), settings=values)

    def run(self, profile: Profile, sources: Sequence[Source] | None = None) -> PipelineReport:
        started_clock = monotonic()
        run_id = str(uuid4())
        logger = logging.getLogger("jobscrapper.pipeline")
        logger.info("pipeline_started", extra={"event": "pipeline_started", "run_id": run_id})
        report = PipelineReport(run_id, "running")
        execution = PipelineExecution(run_id=run_id, status="running", started_at=datetime.now(timezone.utc), metrics={})
        self.session.add(execution); self.session.flush(); report.execution_id = execution.id
        discovered: list[Job] = []
        source_items = list(sources if sources is not None else self.session.scalars(select(Source).where(Source.enabled.is_(True)).order_by(Source.name)).all())
        for source in source_items:
            values = source.config or {}
            adapter = self._adapter(source, values)
            started = datetime.now(timezone.utc)
            source_error: str | None = None
            if adapter is None:
                message = "No adapter configured"
                source_error = message
                report.issues.append(PipelineIssue("ingest", message, source.name))
                result = None
            else:
                try:
                    result = adapter.fetch(self._config(source))
                except Exception as exc:  # adapter isolation
                    result = None
                    message = f"{type(exc).__name__}: {exc}"
                    source_error = message
                    report.issues.append(PipelineIssue("ingest", message, source.name))
            if result is not None:
                if result.error:
                    report.issues.append(PipelineIssue("ingest", result.error, source.name))
                for normalized in list(result.jobs)[: self.max_jobs]:
                    try:
                        job = Job(source_id=source.id, title=normalized.title, company=normalized.company,
                                  description=normalized.description, description_url=normalized.description_url,
                                  application_url=normalized.application_url,
                                  canonical_url=canonicalize_url(normalized.effective_canonical_url),
                                  fingerprint=fingerprint_job(normalized), location=normalized.location,
                                  region=normalized.region, modality=str(normalized.modality),
                                  salary_min=normalized.salary_min, salary_max=normalized.salary_max,
                                  salary_currency=normalized.salary_currency, published_at=normalized.published_at,
                                  metadata_json={**dict(normalized.metadata), "source": source.name,
                                                 "requirements": list(normalized.requirements),
                                                 "salary_period": normalized.salary_period})
                        discovered.append(JobRepository(self.session).upsert(job)); report.jobs_ingested += 1
                    except Exception as exc:
                        report.issues.append(PipelineIssue("normalize", f"{type(exc).__name__}: {exc}", source.name, normalized.title))
            run_status = result.status if result is not None else "failed"
            source_run = SourceRun(execution_id=execution.id, source_id=source.id, status=run_status,
                                   jobs_found=len(result.jobs) if result is not None else 0,
                                   error=result.error if result is not None else source_error,
                                   started_at=started, finished_at=datetime.now(timezone.utc))
            self.session.add(source_run)
            report.source_runs.append({"source": source.name, "status": run_status, "jobs_found": source_run.jobs_found, "error": source_run.error})
            self.session.commit()

        # Evaluate each retained job independently.  The deterministic score is
        # persisted even if Ollama is unavailable (MatchingService fallback).
        matcher = MatchingService(EvaluationRepository(self.session), ProfileRepository(self.session))
        evaluations: list[tuple[Job, Any]] = []
        preferences = ProfileRepository(self.session).current_preferences(profile.id)
        for job in discovered:
            try:
                evaluation = matcher.evaluate(profile, job, preferences, analyzer=self.analyzer)
                evaluations.append((job, evaluation)); report.evaluations_created += 1
                # Persist each successful evaluation immediately so a later
                # malformed job or repository error cannot erase prior work.
                self.session.commit()
            except Exception as exc:
                self.session.rollback()
                report.issues.append(PipelineIssue("score", f"{type(exc).__name__}: {exc}", job=job.title))
        self.session.commit()

        if self.notion is not None:
            try:
                outcomes: list[SyncOutcome] = self.notion.sync_jobs(evaluations)
                report.notion_synced = sum(item.state == "synced" for item in outcomes)
                report.notion_failed = sum(item.state != "synced" for item in outcomes)
                for item in outcomes:
                    if item.state != "synced":
                        report.issues.append(PipelineIssue("notion", item.error or "sync failed", job=item.external_id))
            except Exception as exc:
                # A misconfigured transport must not roll back ingestion or
                # evaluations that were already committed.
                report.notion_failed = len(evaluations)
                report.issues.append(PipelineIssue("notion", f"{type(exc).__name__}: {exc}"))

        successful = report.jobs_ingested or report.evaluations_created or report.notion_synced
        report.status = "failed" if report.issues and not successful else ("partial" if report.issues else "success")
        execution.status = report.status
        execution.finished_at = datetime.now(timezone.utc)
        metrics = report.as_dict()["metrics"]
        metrics.update({"duration_seconds": round(monotonic() - started_clock, 3),
                        "sources_total": len(source_items), "issues_total": len(report.issues),
                        "max_concurrency": self.max_concurrency})
        execution.metrics = metrics
        execution.error = "; ".join(issue.message for issue in report.issues)[:2000] or None
        self.session.commit()
        logger.info("pipeline_finished", extra={"event": "pipeline_finished", "run_id": run_id,
                                                 "execution_id": execution.id})
        return report
