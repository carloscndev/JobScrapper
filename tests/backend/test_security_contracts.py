"""TEST-006 security contracts for untrusted listings, files and secrets."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.cv_profile import CVValidationError, _validate  # noqa: E402
from app.notion import NotionConfig  # noqa: E402
from app.ollama import _safe_payload  # noqa: E402

if importlib.util.find_spec("sqlalchemy"):
    from app.jobs import canonicalize_url  # noqa: E402
else:
    canonicalize_url = None


class SecurityContractTests(unittest.TestCase):
    def test_only_absolute_http_urls_are_accepted_for_job_identity(self) -> None:
        if canonicalize_url is None:
            self.skipTest("SQLAlchemy is not installed; jobs module import is optional")
        for unsafe in ("javascript:alert(1)", "file:///tmp/cv", "/relative/job", "https://"):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                canonicalize_url(unsafe)

    def test_cv_validation_rejects_traversal_controls_and_polyglot_size(self) -> None:
        for filename in ("../resume.pdf", "folder/resume.pdf", "resume\\.pdf", "resume\n.pdf"):
            with self.subTest(filename=filename), self.assertRaises(CVValidationError):
                _validate(b"%PDF-1.7", filename, "application/pdf", 1024)
        with self.assertRaises(CVValidationError):
            _validate(b"%PDF-1.7" + b"x" * 1024, "resume.pdf", "application/pdf", 100)

    def test_secrets_are_redacted_and_local_model_payload_is_allowlisted(self) -> None:
        config = NotionConfig(token_env="TEST_SECRET_TOKEN", database_id_env="TEST_SECRET_DB")
        self.assertNotIn("secret-value", json.dumps(config.redacted()))
        profile = {"skills": ["Python"], "cv_text": "SECRET-CV", "api_token": "SECRET-TOKEN", "preferences": {}}
        job = {"title": "Backend", "company": "Acme", "description": "Build APIs", "metadata_json": {"secret": "PRIVATE"}}
        payload = json.dumps(_safe_payload(profile, job))
        for secret in ("SECRET-CV", "SECRET-TOKEN", "PRIVATE", "cv_text", "api_token"):
            self.assertNotIn(secret, payload)


if __name__ == "__main__":
    unittest.main()
