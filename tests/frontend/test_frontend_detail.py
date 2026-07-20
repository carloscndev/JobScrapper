"""Acceptance checks for FRONTEND-004 vacancy detail and safe links."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend/src/App.tsx").read_text()
STYLES = (ROOT / "frontend/src/styles.css").read_text()


class FrontendDetailTests(unittest.TestCase):
    def test_vacancy_detail_exposes_required_match_and_job_fields(self) -> None:
        for field in (
            "description",
            "salary",
            "region",
            "modality",
            "score",
            "gaps",
            "recommendations",
            "descriptionUrl",
            "applicationUrl",
        ):
            self.assertIn(f"vacancy.{field}", APP)
        for label in ("Descripción", "Salario estimado", "Ubicación", "Modalidad", "Compatibilidad", "Brechas detectadas", "Recomendaciones"):
            self.assertIn(label, APP)
        self.assertIn("aria-labelledby=\"vacancy-detail-title\"", APP)
        self.assertIn('id="vacancy-detail-title"', APP)

    def test_external_links_are_explicit_and_safe(self) -> None:
        # Both external actions must open a new context and prevent opener access.
        links = re.findall(
            r'<a[^>]+href=\{vacancy\.(?:applicationUrl|descriptionUrl)\}[^>]*>', APP
        )
        self.assertEqual(len(links), 2)
        for link in links:
            self.assertIn('target="_blank"', link)
            self.assertRegex(link, r'rel="[^"]*noopener[^"]*noreferrer[^"]*"')
        self.assertIn("Aplicar en {vacancy.company}", APP)
        self.assertIn("Ver descripción original", APP)

    def test_detail_can_return_to_list_and_is_keyboard_accessible(self) -> None:
        self.assertIn('className="secondary-button compact detail-back"', APP)
        self.assertIn("← Volver a ofertas", APP)
        self.assertIn("onBack={() => setSelectedVacancy(null)}", APP)
        self.assertIn("onClick={onBack}", APP)
        self.assertIn('type="button"', APP)
        self.assertIn(".detail-back", STYLES)
        self.assertIn(":focus-visible", STYLES)

    def test_detail_has_responsive_layout_contract(self) -> None:
        self.assertIn(".detail-grid", STYLES)
        self.assertIn(".detail-aside", STYLES)
        self.assertIn("@media (max-width: 760px)", STYLES)
        self.assertIn(".detail-grid { grid-template-columns: 1fr; }", STYLES)


if __name__ == "__main__":
    unittest.main()
