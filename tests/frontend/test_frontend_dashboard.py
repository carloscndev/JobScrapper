"""Static acceptance checks for FRONTEND-003 vacancy dashboard."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend/src/App.tsx").read_text()
STYLES = (ROOT / "frontend/src/styles.css").read_text()


class FrontendDashboardTests(unittest.TestCase):
    def test_filters_cover_acceptance_dimensions(self) -> None:
        for label in ("Region", "Work arrangement", "Minimum score", "Company", "Status", "Sort by"):
            self.assertIn(label, APP)
        for field in ("region", "modality", "status", "minScore", "company", "sort"):
            self.assertIn(field, APP)

    def test_sorting_and_pagination_are_present(self) -> None:
        self.assertIn('Compatibility', APP)
        self.assertIn('Most recent', APP)
        self.assertIn('Company A-Z', APP)
        self.assertIn("pageSize = 4", APP)
        self.assertIn("Previous", APP)
        self.assertIn("Next", APP)
        self.assertIn('aria-label="Pagination"', APP)

    def test_all_job_statuses_are_distinguishable(self) -> None:
        for status in ("new", "changed", "inactive", "pending"):
            self.assertIn(f'.status-pill.{status}', STYLES)
            self.assertIn(f'.status-dot.{status}', STYLES)
        self.assertIn("status-dot ${key}", APP)
        self.assertIn("status-pill ${mapStatus(job.status)}", APP)
        self.assertIn('aria-label="Opening statuses"', APP)

    def test_region_and_source_fixtures_cover_required_market_segments(self) -> None:
        for region in ("CDMX", "Guadalajara", "USA"):
            self.assertRegex(APP, rf'<option value="[^"]+">{region}</option>')
        self.assertIn("published_at", APP)

    def test_dashboard_has_accessibility_and_responsive_contracts(self) -> None:
        self.assertIn('role="tabpanel"', APP)
        self.assertIn('aria-live="polite"', APP)
        self.assertIn('aria-label="Opening filters"', APP)
        self.assertIn('aria-label={`${job.score ?? "N/A"}% compatibility`}', APP)
        self.assertIn(":focus-visible", STYLES)
        self.assertIn("@media (max-width: 600px)", STYLES)
        self.assertIn("@media (max-width: 900px)", STYLES)
        self.assertIn(".filter-panel { grid-template-columns: 1fr; }", STYLES)


if __name__ == "__main__":
    unittest.main()
