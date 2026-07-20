"""Acceptance checks for FRONTEND-005 operations dashboard.

These tests intentionally stay dependency-light: they validate the rendered
React contract and responsive/accessibility hooks even when Playwright is not
installed in the test environment.  The frontend build is run separately as
the executable TypeScript gate.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend/src/App.tsx").read_text()
CLIENT = (ROOT / "frontend/src/api/client.ts").read_text()
STYLES = (ROOT / "frontend/src/styles.css").read_text()


class FrontendOperationsTests(unittest.TestCase):
    def test_operations_tab_and_source_toggles_are_semantic(self) -> None:
        self.assertIn('id="tab-operations"', APP)
        self.assertIn('aria-controls="operations-panel"', APP)
        self.assertIn('role="tabpanel"', APP)
        self.assertIn('id="operations-panel"', APP)
        self.assertIn("toggleSource", APP)
        self.assertIn("source.enabled ? \"Activa\" : \"Pausada\"", APP)
        self.assertIn('aria-pressed={source.enabled}', APP)
        self.assertIn("sources.filter((source) => source.enabled).length", APP)

    def test_metrics_health_runs_errors_and_refresh_are_visible(self) -> None:
        for label in (
            "Ofertas activas",
            "Ejecuciones",
            "Alta compatibilidad",
            "Última actualización",
            "Fuentes conectadas",
            "Salud de servicios",
            "Últimas ejecuciones",
            "Errores",
        ):
            self.assertIn(label, APP)
        self.assertIn("highMatch", APP)
        self.assertIn("operationsHealth", APP)
        self.assertIn("lastUpdated", APP)
        self.assertIn("manualRefresh", APP)
        self.assertIn('aria-busy={refreshing}', APP)
        self.assertIn("Estado temporalmente limitado", APP)
        self.assertIn("Reintentar", APP)
        self.assertIn('role="alert"', APP)

    def test_loading_and_empty_states_have_live_semantics(self) -> None:
        self.assertIn('loading ? <div className="loading-state" role="status" aria-live="polite">', APP)
        self.assertIn("Cargando estado operativo…", APP)
        self.assertIn("No hay fuentes configuradas.", APP)
        self.assertIn("Aún no hay ejecuciones.", APP)
        self.assertIn("Agrega una fuente para iniciar la búsqueda.", APP)
        self.assertIn("Usa “Actualizar ofertas” para iniciar la primera.", APP)
        self.assertGreaterEqual(APP.count('className="empty-state"'), 2)

    def test_execution_table_has_caption_headers_and_scoped_columns(self) -> None:
        self.assertIn("<table>", APP)
        self.assertIn('caption className="sr-only"', APP)
        self.assertIn("Historial de ejecuciones de búsqueda", APP)
        headers = re.findall(r'<th scope="col">([^<]+)</th>', APP)
        for header in ("Estado", "Inicio", "Ofertas", "Errores"):
            self.assertIn(header, headers)
        self.assertIn('role="tablist"', APP)
        self.assertIn('aria-label="Secciones del perfil"', APP)

    def test_api_client_exposes_operations_contract(self) -> None:
        for method in ("getOperationsHealth", "getSources", "getExecutions", "getMetrics", "refresh"):
            self.assertIn(f"{method}:", CLIENT)
        for endpoint in (
            "/api/v1/operations/health",
            "/api/v1/operations/sources",
            "/api/v1/operations/executions?page_size=10",
            "/api/v1/operations/metrics",
            "/api/v1/operations/refresh",
        ):
            self.assertIn(endpoint, CLIENT)
        self.assertIn('method: "POST"', CLIENT)

    def test_responsive_and_keyboard_contracts_are_present(self) -> None:
        self.assertIn('tabIndex={0}', APP)
        self.assertIn(":focus-visible", STYLES)
        self.assertIn(".operations-grid", STYLES)
        self.assertIn(".execution-table-wrap", STYLES)
        self.assertIn("overflow-x: auto", STYLES)
        self.assertIn("@media (max-width: 900px)", STYLES)
        self.assertIn("@media (max-width: 600px)", STYLES)
        self.assertIn(".operations-grid { grid-template-columns: 1fr; }", STYLES)


if __name__ == "__main__":
    unittest.main()
