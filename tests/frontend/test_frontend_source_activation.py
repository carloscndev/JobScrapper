from pathlib import Path
import unittest


APP = (Path(__file__).resolve().parents[2] / "frontend/src/App.tsx").read_text()


class FrontendSourceActivationTests(unittest.TestCase):
    def test_activation_requires_explicit_terms_confirmation(self):
        self.assertIn("source?.config?.terms_accepted !== true", APP)
        self.assertIn("window.confirm", APP)
        self.assertIn("source?.terms_url", APP)
        self.assertIn("if (!accepted) return", APP)

    def test_activation_persists_terms_acceptance_and_pause_does_not(self):
        self.assertIn("config: { terms_accepted: true }", APP)
        self.assertIn("current ? { enabled: false }", APP)

    def test_operation_errors_include_api_field_details(self):
        self.assertIn("errorFields", APP)
        self.assertIn("caught instanceof ApiRequestError", APP)
        self.assertIn("field.message", APP)


if __name__ == "__main__":
    unittest.main()
