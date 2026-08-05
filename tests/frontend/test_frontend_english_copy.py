"""Regression audit for English-only user-facing frontend copy."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_FILES = (ROOT / "frontend/index.html", ROOT / "frontend/src/App.tsx")


class FrontendEnglishCopyTests(unittest.TestCase):
    def test_user_facing_copy_has_no_spanish_ui_phrases(self) -> None:
        spanish_ui_words = re.compile(
            r"\b(?:sube|guardar|ofertas|perfil|preferencias|operación|actualizar|"
            r"reintentar|descripción|ubicación|modalidad|compatibilidad|"
            r"brechas|recomendaciones|ejecuciones|fuentes|términos)\b",
            re.IGNORECASE,
        )
        findings: list[str] = []
        for path in FRONTEND_FILES:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if spanish_ui_words.search(line):
                    findings.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")
        self.assertEqual(findings, [], "Spanish user-facing copy remains:\n" + "\n".join(findings))

    def test_intentional_candidate_name_remains_allowed(self) -> None:
        app = (ROOT / "frontend/src/App.tsx").read_text(encoding="utf-8")
        self.assertIn('name: "Carlos Castañeda"', app)


if __name__ == "__main__":
    unittest.main()
