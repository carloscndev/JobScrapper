"""Contract and runtime tests for PROFILE-002 preferences and versioning.

SQLAlchemy/Alembic remain optional in the lightweight test environment.  The
static contracts always run; database-backed behavior is skipped explicitly
when the optional dependencies are unavailable.
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
MIGRATION = ROOT / "alembic" / "versions" / "0003_profile_preferences.py"


def _available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _backend_module(name: str):
    backend_path = str(BACKEND)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    return __import__(f"app.{name}", fromlist=["*"])


class PreferenceContractTests(unittest.TestCase):
    def test_profile_and_preference_fields_cover_configurable_dimensions(self) -> None:
        source = MODELS.read_text()
        for field in (
            "version",
            "seniority",
            "reevaluation_required",
            "reevaluation_reason",
            "reevaluation_metadata",
            "versioned_at",
            "preferred_languages",
            "salary_min",
            "salary_max",
            "salary_currency",
            "salary_period",
            "employment_types",
            "work_authorization",
            "willing_to_relocate",
            "excluded_constraints",
            "weights",
            "is_current",
        ):
            self.assertIn(f"{field}:", source, field)

    def test_preference_repository_and_service_define_revision_workflow(self) -> None:
        repository = REPOSITORIES.read_text()
        service = SERVICES.read_text()
        for symbol in ("current_preferences", "add_preferences", "supersede_preferences"):
            self.assertIn(f"def {symbol}", repository)
        for symbol in ("update_preferences", "clear_reevaluation"):
            self.assertIn(f"def {symbol}", service)
        self.assertIn('profile.version += 1', service)
        self.assertIn('profile.reevaluation_reason = "preferences_changed"', service)
        self.assertIn('"changed_dimensions"', service)
        self.assertIn('evaluated_version == profile.version', service)

    def test_migration_0003_adds_and_reverts_profile_preference_fields(self) -> None:
        source = MIGRATION.read_text()
        self.assertIn('revision: str = "0003_profile_preferences"', source)
        self.assertIn('down_revision: Union[str, None] = "0002_domain_models"', source)
        for table, column in (
            ("profiles", "seniority"),
            ("profiles", "reevaluation_required"),
            ("profiles", "reevaluation_reason"),
            ("profiles", "reevaluation_metadata"),
            ("profiles", "versioned_at"),
            ("profile_preferences", "preferred_languages"),
            ("profile_preferences", "salary_max"),
            ("profile_preferences", "salary_period"),
            ("profile_preferences", "employment_types"),
            ("profile_preferences", "excluded_constraints"),
        ):
            self.assertIn(f'op.add_column("{table}", sa.Column("{column}"', source)
            self.assertIn(f'("{table}", "{column}")', source)

    def test_service_has_no_fastapi_dependency(self) -> None:
        tree = ast.parse(SERVICES.read_text(), filename=str(SERVICES))
        imports = {
            alias.name.split(".")[0]
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("fastapi", imports)


@unittest.skipUnless(_available("sqlalchemy"), "SQLAlchemy is not installed; runtime preference tests are optional")
class PreferenceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        models = _backend_module("models")
        database = _backend_module("database")
        services = _backend_module("services")
        cls.models = models
        cls.engine = database.create_db_engine(database_url="sqlite:///:memory:")
        models.Base.metadata.create_all(cls.engine)
        cls.factory = database.create_session_factory(cls.engine)
        cls.ProfileService = services.ProfileService
        cls.ProfileRepository = _backend_module("repositories").ProfileRepository

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_update_preferences_versions_profile_and_supersedes_current_revision(self) -> None:
        with self.factory() as session:
            profile = self.models.Profile(name="Candidate")
            session.add(profile)
            session.commit()
            service = self.ProfileService(self.ProfileRepository(session))

            first = service.update_preferences(
                profile.id,
                target_roles=["Backend Engineer"],
                locations=["CDMX"],
                modalities=["remote"],
                excluded_constraints=["requires relocation"],
            )
            session.commit()
            self.assertEqual(profile.version, 2)
            self.assertTrue(profile.reevaluation_required)
            self.assertEqual(profile.reevaluation_reason, "preferences_changed")
            self.assertEqual(profile.reevaluation_metadata["profile_version"], 2)
            self.assertEqual(profile.reevaluation_metadata["changed_dimensions"], ["excluded_constraints", "locations", "modalities", "target_roles"])
            self.assertTrue(first.is_current)

            second = service.update_preferences(
                profile.id,
                target_roles=["Senior Backend Engineer"],
                seniority="senior",
                salary_min=50000,
                salary_max=90000,
                salary_currency="USD",
                salary_period="year",
                preferred_languages=["English", "Spanish"],
                employment_types=["full_time"],
                work_authorization=["US citizen"],
                willing_to_relocate=False,
            )
            session.commit()
            self.assertEqual(profile.version, 3)
            self.assertFalse(first.is_current)
            self.assertTrue(second.is_current)
            self.assertEqual(second.salary_max, 90000)
            self.assertEqual(second.preferred_languages, ["English", "Spanish"])

    def test_clear_reevaluation_only_clears_matching_profile_version(self) -> None:
        with self.factory() as session:
            profile = self.models.Profile(name="Candidate")
            session.add(profile)
            session.commit()
            service = self.ProfileService(self.ProfileRepository(session))
            service.update_preferences(profile.id, locations=["USA"])
            session.commit()

            unchanged = service.clear_reevaluation(profile.id, evaluated_version=1)
            self.assertTrue(unchanged.reevaluation_required)
            cleared = service.clear_reevaluation(profile.id, evaluated_version=2)
            self.assertFalse(cleared.reevaluation_required)
            self.assertIsNone(cleared.reevaluation_reason)
            self.assertEqual(cleared.reevaluation_metadata["evaluated_version"], 2)


if __name__ == "__main__":
    unittest.main()
