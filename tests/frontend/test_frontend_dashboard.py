"""Static acceptance checks for FRONTEND-003 vacancy dashboard."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend/src/App.tsx").read_text()
STYLES = (ROOT / "frontend/src/styles.css").read_text()


class FrontendDashboardTests(unittest.TestCase):
    def test_filters_cover_acceptance_dimensions(self) -> None:
        # Each acceptance dimension has a labelled control and participates in
        # the memoized vacancy predicate.
        for label in ("Región", "Modalidad", "Score mínimo", "Empresa", "Fuente", "Desde", "Estado"):
            self.assertIn(label, APP)
        for field in ("region", "modality", "status", "source", "minScore", "company", "date"):
            self.assertIn(field, APP)
        self.assertIn("VACANCIES.filter", APP)
        self.assertIn("useMemo", APP)

    def test_sorting_and_pagination_are_present(self) -> None:
        self.assertIn('Compatibilidad', APP)
        self.assertIn('Más recientes', APP)
        self.assertIn('Empresa A-Z', APP)
        self.assertIn(".sort((a, b)", APP)
        self.assertIn("pageSize = 4", APP)
        self.assertIn("Math.ceil(filtered.length / pageSize)", APP)
        self.assertIn("Anterior", APP)
        self.assertIn("Siguiente", APP)
        self.assertIn('aria-label="Paginación"', APP)

    def test_all_job_statuses_are_distinguishable(self) -> None:
        for status in ("new", "changed", "inactive", "pending"):
            self.assertIn(f'status: "{status}"', APP)
            self.assertIn("status-pill ${job.status}", APP)
            self.assertIn("status-dot ${key}", APP)
            self.assertIn(f".status-pill.{status}", STYLES)
            self.assertIn(f".status-dot.{status}", STYLES)
        self.assertIn('aria-label="Estados de ofertas"', APP)

    def test_region_and_source_fixtures_cover_required_market_segments(self) -> None:
        for region in ("CDMX", "Guadalajara", "USA"):
            self.assertIn(f'<option>{region}</option>', APP)
        for source in ("Greenhouse", "Lever", "LinkedIn"):
            self.assertIn(f'<option>{source}</option>', APP)
        self.assertIn("publishedAt", APP)

    def test_dashboard_has_accessibility_and_responsive_contracts(self) -> None:
        self.assertIn('role="tabpanel"', APP)
        self.assertIn('aria-live="polite"', APP)
        self.assertIn('aria-label="Filtros de ofertas"', APP)
        self.assertIn('aria-label={`${job.score}% de compatibilidad`}', APP)
        self.assertIn(":focus-visible", STYLES)
        self.assertIn("@media (max-width: 600px)", STYLES)
        self.assertIn("@media (max-width: 900px)", STYLES)
        self.assertIn(".filter-panel { grid-template-columns: 1fr; }", STYLES)


if __name__ == "__main__":
    unittest.main()
