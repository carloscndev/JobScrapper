"""Static contract tests for the FRONTEND-001 Vite/React bootstrap."""

from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


class DeferredHealthHarness:
    """Executable model of App's in-flight request ref across effect replay."""

    def __init__(self) -> None:
        self.requests = 0
        self.current: object | None = None

    def refresh(self) -> object:
        request = self.current
        if request is None:
            self.requests += 1
            request = object()
        self.current = request
        return request

    def settle(self, request: object) -> None:
        if self.current is request:
            self.current = None


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
        self.assertIn('id="main-content">', app)
        self.assertIn('aria-labelledby="page-title"', app)
        self.assertIn('<h1 id="page-title">', app)
        self.assertGreaterEqual(app.count('type="button"'), 2)
        self.assertIn('disabled={isRefreshing}', app)
        self.assertIn('role="status"', app)

    def test_manual_connection_check_calls_health_and_exposes_pending_state(self) -> None:
        app = (FRONTEND / "src" / "App.tsx").read_text()
        self.assertIn("const refreshHealth = async (announce = true)", app)
        self.assertIn("const response = await apiClient.getHealth()", app)
        self.assertEqual(app.count("await apiClient.getHealth()"), 1)
        self.assertIn('onClick={() => void refreshHealth()}', app)
        self.assertIn('disabled={isRefreshing}', app)
        self.assertIn('aria-busy={isRefreshing}', app)
        self.assertIn('isRefreshing ? "Checking…" : "Check connection"', app)
        self.assertIn('setConnectionMessage("Checking the API connection…")', app)
        self.assertIn("finally {\n      setIsRefreshing(false);", app)

    def test_connection_check_announces_success_and_both_failure_paths(self) -> None:
        app = (FRONTEND / "src" / "App.tsx").read_text()
        self.assertIn("Connection successful. The API is online.", app)
        self.assertIn("Connection failed. The API reported an unhealthy status.", app)
        self.assertIn("Connection failed. The API could not be reached.", app)
        self.assertIn('health === "ok" ? "success" : "failure"', app)
        self.assertIn('role="status" aria-live="polite"', app)
        self.assertIn("{connectionMessage}", app)
        self.assertIn('health === "ok" ? "API connected" : "API pending"', app)

    def test_startup_health_check_does_not_announce_manual_feedback(self) -> None:
        app = (FRONTEND / "src" / "App.tsx").read_text()
        self.assertIn("useEffect(() => { void refreshHealth(false); }, [])", app)
        self.assertIn('if (announce) setConnectionMessage("Checking the API connection…")', app)
        self.assertIn("if (announce) setConnectionMessage(connected ?", app)

    def test_strict_mode_replay_shares_startup_request_and_manual_clicks_are_fresh(self) -> None:
        app = (FRONTEND / "src" / "App.tsx").read_text()
        for contract in (
            "const healthRequestRef = useRef<ReturnType<typeof requestHealth> | null>(null)",
            "const request = healthRequestRef.current ?? requestHealth()",
            "healthRequestRef.current = request",
            "if (healthRequestRef.current === request) healthRequestRef.current = null",
        ):
            self.assertIn(contract, app)

        runtime = DeferredHealthHarness()
        first_effect = runtime.refresh()
        replayed_effect = runtime.refresh()
        self.assertIs(first_effect, replayed_effect)
        self.assertEqual(runtime.requests, 1)

        runtime.settle(first_effect)
        first_manual_click = runtime.refresh()
        self.assertEqual(runtime.requests, 2)
        runtime.settle(first_manual_click)
        second_manual_click = runtime.refresh()
        self.assertIsNot(first_manual_click, second_manual_click)
        self.assertEqual(runtime.requests, 3)

    def test_styles_include_focus_and_small_screen_layout(self) -> None:
        styles = (FRONTEND / "src" / "styles.css").read_text()
        self.assertIn(":focus-visible", styles)
        self.assertIn("@media (max-width: 760px)", styles)
        self.assertIn("grid-template-columns: 1fr", styles)

    def test_api_client_is_typed_and_uses_configured_base_url(self) -> None:
        client = (FRONTEND / "src" / "api" / "client.ts").read_text()
        self.assertIn("export interface ApiClient", client)
        self.assertIn("Promise<HealthResponse>", client)
        self.assertIn("baseUrl = \"\"", client)
        self.assertIn("fetch(`${baseUrl}/health`)", client)


if __name__ == "__main__":
    unittest.main()
