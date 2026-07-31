"""Static acceptance checks for FRONTEND-002 profile configuration screens."""

from pathlib import Path
import re
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

    def test_profile_draft_models_constraint_booleans(self) -> None:
        """PROFILE-003 keeps the three constraint controls in the draft model."""
        draft = re.search(r"interface ProfileDraft \{(?P<body>.*?)\n\}", APP, re.DOTALL)
        self.assertIsNotNone(draft)
        body = draft.group("body")
        for field in ("excludeNoSalary", "excludeUnverified", "allowRelocation"):
            self.assertRegex(body, rf"\b{field}: boolean;")
        for token in ("no_salary", "unverified_company", "relocation_required"):
            self.assertIn(f' = "{token}"', APP)

    def test_constraint_checkboxes_are_controlled(self) -> None:
        """Each checkbox must derive checked state and updates from React state."""
        constraints = re.search(r"<fieldset className=\"constraints\">(?P<body>.*?)</fieldset>", APP, re.DOTALL)
        self.assertIsNotNone(constraints)
        body = constraints.group("body")
        for field in ("excludeNoSalary", "excludeUnverified", "allowRelocation"):
            self.assertRegex(body, rf"checked=\{{draft\.{field}\}}")
            self.assertRegex(body, rf'onChange=\{{\(event\) => update\("{field}", event\.target\.checked\)\}}')

    def test_preferences_load_constraint_values_from_api_response(self) -> None:
        """Initial profile hydration reads both persisted constraint representations."""
        hydration = re.search(r"setDraft\(\{(?P<body>.*?)\n\s*\}\);", APP, re.DOTALL)
        self.assertIsNotNone(hydration)
        body = hydration.group("body")
        self.assertIn("p.preferences?.excluded_constraints?.includes(CONSTRAINT_NO_SALARY)", body)
        self.assertIn("p.preferences?.excluded_constraints?.includes(CONSTRAINT_UNVERIFIED_COMPANY)", body)
        self.assertIn("p.preferences?.willing_to_relocate", body)
        self.assertIn("CONSTRAINT_RELOCATION_REQUIRED", body)

    def test_preferences_save_payload_contains_constraint_values(self) -> None:
        """Saving preferences sends willing_to_relocate plus all selected exclusions."""
        payload = re.search(r"updateProfilePreferences\(profileId, \{(?P<body>.*?)\n\s*\}\);", APP, re.DOTALL)
        self.assertIsNotNone(payload)
        body = payload.group("body")
        self.assertIn("willing_to_relocate: draft.allowRelocation", body)
        self.assertIn("excluded_constraints:", body)
        for token in ("CONSTRAINT_NO_SALARY", "CONSTRAINT_UNVERIFIED_COMPANY", "CONSTRAINT_RELOCATION_REQUIRED"):
            self.assertIn(token, body)

    def test_preferences_save_rehydrates_constraint_state_from_response(self) -> None:
        """The API response is applied back to the draft after a successful save."""
        persisted = re.search(r"const persistedConstraints = updated\.preferences\.excluded_constraints.*?setDraft\(\(current\) => \(\{(?P<body>.*?)\n\s*\}\)\);", APP, re.DOTALL)
        self.assertIsNotNone(persisted)
        body = persisted.group("body")
        self.assertIn("persistedConstraints.includes(CONSTRAINT_NO_SALARY)", body)
        self.assertIn("persistedConstraints.includes(CONSTRAINT_UNVERIFIED_COMPANY)", body)
        self.assertIn("updated.preferences?.willing_to_relocate", body)
        self.assertIn("CONSTRAINT_RELOCATION_REQUIRED", body)


if __name__ == "__main__":
    unittest.main()
