"""Static acceptance checks for FRONTEND-002 profile configuration screens."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend/src/App.tsx").read_text()
STYLES = (ROOT / "frontend/src/styles.css").read_text()


class FrontendProfileTests(unittest.TestCase):
    def test_cv_review_and_edit_controls_exist(self) -> None:
        self.assertIn('type="file"', APP)
        self.assertIn('accept=".pdf,.docx', APP)
        self.assertIn("Revisa y corrige tu información", APP)
        for field in ("name", "headline", "skills", "experience", "languages", "education"):
            self.assertIn(f'update("{field}"', APP)

    def test_preferences_constraints_weights_and_reevaluation_warning(self) -> None:
        for field in ("locations", "mode", "minSalary", "maxSalary", "authorization"):
            self.assertIn(f'update("{field}"', APP)
        self.assertIn("Restricciones", APP)
        self.assertIn("weightSkills", APP)
        self.assertIn("weightExperience", APP)
        self.assertIn("weightLocation", APP)
        self.assertIn("weightMode", APP)
        self.assertIn("weightsTotal", APP)
        self.assertIn("Perfil versión ${profileVersion}", APP)

    def test_accessibility_and_responsive_contracts(self) -> None:
        self.assertIn('aria-label={`Peso de ${label}`}', APP)
        self.assertIn('aria-live="polite"', APP)
        self.assertIn('role="status"', APP)
        self.assertIn(":focus-visible", STYLES)
        self.assertIn("@media (max-width: 760px)", STYLES)
        self.assertIn("grid-template-columns: 1fr", STYLES)


if __name__ == "__main__":
    unittest.main()
