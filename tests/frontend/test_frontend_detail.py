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
            "region",
            "modality",
            "score",
            "description_url",
            "application_url",
        ):
            self.assertIn(f"detail.{field}", APP)
        self.assertIn("salary_min", APP)
        self.assertIn("salary_max", APP)
        self.assertIn("detail.evaluation?.gaps", APP)
        self.assertIn("detail.recommendations", APP)
        for label in ("Descripción", "Salario estimado", "Ubicación", "Modalidad", "Compatibilidad", "Brechas detectadas", "Recomendaciones"):
            self.assertIn(label, APP)
        self.assertIn("aria-labelledby=\"vacancy-detail-title\"", APP)
        self.assertIn('id="vacancy-detail-title"', APP)

    def test_external_links_are_explicit_and_safe(self) -> None:
        matches_aplicar = re.findall(r'<a[^>]+>Aplicar', APP)
        matches_original = re.findall(r'<a[^>]+>Ver descripción original', APP)
        self.assertEqual(len(matches_aplicar), 1)
        self.assertEqual(len(matches_original), 1)
        for tag in re.findall(r'<a[^>]+href=\{detail\.(?:application_url|description_url)\}[^>]*>', APP):
            self.assertIn('target="_blank"', tag)
            self.assertRegex(tag, r'rel="[^"]*noopener[^"]*noreferrer[^"]*"')
        self.assertIn("Aplicar", APP)
        self.assertIn("Ver descripción original", APP)

    def test_detail_can_return_to_list_and_is_keyboard_accessible(self) -> None:
        self.assertIn('className="secondary-button compact detail-back"', APP)
        self.assertIn("← Volver a ofertas", APP)
        self.assertIn("onBack={() => setSelectedJobId(null)}", APP)
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
