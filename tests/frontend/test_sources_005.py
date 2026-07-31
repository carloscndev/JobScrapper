"""Executable contracts for SOURCES-005 source configuration diagnostics.

The repository does not currently ship a browser-test runner, so these checks
exercise the user-visible React/TypeScript contract directly.  They are kept
dependency-light and run as part of the normal unittest discovery; the
frontend build/tsc gate validates the extracted TypeScript as executable code.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend/src/App.tsx").read_text()
CLIENT = (ROOT / "frontend/src/api/client.ts").read_text()


class SourceConfigurationContractTests(unittest.TestCase):
    def test_adapter_selector_lists_supported_adapters(self) -> None:
        self.assertIn("const SOURCE_ADAPTERS", APP)
        for adapter in (
            "json-api-feed",
            "greenhouse-career-page",
            "lever-career-page",
        ):
            self.assertIn(f'value: "{adapter}"', APP)
        self.assertIn('value={formAdapter}', APP)
        self.assertIn('onChange={(e) => setFormAdapter(e.target.value as SourceAdapterName)}', APP)
        self.assertIn("selectedAdapter.fixtureLabel", APP)

    def test_terms_checkbox_is_required_and_blocks_incomplete_sources(self) -> None:
        self.assertIn("formTermsAccepted", APP)
        self.assertRegex(
            APP,
            r'<input type="checkbox"[^>]+checked=\{formTermsAccepted\}[^>]+onChange=\{[^}]*setFormTermsAccepted[^}]*\}[^>]+required',
        )
        self.assertIn("terms_accepted: true", APP)
        self.assertIn("Debes aceptar los términos de uso de la fuente antes de activarla.", APP)
        self.assertIn("if (!formTermsAccepted)", APP)

    def test_fixture_and_network_modes_validate_runnable_configuration(self) -> None:
        self.assertIn('useState<"fixture" | "network">("fixture")', APP)
        self.assertIn('option value="fixture"', APP)
        self.assertIn('option value="network"', APP)
        self.assertIn("if (formMode === \"network\" && !url)", APP)
        self.assertIn("La URL base es obligatoria en modo red.", APP)
        self.assertIn("if (formMode === \"fixture\" && !fixture)", APP)
        self.assertIn("JSON.parse(fixture)", APP)
        self.assertIn("El payload debe ser JSON válido.", APP)
        self.assertIn("allow_network: formMode === \"network\"", APP)
        self.assertIn("{ payload: fixture }", APP)
        self.assertIn("{ html: fixture }", APP)
        self.assertIn("config", CLIENT)

    def test_fixture_shape_rejects_empty_json_and_html_without_cards(self) -> None:
        self.assertIn("Array.isArray(payload)", APP)
        self.assertIn("const jobs = Array.isArray(record.jobs)", APP)
        self.assertIn("const data = Array.isArray(record.data)", APP)
        self.assertIn("if (!items || items.length === 0)", APP)
        self.assertIn("description_url ?? job.url", APP)
        self.assertRegex(APP, r"cardPattern = /<\(article\|li\)")
        self.assertIn("al menos una tarjeta article/li con un enlace de oferta", APP)

    def test_structured_fields_are_rendered_with_the_actionable_message(self) -> None:
        self.assertIn("formErrorFields.length > 0", APP)
        self.assertIn('className="form-error-list"', APP)
        self.assertIn("field.field ?? \"Revisa este campo\"", APP)
        self.assertIn("field.message ?? \"Corrige este valor y vuelve a intentar.\"", APP)

    def test_tabs_support_roving_keyboard_navigation(self) -> None:
        self.assertIn("const handleTabKeyDown", APP)
        for key in ("ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"):
            self.assertIn(f'event.key === "{key}"', APP)
        self.assertIn("tabIndex={section ===", APP)
        self.assertIn("document.getElementById(`tab-${TAB_SECTIONS[nextIndex]}`)?.focus()", APP)

    def test_source_controls_have_stable_names_and_autocomplete_hints(self) -> None:
        for control in (
            'id="source-name" name="sourceName" autoComplete="organization"',
            'id="source-adapter" name="sourceAdapter" autoComplete="off"',
            'id="source-mode" name="sourceMode" autoComplete="off"',
            'id="source-base-url" name="baseUrl" autoComplete="url"',
            'id="source-terms-url" name="termsUrl" autoComplete="url"',
            'id="source-fixture" name="fixture" autoComplete="off"',
            'id="source-terms-accepted" name="termsAccepted" autoComplete="off"',
        ):
            self.assertIn(control, APP)

    def test_structured_422_message_and_fields_reach_the_ui(self) -> None:
        self.assertIn("export class ApiRequestError", CLIENT)
        self.assertIn("readonly status: number", CLIENT)
        self.assertIn("readonly fields:", CLIENT)
        self.assertIn("detail?.message", CLIENT)
        self.assertIn("detail?.fields", CLIENT)
        # FastAPI's structured handlers return {error: {...}} at the top level.
        # Keep this assertion executable so a generic `API request failed (422)`
        # cannot silently replace the actionable source message.
        self.assertIn("body?.error", CLIENT)
        self.assertIn("caught instanceof ApiRequestError ? caught.message", APP)
        self.assertIn('className="error-callout" role="alert"', APP)

    def test_source_run_status_and_errors_are_exposed_per_source(self) -> None:
        self.assertIn("source_runs?: SourceRunSummary[]", CLIENT)
        self.assertIn("const latestSourceRuns = new Map<number, SourceRunSummary>()", APP)
        self.assertIn("execution.source_runs?.forEach", APP)
        self.assertIn("latestSourceRuns.get(source.id)", APP)
        self.assertIn("run?.status === \"success\"", APP)
        self.assertIn("source-run-status", APP)
        self.assertIn("Última ejecución: ${run.status}", APP)
        self.assertIn("${run.status} · ${run.jobs_found} ofertas", APP)
        self.assertIn('className="source-error" title={run.error}', APP)


if __name__ == "__main__":
    unittest.main()
