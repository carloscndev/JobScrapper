"""Tests for the DATA-001 database and migration foundation.

The repository's lightweight harness does not install backend dependencies by
default.  Static contracts therefore run everywhere, while SQLAlchemy import
and lifecycle tests skip explicitly when the optional dependency is absent.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def _sqlalchemy_available() -> bool:
    return importlib.util.find_spec("sqlalchemy") is not None


def _import_database():
    """Import ``app.database`` after making the backend package discoverable."""

    backend_path = str(BACKEND)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    return __import__("app.database", fromlist=["*"])


class DatabaseFoundationTests(unittest.TestCase):
    def test_settings_expose_configurable_database_url(self) -> None:
        path = BACKEND / "app" / "config.py"
        spec = importlib.util.spec_from_file_location("jobscrapper_database_config_test", path)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        with mock.patch.dict(os.environ, {"DATABASE_URL": "sqlite:///./tmp/test.db"}, clear=False):
            settings = module.Settings.from_env()
        self.assertEqual(settings.database_url, "sqlite:///./tmp/test.db")

    def test_database_module_import_contract(self) -> None:
        if not _sqlalchemy_available():
            self.skipTest("SQLAlchemy is not installed; database import contract requires the backend dependency")

        database = _import_database()
        self.assertTrue(callable(database.create_db_engine))
        self.assertTrue(callable(database.create_session_factory))
        self.assertTrue(callable(database.session_scope))

    def test_sqlite_engine_and_session_scope_commit_and_rollback(self) -> None:
        if not _sqlalchemy_available():
            self.skipTest("SQLAlchemy is not installed; engine/session lifecycle requires the backend dependency")

        from sqlalchemy import text

        database = _import_database()
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "jobs.db"
            engine = database.create_db_engine(database_url=f"sqlite:///{database_path}")
            factory = database.create_session_factory(engine)

            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"))

            with database.session_scope(factory) as session:
                session.execute(text("INSERT INTO records (value) VALUES ('committed')"))

            with self.assertRaisesRegex(RuntimeError, "rollback sentinel"):
                with database.session_scope(factory) as session:
                    session.execute(text("INSERT INTO records (value) VALUES ('rolled back')"))
                    raise RuntimeError("rollback sentinel")

            with factory() as session:
                values = [row[0] for row in session.execute(text("SELECT value FROM records ORDER BY id"))]
            self.assertEqual(values, ["committed"])

            engine.dispose()

    def test_alembic_configuration_and_initial_revision_are_present(self) -> None:
        ini = (ROOT / "alembic.ini").read_text()
        self.assertIn("script_location = alembic", ini)
        self.assertIn("prepend_sys_path = backend", ini)
        self.assertIn("sqlalchemy.url = sqlite:///./data/jobscrapper.db", ini)

        env = (ROOT / "alembic" / "env.py").read_text()
        self.assertIn("DATABASE_URL", env)
        self.assertIn("run_migrations_offline", env)
        self.assertIn("run_migrations_online", env)

        revision = ROOT / "alembic" / "versions" / "0001_initial.py"
        self.assertTrue(revision.exists())
        revision_text = revision.read_text()
        self.assertIn('revision: str = "0001_initial"', revision_text)
        self.assertIn("down_revision", revision_text)

    def test_backend_readme_documents_sqlite_backup_and_restore(self) -> None:
        readme = (BACKEND / "README.md").read_text()
        self.assertIn("SQLite backup and restore", readme)
        self.assertIn("sqlite3 data/jobscrapper.db", readme)
        self.assertIn("alembic upgrade head", readme)
        self.assertIn("Never commit database files or credentials", readme)


if __name__ == "__main__":
    unittest.main()
