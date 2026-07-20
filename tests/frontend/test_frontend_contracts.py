"""TEST-004 contracts for the composed React views and typed API boundary."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend/src/App.tsx").read_text()
CLIENT = (ROOT / "frontend/src/api/client.ts").read_text()


class FrontendComponentContractTests(unittest.TestCase):
    def test_profile_list_detail_and_operations_views_are_composed(self) -> None:
        for component in ("ProfileSection", "PreferencesSection", "VacancyDashboard", "VacancyDetail", "OperationsDashboard"):
            self.assertIn(f"function {component}", APP)
        for view in ("CV y perfil", "Ofertas", "Operación"):
            self.assertIn(view, APP)

    def test_api_boundary_has_success_and_error_paths(self) -> None:
        self.assertIn("Promise<HealthResponse>", CLIENT)
        self.assertIn("if (!response.ok)", CLIENT)
        self.assertIn("API request failed (${response.status})", CLIENT)
        self.assertIn("method: \"POST\"", CLIENT)


if __name__ == "__main__":
    unittest.main()
