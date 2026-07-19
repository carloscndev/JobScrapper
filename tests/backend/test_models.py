"""Contract tests for the DATA-002 domain model layer.

The project keeps SQLAlchemy and Alembic optional in the lightweight test
environment.  Static contracts therefore run without third-party packages;
runtime import checks are skipped explicitly when those packages are absent.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
MODELS = BACKEND / "app" / "models.py"
REPOSITORIES = BACKEND / "app" / "repositories.py"
SERVICES = BACKEND / "app" / "services.py"
MIGRATION = ROOT / "alembic" / "versions" / "0002_domain_models.py"


def _available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _module_from_backend(name: str):
    backend_path = str(BACKEND)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    return __import__(f"app.{name}", fromlist=["*"])


class DomainModelContractTests(unittest.TestCase):
    def test_expected_domain_entities_are_declared(self) -> None:
        tree = ast.parse(MODELS.read_text(), filename=str(MODELS))
        classes = {
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }
        self.assertTrue(
            {
                "Base",
                "Profile",
                "ProfilePreference",
                "Source",
                "Job",
                "JobSnapshot",
                "Evaluation",
                "PipelineExecution",
                "SourceRun",
                "NotionSync",
            }.issubset(classes)
        )

    def test_expected_tables_and_integrity_constraints_are_declared(self) -> None:
        source = MODELS.read_text()
        for table in (
            '"profiles"',
            '"profile_preferences"',
            '"sources"',
            '"jobs"',
            '"job_snapshots"',
            '"evaluations"',
            '"pipeline_executions"',
            '"source_runs"',
            '"notion_syncs"',
        ):
            self.assertIn(f"__tablename__ = {table}", source)
        for constraint in (
            'UniqueConstraint("canonical_url", name="uq_jobs_canonical_url")',
            'UniqueConstraint("fingerprint", name="uq_jobs_fingerprint")',
            'UniqueConstraint("job_id", "content_hash", name="uq_job_snapshot_hash")',
            'UniqueConstraint("job_id", name="uq_notion_sync_job")',
            'UniqueConstraint("external_id", name="uq_notion_sync_external_id")',
        ):
            self.assertIn(constraint, source)

    def test_operational_indexes_cover_query_dimensions(self) -> None:
        source = MODELS.read_text()
        for index in (
            'Index("ix_jobs_region", "region")',
            'Index("ix_jobs_status", "status")',
            'Index("ix_jobs_detected_at", "detected_at")',
            'Index("ix_jobs_published_at", "published_at")',
            'Index("ix_evaluations_score", "score")',
            'Index("ix_evaluations_status", "status")',
            'Index("ix_notion_syncs_state", "state")',
        ):
            self.assertIn(index, source)

    def test_model_module_import_contract_when_sqlalchemy_is_available(self) -> None:
        if not _available("sqlalchemy"):
            self.skipTest("SQLAlchemy is not installed; runtime model import is optional")
        models = _module_from_backend("models")
        for entity in (
            "Profile",
            "ProfilePreference",
            "Source",
            "Job",
            "JobSnapshot",
            "Evaluation",
            "PipelineExecution",
            "SourceRun",
            "NotionSync",
        ):
            self.assertTrue(hasattr(models, entity), entity)
        self.assertEqual(
            set(models.Base.metadata.tables),
            {
                "profiles",
                "profile_preferences",
                "sources",
                "jobs",
                "job_snapshots",
                "evaluations",
                "pipeline_executions",
                "source_runs",
                "notion_syncs",
            },
        )

    def test_repositories_and_services_are_not_coupled_to_fastapi(self) -> None:
        for path in (REPOSITORIES, SERVICES):
            tree = ast.parse(path.read_text(), filename=str(path))
            imported_names = {
                alias.name.split(".")[0]
                for node in tree.body
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            }
            self.assertNotIn("fastapi", imported_names, path.name)
        self.assertIn("class ProfileRepository", REPOSITORIES.read_text())
        self.assertIn("class JobRepository", REPOSITORIES.read_text())
        self.assertIn("class ProfileService", SERVICES.read_text())
        self.assertIn("class JobIngestionService", SERVICES.read_text())

    def test_migration_0002_metadata_and_dependency_are_declared(self) -> None:
        source = MIGRATION.read_text()
        self.assertIn('revision: str = "0002_domain_models"', source)
        self.assertIn('down_revision: Union[str, None] = "0001_initial"', source)
        self.assertIn("def upgrade()", source)
        self.assertIn("def downgrade()", source)
        self.assertIn("op.create_table", source)
        self.assertIn("op.create_index", source)
        self.assertIn("op.drop_table", source)
        self.assertIn("op.drop_index", source)
        self.assertNotIn("from app.models", source)
        self.assertNotIn("Base.metadata.create_all", source)
        self.assertNotIn("Base.metadata.drop_all", source)

        # A downgrade must only remove objects introduced by this revision;
        # it must not drop the initial schema or any future revision's tables.
        downgrade = source[source.index("def downgrade()") :]
        for table in (
            "notion_syncs",
            "source_runs",
            "evaluations",
            "job_snapshots",
            "pipeline_executions",
            "jobs",
            "profile_preferences",
            "sources",
            "profiles",
        ):
            self.assertIn(f'"{table}"', downgrade)
        for forbidden in ("alembic_version", "profile_versions", "job_events"):
            self.assertNotIn(forbidden, downgrade)


if __name__ == "__main__":
    unittest.main()
