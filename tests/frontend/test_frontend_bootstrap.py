"""Static contract tests for the FRONTEND-001 Vite/React bootstrap."""

from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


class FrontendBootstrapTests(unittest.TestCase):
    def test_package_declares_build_metadata_and_scripts(self) -> None:
        package = json.loads((FRONTEND / "package.json").read_text())
        self.assertEqual(package["name"], "jobscrapper-web")
        self.assertEqual(package["version"], "0.1.0")
        self.assertEqual(package["type"], "module")
        self.assertIn("build", package["scripts"])
        self.assertIn("react", package["dependencies"])
        self.assertIn("vite", package["devDependencies"])

    def test_html_has_language_viewport_and_mount_point(self) -> None:
        html = (FRONTEND / "index.html").read_text()
        self.assertIn('<html lang="es">', html)
        self.assertIn('name="viewport"', html)
        self.assertIn('id="root"', html)
        self.assertIn('src="/src/main.tsx"', html)

    def test_app_exposes_semantic_and_keyboard_accessible_controls(self) -> None:
        app = (FRONTEND / "src" / "App.tsx").read_text()
        self.assertIn("createApiClient", app)
        self.assertIn("apiClient.getHealth()", app)
        self.assertNotIn("/api/health", app)
        self.assertIn('<main className="main-content">', app)
        self.assertIn('aria-labelledby="page-title"', app)
        self.assertIn('<h1 id="page-title">', app)
        self.assertGreaterEqual(app.count('type="button"'), 2)
        self.assertIn('disabled={isRefreshing}', app)
        self.assertIn('role="status"', app)

    def test_styles_include_focus_and_small_screen_layout(self) -> None:
        styles = (FRONTEND / "src" / "styles.css").read_text()
        self.assertIn("button:focus-visible", styles)
        self.assertIn("a:focus-visible", styles)
        self.assertIn("@media (max-width: 700px)", styles)
        self.assertIn("grid-template-columns: 1fr", styles)

    def test_api_client_is_typed_and_uses_configured_base_url(self) -> None:
        client = (FRONTEND / "src" / "api" / "client.ts").read_text()
        self.assertIn("export interface ApiClient", client)
        self.assertIn("Promise<HealthResponse>", client)
        self.assertIn("baseUrl = \"\"", client)
        self.assertIn("fetch(`${baseUrl}/health`)", client)


if __name__ == "__main__":
    unittest.main()
