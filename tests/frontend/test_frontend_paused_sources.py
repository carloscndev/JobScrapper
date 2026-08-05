"""Static contracts for paused-source status rendering (FRONTEND-012)."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend/src/App.tsx").read_text(encoding="utf-8")


class FrontendPausedSourcesTests(unittest.TestCase):
    def test_latest_run_is_only_selected_for_enabled_sources(self) -> None:
        self.assertIn("const latestSourceRuns = new Map<number, SourceRunSummary>()", APP)
        self.assertIn("if (!latestSourceRuns.has(run.source_id)) latestSourceRuns.set(run.source_id, run);", APP)
        self.assertIn("const run = source.enabled ? latestSourceRuns.get(source.id) : undefined;", APP)

    def test_paused_sources_have_explicit_class_and_label(self) -> None:
        self.assertRegex(
            APP,
            r'const runClass = source\.enabled \? \(run\?\.status === "success" \? "healthy" : run \? "failed" : "unknown"\) : "paused";',
        )
        self.assertIn(
            'const runLabel = source.enabled ? (run ? `Latest run: ${run.status}` : "No runs") : "Paused";',
            APP,
        )
        self.assertIn(
            'source.enabled ? (run ? `${run.status} · ${run.jobs_found} openings` : "No runs") : "Paused"',
            APP,
        )

    def test_enabled_source_statuses_and_errors_remain_visible(self) -> None:
        # Enabled sources retain success/failed/unknown status classes and only
        # expose a run error when the source is still enabled.
        self.assertIn('run?.status === "success" ? "healthy" : run ? "failed" : "unknown"', APP)
        self.assertIn("source.enabled && run?.error &&", APP)
        self.assertIn('className="source-error" title={run.error}', APP)


if __name__ == "__main__":
    unittest.main()
