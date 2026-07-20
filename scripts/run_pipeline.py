#!/usr/bin/env python3
"""Run the complete JobScrapper pipeline once.

Example: ``python scripts/run_pipeline.py --profile-id 1``.
All source fixtures remain controlled by their persisted source configuration;
network fetching is never enabled by this command implicitly.
"""
from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest, score, analyze, and sync jobs")
    parser.add_argument("--profile-id", type=int, help="profile to evaluate (defaults to the first profile)")
    parser.add_argument("--no-notion", action="store_true", help="skip Notion synchronization")
    parser.add_argument("--no-ollama", action="store_true", help="skip local model narrative analysis")
    parser.add_argument("--max-jobs", type=int, default=100)
    args = parser.parse_args(argv)
    # Keep lock contention observable even when optional backend dependencies
    # are not installed: heavy imports happen only after lock acquisition.
    from app.process_lock import ProcessLock
    lock = ProcessLock()
    if not lock.acquire(blocking=False):
        print(json.dumps({"status": "skipped", "reason": "pipeline_in_progress", "lock_file": str(lock.path)}))
        return 75
    try:
        from app.config import Settings
        from app.database import create_db_engine, create_session_factory
        from app.models import Base, Profile
        from app.notion import NotionConfig
        from app.notion_sync import NotionHttpClient, NotionSyncService
        from app.ollama import OllamaAnalyzer
        from app.pipeline import JobPipeline
        from app.repositories import ProfileRepository
        from sqlalchemy import select
        settings = Settings.from_env()
        from app.observability import configure_logging
        configure_logging(level=settings.log_level, path=settings.log_file,
                          max_bytes=settings.log_max_bytes, backup_count=settings.log_backup_count)
        engine = create_db_engine(settings)
        Base.metadata.create_all(engine)
        sessions = create_session_factory(engine)
        with sessions() as db:
            profile = ProfileRepository(db).get(args.profile_id) if args.profile_id else db.scalar(select(Profile).order_by(Profile.id))
            if profile is None:
                print(json.dumps({"status": "failed", "error": "no profile available"}))
                return 2
            analyzer = None if args.no_ollama else OllamaAnalyzer(base_url=settings.ollama_base_url, model=settings.ollama_model,
                                                               timeout_seconds=settings.ollama_timeout_seconds, num_ctx=settings.ollama_num_ctx,
                                                               num_thread=settings.ollama_num_thread)
            notion = None
            if not args.no_notion:
                notion = NotionSyncService(NotionHttpClient(NotionConfig.from_settings(settings)))
            report = JobPipeline(db, notion=notion, analyzer=analyzer, max_jobs=args.max_jobs,
                                 max_concurrency=settings.max_concurrency).run(profile)
            print(json.dumps(report.as_dict(), ensure_ascii=False, default=str))
            return 0 if report.status in {"success", "partial"} else 1
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
