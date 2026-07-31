from pathlib import Path
import unittest


APP = (Path(__file__).resolve().parents[2] / "frontend/src/App.tsx").read_text()
STYLES = (Path(__file__).resolve().parents[2] / "frontend/src/styles.css").read_text()


class FrontendActivationDialogTests(unittest.TestCase):
    def test_dialog_exposes_terms_and_accessible_labeling(self):
        for text in (
            'role="dialog"',
            'aria-modal="true"',
            'aria-labelledby="activation-dialog-title"',
            'aria-describedby="activation-dialog-description"',
            'href={sourcePendingActivation.terms_url}',
            'target="_blank"',
            'rel="noopener noreferrer"',
        ):
            self.assertIn(text, APP)

    def test_activation_requires_checkbox_and_cancel_clears_state(self):
        self.assertIn('id="activation-terms-check"', APP)
        self.assertIn("required", APP)
        self.assertIn("disabled={!termsChecked}", APP)
        self.assertIn("const cancelActivation", APP)
        self.assertIn("setSourcePendingActivation(null)", APP)

    def test_dialog_keeps_terms_payload_and_inline_error(self):
        self.assertIn("config: { terms_accepted: true }", APP)
        self.assertIn("activationError", APP)
        self.assertIn("activation-error", APP)
        self.assertIn(".activation-dialog-backdrop", STYLES)
        self.assertIn("@media (max-width: 500px) { .activation-dialog", STYLES)


if __name__ == "__main__":
    unittest.main()
