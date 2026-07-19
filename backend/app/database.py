"""SQLAlchemy engine and session lifecycle for the local operational database."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings


def create_db_engine(settings: Settings | None = None, *, database_url: str | None = None) -> Engine:
    """Create an engine from settings, with SQLite-safe connection options."""

    runtime = settings or Settings.from_env()
    url = database_url or runtime.database_url
    connect_args: dict[str, Any] = {}
    if url.startswith("sqlite"):
        # The API and scheduler can use the same SQLite database from separate
        # threads. SQLite still serializes writes, so callers should keep
        # transactions short.
        connect_args["check_same_thread"] = False
    return create_engine(url, echo=runtime.database_echo, pool_pre_ping=True, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a reusable session factory bound to ``engine``."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield a session and commit/rollback/close it deterministically."""

    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
